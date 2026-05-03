"""Tests for the background task manager."""

import time
from pathlib import Path

from nova.tasks import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_KILLED,
    STATUS_RUNNING,
    BackgroundTaskManager,
    get_task_manager,
    reset_task_manager,
)


def _make_manager(tmp_path: Path) -> BackgroundTaskManager:
    return BackgroundTaskManager(tasks_dir=tmp_path / "tasks")


# ── Create and Run Shell Task ───────────────────────────────────────────────


def test_create_shell_task_immediate_command(tmp_path):
    mgr = _make_manager(tmp_path)
    task_id = mgr.create_shell_task("echo hello", "test echo")

    task = mgr.get_task(task_id)
    assert task is not None
    assert task.type == "shell"
    assert task.description == "test echo"
    assert task.status in (STATUS_RUNNING, STATUS_COMPLETED)

    # Wait for completion
    time.sleep(0.5)
    task = mgr.get_task(task_id)
    assert task.status == STATUS_COMPLETED
    assert task.return_code == 0


def test_create_shell_task_failing_command(tmp_path):
    mgr = _make_manager(tmp_path)
    task_id = mgr.create_shell_task("false", "test fail")

    time.sleep(0.5)
    task = mgr.get_task(task_id)
    assert task.status == STATUS_FAILED
    assert task.return_code == 1


def test_create_shell_task_with_cwd(tmp_path):
    mgr = _make_manager(tmp_path)
    task_id = mgr.create_shell_task("pwd", "test cwd", cwd=str(tmp_path))

    time.sleep(0.5)
    output = mgr.read_task_output(task_id)
    assert str(tmp_path) in output


# ── Read Task Output ────────────────────────────────────────────────────────


def test_read_task_output(tmp_path):
    mgr = _make_manager(tmp_path)
    task_id = mgr.create_shell_task("echo hello world", "test output")

    time.sleep(0.5)
    output = mgr.read_task_output(task_id)
    assert "hello world" in output


def test_read_task_output_nonexistent(tmp_path):
    mgr = _make_manager(tmp_path)
    result = mgr.read_task_output("nonexistent")
    assert "not found" in result


def test_read_task_output_no_file(tmp_path):
    mgr = _make_manager(tmp_path)
    task_id = mgr.create_shell_task("echo test", "test")
    # Output file might not exist yet if process hasn't started
    result = mgr.read_task_output(task_id)
    # Should not crash
    assert isinstance(result, str)


# ── Stop Task ───────────────────────────────────────────────────────────────


def test_stop_running_task(tmp_path):
    mgr = _make_manager(tmp_path)
    task_id = mgr.create_shell_task("sleep 10", "test stop")

    time.sleep(0.2)
    result = mgr.stop_task(task_id)
    assert "stopped" in result.lower() or "already" in result.lower()

    time.sleep(0.5)
    task = mgr.get_task(task_id)
    assert task.status in (STATUS_KILLED, STATUS_COMPLETED, STATUS_FAILED)


def test_stop_nonexistent_task(tmp_path):
    mgr = _make_manager(tmp_path)
    result = mgr.stop_task("nonexistent")
    assert "not found" in result


def test_stop_already_finished_task(tmp_path):
    mgr = _make_manager(tmp_path)
    task_id = mgr.create_shell_task("echo done", "test")

    time.sleep(0.5)
    result = mgr.stop_task(task_id)
    assert "already" in result.lower()


# ── List Tasks ──────────────────────────────────────────────────────────────


def test_list_tasks(tmp_path):
    mgr = _make_manager(tmp_path)
    mgr.create_shell_task("echo a", "task a")
    mgr.create_shell_task("echo b", "task b")

    time.sleep(0.5)
    tasks = mgr.list_tasks()
    assert len(tasks) >= 2


def test_list_tasks_filter_by_status(tmp_path):
    mgr = _make_manager(tmp_path)
    mgr.create_shell_task("echo ok", "success")
    mgr.create_shell_task("false", "failure")

    time.sleep(0.5)
    completed = mgr.list_tasks(status=STATUS_COMPLETED)
    failed = mgr.list_tasks(status=STATUS_FAILED)

    # At least one of each should exist
    assert len(completed) >= 1 or len(failed) >= 1


# ── Update Task ─────────────────────────────────────────────────────────────


def test_update_task(tmp_path):
    mgr = _make_manager(tmp_path)
    task_id = mgr.create_shell_task("echo test", "original")

    result = mgr.update_task(task_id, description="updated", progress="50%")
    assert "updated" in result

    task = mgr.get_task(task_id)
    assert task.description == "updated"
    assert task.metadata.get("progress") == "50%"


def test_update_nonexistent_task(tmp_path):
    mgr = _make_manager(tmp_path)
    result = mgr.update_task("nonexistent", description="nope")
    assert "not found" in result


# ── Completion Listener ─────────────────────────────────────────────────────


def test_completion_listener(tmp_path):
    mgr = _make_manager(tmp_path)
    completed_tasks = []

    mgr.register_completion_listener(lambda task: completed_tasks.append(task.id))
    task_id = mgr.create_shell_task("echo done", "test listener")

    time.sleep(1.0)
    assert task_id in completed_tasks


# ── Global Task Manager ─────────────────────────────────────────────────────


def test_get_task_manager_singleton():
    reset_task_manager()
    mgr1 = get_task_manager()
    mgr2 = get_task_manager()
    assert mgr1 is mgr2
    reset_task_manager()


def test_reset_task_manager():
    mgr = get_task_manager()
    mgr.create_shell_task("echo test", "test")
    reset_task_manager()
    # After reset, a new manager is created
    new_mgr = get_task_manager()
    assert new_mgr.list_tasks() == []
    reset_task_manager()
