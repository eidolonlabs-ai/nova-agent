# Background Tasks

Nova Agent supports fire-and-forget background task execution. Start long-running commands without blocking the conversation, check their status, read output, or stop them at any time.

## Quick Start

Use the built-in task tools in conversation:

```
User: Start a background task to run the test suite
Assistant: [calls task_create with command="pytest -v"]
Assistant: Task started: b3f8a2c (test suite)

User: Check the status of task b3f8a2c
Assistant: [calls task_status]
Assistant: Task b3f8a2c is running (pid 12345)

User: Show me the output so far
Assistant: [calls task_output]
Assistant: ==================== test session starts ====================
collected 240 items
...
```

## Available Tools

| Tool | Description |
|------|-------------|
| `task_create` | Start a background shell command |
| `task_status` | Check a task's status |
| `task_output` | Read the tail of a task's log |
| `task_stop` | Stop a running task (SIGTERM → SIGKILL) |
| `task_list` | List all tasks, optionally filtered by status |

## Task Lifecycle

```
task_create("sleep 60 && echo done", "wait a minute")
    ↓
Task ID returned immediately (e.g., "b3f8a2c")
    ↓
Task runs in background (new process group)
    ↓
Check status: task_status("b3f8a2c") → {"status": "running"}
    ↓
Read output: task_output("b3f8a2c") → "(no output yet)"
    ↓
... time passes ...
    ↓
task_status("b3f8a2c") → {"status": "completed", "return_code": 0}
task_output("b3f8a2c") → "done"
```

## Task Statuses

| Status | Meaning |
|--------|---------|
| `pending` | Task created but not yet started |
| `running` | Task is executing |
| `completed` | Task finished with exit code 0 |
| `failed` | Task finished with non-zero exit code |
| `killed` | Task was stopped by `task_stop` |

## Stopping Tasks

`task_stop` sends SIGTERM first, waits 3 seconds, then sends SIGKILL:

```
task_stop("b3f8a2c")
    ↓
SIGTERM sent to process group
    ↓
Wait up to 3 seconds for graceful exit
    ↓
If still running → SIGKILL
    ↓
Status set to "killed"
```

## Task Output

Output is captured to a log file in `~/.nova/tasks/`. `task_output` reads the tail:

```python
# Default: last 12,000 bytes
task_output("b3f8a2c")

# Custom size
task_output("b3f8a2c", max_bytes=5000)
```

## Listing Tasks

```python
# All tasks
task_list()

# Filter by status
task_list(status="running")
task_list(status="completed")
```

## Programmatic API

For custom integrations, use the `BackgroundTaskManager` directly:

```python
from nova.tasks import get_task_manager

mgr = get_task_manager()

# Create a task
task_id = mgr.create_shell_task("sleep 10 && echo done", "wait")

# Check status
task = mgr.get_task(task_id)
print(task.status)  # "running"

# Read output
output = mgr.read_task_output(task_id)

# Stop a task
mgr.stop_task(task_id)

# Register a completion listener
def on_complete(task):
    print(f"Task {task.id} finished with code {task.return_code}")

mgr.register_completion_listener(on_complete)
```

## Configuration

Background tasks are always available — no config needed. Task logs are stored in `~/.nova/tasks/`.
