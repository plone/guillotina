import asyncio

from guillotina.tests.fixtures import _UNFINISHED_TASKS, _cancel_leftover_tasks, _keep_unfinished_tasks
from guillotina.utils.asyncio import cancel_tasks


def test_cancel_tasks_cancels_tasks_scheduled_during_cancellation():
    loop = asyncio.new_event_loop()
    spawned_tasks = []

    async def pending_task():
        await asyncio.Event().wait()

    async def task_that_spawns_on_cancel():
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            spawned_tasks.append(loop.create_task(pending_task()))
            raise

    parent_task = loop.create_task(task_that_spawns_on_cancel())
    try:
        loop.run_until_complete(asyncio.sleep(0))
        unfinished = _cancel_leftover_tasks(loop, timeout=1)

        assert parent_task.done()
        assert len(spawned_tasks) == 1
        assert spawned_tasks[0].done()
        assert unfinished == []
    finally:
        loop.close()


def test_cancel_tasks_returns_tasks_that_ignore_cancellation():
    loop = asyncio.new_event_loop()
    release_task = loop.create_future()
    exception_contexts = []
    loop.set_exception_handler(lambda loop, context: exception_contexts.append(context))

    async def task_that_delays_cancellation():
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            await release_task

    task = loop.create_task(task_that_delays_cancellation())
    loop.run_until_complete(asyncio.sleep(0))
    try:
        cancelled, unfinished = cancel_tasks(loop, timeout=0.01)

        assert task in cancelled
        assert unfinished == [task]
        _keep_unfinished_tasks(loop, unfinished)
        assert task in _UNFINISHED_TASKS
        assert "did not finish" in exception_contexts[0]["message"]

        release_task.set_result(None)
        loop.run_until_complete(task)
    finally:
        if not task.done():
            if not release_task.done():
                release_task.set_result(None)
            task.cancel()
            loop.run_until_complete(asyncio.gather(task, return_exceptions=True))
        if task in _UNFINISHED_TASKS:
            _UNFINISHED_TASKS.remove(task)
        loop.close()
