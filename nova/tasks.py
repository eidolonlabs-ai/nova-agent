"""Background task management — fire-and-forget execution with tracking.

Provides a task manager for running shell commands and sub-agents
in the background with status tracking, output tailing, and
completion notifications.

Design: lightweight, file-based output logs with in-memory task registry.
"""

import logging
import os
import signal
import subprocess
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Task status constants
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_KILLED = "killed"

TERMINAL_STATUSES = {STATUS_COMPLETED, STATUS_FAILED, STATUS_KILLED}


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

    def __init__(self, tasks_dir: Path | None = None) -> None:
        if tasks_dir is None:
            from nova.config import get_nova_home
            tasks_dir = get_nova_home() / "tasks"
        self.tasks_dir = tasks_dir
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

        self._tasks: dict[str, TaskRecord] = {}
        self._processes: dict[str, subprocess.Popen] = {}
        self._completion_listeners: list[Callable[[TaskRecord], None]] = []
        self._lock = threading.Lock()

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

        # Start the process
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                proc = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    cwd=task.cwd,
                    start_new_session=True,  # New process group for clean kill
                )
            task.pid = proc.pid

            with self._lock:
                self._processes[task_id] = proc

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
            logger.error("Failed to start background task %s: %s", task_id, e)
            self._notify_completion(task)

        return task_id

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
            return f"Task '{task_id}' already finished."

        # SIGTERM first
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            logger.info("Sent SIGTERM to task %s (pid=%d)", task_id, proc.pid)
        except OSError:
            pass

        # Wait up to 3 seconds
        for _ in range(30):
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        else:
            # SIGKILL
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                logger.info("Sent SIGKILL to task %s (pid=%d)", task_id, proc.pid)
            except OSError:
                pass

        task.status = STATUS_KILLED
        task.ended_at = time.time()
        task.return_code = proc.returncode
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
        task = self.get_task(task_id)
        if not task:
            return f"Error: Task '{task_id}' not found."

        if description is not None:
            task.description = description
        if progress is not None:
            task.metadata["progress"] = progress
        if status_note is not None:
            task.metadata["status_note"] = status_note

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
            return_code = proc.wait()
        except Exception as e:
            return_code = -1
            logger.error("Error watching task %s: %s", task_id, e)

        with self._lock:
            task = self._tasks.get(task_id)
            self._processes.pop(task_id, None)

        if task:
            task.return_code = return_code
            task.ended_at = time.time()
            task.status = STATUS_COMPLETED if return_code == 0 else STATUS_FAILED

            logger.info(
                "Background task %s finished (exit=%d) after %.1fs",
                task_id, return_code,
                (task.ended_at - (task.started_at or task.created_at)),
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
            _task_manager.shutdown()
        _task_manager = None
