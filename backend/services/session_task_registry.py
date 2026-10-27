"""Track in-process pipeline tasks so deleted sessions can stop running."""

import asyncio


_tasks: dict[str, asyncio.Task] = {}


def register_session_task(session_id: str, task: asyncio.Task) -> None:
    _tasks[session_id] = task

    def remove_if_current(completed: asyncio.Task) -> None:
        if _tasks.get(session_id) is completed:
            _tasks.pop(session_id, None)

    task.add_done_callback(remove_if_current)


def cancel_session_task(session_id: str) -> None:
    task = _tasks.pop(session_id, None)
    if task is not None:
        task.cancel()
