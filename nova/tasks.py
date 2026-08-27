"""Background task management — fire-and-forget execution with tracking.

Provides a task manager for running shell commands and sub-agents
in the background with status tracking, output tailing, and
completion notifications.

Design: lightweight, file-based output logs with JSON task manifests.
"""

import json
import logging
import os
import signal
import subprocess
import threading
import time
import uuid
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nova.config import get_nova_home

logger = logging.getLogger(__name__)

# Task status constants
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_KILLED = "killed"

TERMINAL_STATUSES = {STATUS_COMPLETED, STATUS_FAILED, STATUS_KILLED}
_DEFAULT_MAX_OUTPUT_BYTES = 100_000
_DEFAULT_MAX_LIFETIME_SECONDS = 3600


def sanitize_environment() -> dict[str, str]:
    """Return an environment without common credential variables."""
    secret_markers = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
    return {
        key: value
        for key, value in os.environ.items()
        if not any(marker in key.upper() for marker in secret_markers)
    }


@dataclass
class TaskRecord:
    """Metadata for a background task."""

    id: str
    type: str  # "shell" or "agent"
    status: str = STATUS_PENDING
    description: str = ""
    command: str = ""
    cwd: str = ""
    output_file: Path | None = None
    pid: int | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    ended_at: float | None = None
    return_code: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BackgroundTaskManager:
    """Manages background tasks with lifecycle tracking.

    Usage:
        mgr = BackgroundTaskManager()
        task_id = mgr.create_shell_task("sleep 10 && echo done", "wait for it")
        mgr.get_task(task_id)  # check status
        mgr.read_task_output(task_id)  # tail output
        mgr.stop_task(task_id)  # SIGTERM → SIGKILL
    """

    def __init__(self, tasks_dir: Path | None = None, config: dict[str, Any] | None = None) -> None:
        if tasks_dir is None:
            tasks_dir = get_nova_home() / "tasks"
        self.tasks_dir = tasks_dir
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_dir.chmod(0o700)
        task_config = (config or {}).get("tasks", {})
        self.max_output_bytes = int(task_config.get("max_output_bytes", _DEFAULT_MAX_OUTPUT_BYTES))
        self.max_lifetime_seconds = int(
            task_config.get("max_lifetime_seconds", _DEFAULT_MAX_LIFETIME_SECONDS)
        )

        self._tasks: dict[str, TaskRecord] = {}
        self._processes: dict[str, subprocess.Popen] = {}
        self._completion_listeners: list[Callable[[TaskRecord], None]] = []
        self._lock = threading.Lock()
        self._load_manifests()

    def _manifest_path(self, task_id: str) -> Path:
        return self.tasks_dir / f"{task_id}.json"

    @staticmethod
    def _serialize_task(task: TaskRecord) -> dict[str, Any]:
        data = dict(vars(task))
        data["output_file"] = str(task.output_file) if task.output_file else None
        return data

    def _persist_task(self, task: TaskRecord) -> None:
        path = self._manifest_path(task.id)
        temporary = path.with_suffix(".json.tmp")
        try:
            temporary.write_text(json.dumps(self._serialize_task(task)), encoding="utf-8")
            temporary.chmod(0o600)
            temporary.replace(path)
            path.chmod(0o600)
        except OSError as exc:
            logger.warning("Could not persist task %s: %s", task.id, type(exc).__name__)

    def _load_manifests(self) -> None:
        for path in self.tasks_dir.glob("b*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                output_file = data.pop("output_file", None)
                task = TaskRecord(**data, output_file=Path(output_file) if output_file else None)
            except (OSError, TypeError, ValueError):
                logger.warning("Ignoring malformed task manifest %s", path.name)
                continue
            if task.status == STATUS_RUNNING:
                task.status = STATUS_FAILED
                task.ended_at = task.ended_at or time.time()
                task.metadata["error"] = "Task was running when the manager restarted"
                self._persist_task(task)
            self._tasks[task.id] = task

    def create_shell_task(
        self,
        command: str,
        description: str = "",
        cwd: str | None = None,
    ) -> str:
        """Create and start a background shell task.

        Args:
            command: Shell command to execute.
            description: Human-readable description.
            cwd: Working directory (defaults to current directory).

        Returns:
            Task ID string.
        """
        task_id = f"b{uuid.uuid4().hex[:7]}"
        output_file = self.tasks_dir / f"{task_id}.log"

        task = TaskRecord(
            id=task_id,
            type="shell",
            status=STATUS_RUNNING,
            description=description or command[:80],
            command=command,
            cwd=cwd or os.getcwd(),
            output_file=output_file,
            started_at=time.time(),
        )

        with self._lock:
            self._tasks[task_id] = task
        self._persist_task(task)

        # Start the process
        try:
            output_file.touch(mode=0o600, exist_ok=True)
            output_file.chmod(0o600)
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=task.cwd,
                env=sanitize_environment(),
                start_new_session=True,
            )
            threading.Thread(
                target=self._capture_output,
                args=(proc, output_file),
                daemon=True,
            ).start()
            with self._lock:
                task.pid = proc.pid
                self._processes[task_id] = proc
                self._persist_task(task)

            # Start watcher thread
            watcher = threading.Thread(
                target=self._watch_process,
                args=(task_id, proc),
                daemon=True,
            )
            watcher.start()

            logger.info("Started background task %s (pid=%d): %s", task_id, proc.pid, command[:100])
        except Exception as e:
            task.status = STATUS_FAILED
            task.metadata["error"] = str(e)
            task.ended_at = time.time()
            self._persist_task(task)
            logger.error("Failed to start background task %s: %s", task_id, e)
            self._notify_completion(task)

        return task_id

    def _capture_output(self, proc: subprocess.Popen, output_file: Path) -> None:
        """Drain a child pipe while retaining the beginning and end of output."""
        if proc.stdout is None:
            return
        head_limit = max(1, int(self.max_output_bytes * 0.7))
        tail_limit = max(1, int(self.max_output_bytes * 0.2))
        head = bytearray()
        tail = bytearray()
        complete = bytearray()
        total_read = 0
        try:
            while chunk := proc.stdout.read(8192):
                total_read += len(chunk)
                if len(complete) <= self.max_output_bytes:
                    complete.extend(chunk[: max(0, self.max_output_bytes + 1 - len(complete))])
                if len(head) < head_limit:
                    head.extend(chunk[: head_limit - len(head)])
                tail.extend(chunk)
                if len(tail) > tail_limit:
                    del tail[:-tail_limit]
            with output_file.open("wb") as output:
                if total_read <= self.max_output_bytes:
                    output.write(complete)
                else:
                    output.write(head)
                    output.write(b"\n\n[...output truncated...]\n\n")
                    output.write(tail)
        finally:
            proc.stdout.close()

    def get_task(self, task_id: str) -> TaskRecord | None:
        """Get a task record by ID."""
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self, status: str | None = None) -> list[TaskRecord]:
        """List tasks, optionally filtered by status."""
        with self._lock:
            tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def read_task_output(self, task_id: str, max_bytes: int = 12000) -> str:
        """Read the tail of a task's output file.

        Args:
            task_id: Task ID.
            max_bytes: Maximum bytes to read from the end.

        Returns:
            Output string, or error message.
        """
        task = self.get_task(task_id)
        if not task:
            return f"Error: Task '{task_id}' not found."

        if not task.output_file or not task.output_file.exists():
            return "(no output yet)"

        try:
            file_size = task.output_file.stat().st_size
            if file_size == 0:
                return "(no output yet)"

            read_size = min(file_size, max_bytes)
            with open(task.output_file, "rb") as f:
                f.seek(-read_size, 2)  # Seek from end
                raw = f.read()

            # Try to decode, handling partial UTF-8 at the boundary
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                # Find a valid UTF-8 boundary
                for i in range(min(4, len(raw))):
                    try:
                        return raw[i:].decode("utf-8")
                    except UnicodeDecodeError:
                        continue
                return raw.decode("utf-8", errors="replace")
        except Exception as e:
            return f"Error reading output: {e}"

    def stop_task(self, task_id: str) -> str:
        """Stop a running task (SIGTERM → wait 3s → SIGKILL).

        Returns:
            Success/error message.
        """
        with self._lock:
            proc = self._processes.get(task_id)
            task = self._tasks.get(task_id)

            if not task:
                return f"Error: Task '{task_id}' not found."

            if task.status in TERMINAL_STATUSES:
                return f"Task '{task_id}' already {task.status}."

            if not proc or proc.poll() is not None:
                task.status = STATUS_COMPLETED
                task.ended_at = time.time()
                self._persist_task(task)
                finished = True
            else:
                finished = False

        if finished:
            self._notify_completion(task)
            return f"Task '{task_id}' already finished."

        if proc is None:
            return f"Task '{task_id}' already finished."

        # Signal outside the lock so status queries stay responsive during the
        # grace period, then finalize under the lock.
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            logger.info("Sent SIGTERM to task %s (pid=%d)", task_id, proc.pid)
        except OSError:
            pass

        for _ in range(30):
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        else:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                logger.info("Sent SIGKILL to task %s (pid=%d)", task_id, proc.pid)
            except OSError:
                pass

        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status not in TERMINAL_STATUSES:
                task.status = STATUS_KILLED
                task.ended_at = time.time()
                task.return_code = proc.returncode
                self._persist_task(task)
                finalizing = True
            else:
                finalizing = False

        if task and finalizing:
            self._notify_completion(task)
        return f"Task '{task_id}' stopped."

    def update_task(
        self,
        task_id: str,
        *,
        description: str | None = None,
        progress: str | None = None,
        status_note: str | None = None,
    ) -> str:
        """Update mutable task metadata fields."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return f"Error: Task '{task_id}' not found."
            if description is not None:
                task.description = description
            if progress is not None:
                task.metadata["progress"] = progress
            if status_note is not None:
                task.metadata["status_note"] = status_note
            self._persist_task(task)

        return f"Task '{task_id}' updated."

    def register_completion_listener(
        self,
        callback: Callable[[TaskRecord], None],
    ) -> None:
        """Register a callback fired when a task reaches terminal state."""
        self._completion_listeners.append(callback)

    def _watch_process(self, task_id: str, proc: subprocess.Popen) -> None:
        """Watch a process for completion and update task status."""
        try:
            return_code = proc.wait(timeout=self.max_lifetime_seconds)
        except subprocess.TimeoutExpired:
            with suppress(OSError):
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            return_code = proc.wait()
            logger.warning("Background task %s exceeded lifetime limit", task_id)
            timed_out = True
        except Exception as e:
            return_code = -1
            timed_out = False
            logger.error("Error watching task %s: %s", task_id, e)
        else:
            timed_out = False

        should_notify = False
        with self._lock:
            task = self._tasks.get(task_id)
            self._processes.pop(task_id, None)
            # A concurrent stop_task may have already finalized this record;
            # never regress a terminal status or fire listeners twice.
            if task and task.status not in TERMINAL_STATUSES:
                task.return_code = return_code
                task.ended_at = time.time()
                task.status = (
                    STATUS_FAILED
                    if timed_out
                    else (STATUS_COMPLETED if return_code == 0 else STATUS_FAILED)
                )
                self._persist_task(task)
                should_notify = True

        if task and should_notify:
            logger.info(
                "Background task %s finished (exit=%d) after %.1fs",
                task_id,
                return_code,
                ((task.ended_at or time.time()) - (task.started_at or task.created_at)),
            )
            self._notify_completion(task)

    def _notify_completion(self, task: TaskRecord) -> None:
        """Fire completion listeners."""
        for listener in self._completion_listeners:
            try:
                listener(task)
            except Exception as e:
                logger.error("Completion listener error: %s", e)

    def shutdown(self) -> None:
        """Stop all running tasks and clean up."""
        with self._lock:
            task_ids = list(self._processes.keys())

        for task_id in task_ids:
            self.stop_task(task_id)

        self._tasks.clear()
        self._processes.clear()


# Global task manager (lazy-initialized)
_task_manager: BackgroundTaskManager | None = None
_task_manager_lock = threading.Lock()


def get_task_manager() -> BackgroundTaskManager:
    """Get or create the global task manager."""
    global _task_manager
    if _task_manager is None:
        with _task_manager_lock:
            if _task_manager is None:
                _task_manager = BackgroundTaskManager()
    return _task_manager


def reset_task_manager() -> None:
    """Reset the global task manager (for testing)."""
    global _task_manager
    with _task_manager_lock:
        if _task_manager:
            tasks_dir = _task_manager.tasks_dir
            _task_manager.shutdown()
            for path in tasks_dir.glob("b*.json"):
                with suppress(OSError):
                    path.unlink()
            for path in tasks_dir.glob("b*.log"):
                with suppress(OSError):
                    path.unlink()
        _task_manager = None
