"""Track in-process pipeline tasks so deleted sessions can stop running."""

import asyncio
import logging

_tasks: dict[str, asyncio.Task] = {}


def register_session_task(session_id: str, task: asyncio.Task) -> None:
    previous = _tasks.get(session_id)
    if previous is not None and not previous.done():
        previous.cancel()
    _tasks[session_id] = task

    def remove_if_current(completed: asyncio.Task) -> None:
        if not completed.cancelled():
            error = completed.exception()
            if error is not None:
                logging.getLogger(__name__).error(
                    "Pipeline task stopped: session=%s error=%s", session_id, error
                )
        if _tasks.get(session_id) is completed:
            _tasks.pop(session_id, None)

    task.add_done_callback(remove_if_current)


def cancel_session_task(session_id: str) -> None:
    task = _tasks.pop(session_id, None)
    if task is not None:
        task.cancel()


async def stop_session_tasks() -> None:
    tasks = list(_tasks.values())
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    _tasks.clear()
