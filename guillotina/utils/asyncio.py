import asyncio
import time


def cancel_tasks(loop, timeout):
    """Cancel and drain loop tasks, including tasks scheduled by done callbacks.

    Returns the tasks cancelled and any tasks still pending after ``timeout``.
    The loop must not be running when this function is called.
    """
    deadline = time.monotonic() + timeout
    cancelled = set()

    while True:
        pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
        if not pending:
            break

        for task in pending:
            if task not in cancelled:
                task.cancel()
                cancelled.add(task)

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        loop.run_until_complete(
            asyncio.wait(
                pending,
                timeout=remaining,
                return_when=asyncio.FIRST_COMPLETED,
            )
        )

    unfinished = [task for task in asyncio.all_tasks(loop) if not task.done()]
    return cancelled, unfinished
