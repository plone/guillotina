import asyncio
from contextlib import closing

from guillotina.commands import Command
from guillotina.tests import fixtures
from guillotina.tests.fixtures import _UNFINISHED_TASKS, _cancel_leftover_tasks, _keep_unfinished_tasks
from guillotina.utils.asyncio import cancel_tasks


def test_command_cancels_only_the_tasks_pending_at_shutdown(event_loop):
    spawned_tasks = []

    async def pending_task():
        await asyncio.Event().wait()

    task = event_loop.create_task(pending_task())
    task.add_done_callback(lambda _: spawned_tasks.append(event_loop.create_task(pending_task())))
    event_loop.run_until_complete(asyncio.sleep(0))

    Command()._cancel_all_tasks(event_loop)

    assert task.cancelled()
    assert len(spawned_tasks) == 1
    assert not spawned_tasks[0].done()


def test_event_loop_cancels_tasks_spawned_by_async_generator(event_loop):
    spawned_tasks = []
    stopped = []

    async def pending_task():
        try:
            await asyncio.Event().wait()
        finally:
            stopped.append(True)

    async def generator():
        try:
            yield
        finally:
            spawned_tasks.append(asyncio.create_task(pending_task()))
            await asyncio.sleep(0)

    async def start_generator():
        stream = generator()
        await stream.asend(None)
        return stream

    try:
        with closing(fixtures.event_loop.__wrapped__()) as fixture:
            loop = next(fixture)
            stream = loop.run_until_complete(start_generator())

        assert stream.ag_frame is None
        assert loop.is_closed()
        assert len(spawned_tasks) == 1
        assert spawned_tasks[0].cancelled()
        assert stopped == [True]
        assert spawned_tasks[0] not in _UNFINISHED_TASKS
    finally:
        asyncio.set_event_loop(event_loop)


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
