from guillotina import configure
from guillotina.component import ComponentLookupError
from guillotina.component import get_utility
from guillotina.contrib.mcp.interfaces import IMCPUtility
from guillotina.events import ApplicationInitializedEvent

import asyncio
import logging


logger = logging.getLogger("guillotina")


@configure.subscriber(for_=ApplicationInitializedEvent)
async def mcp_lifespan_startup(event):
    try:
        mcp_utility = get_utility(IMCPUtility)
    except ComponentLookupError:
        return
    session_manager = mcp_utility.session_manager
    ready = asyncio.Event()
    stop = asyncio.Event()
    startup_exc = None

    async def _run_session_manager():
        nonlocal startup_exc
        try:
            async with session_manager.run():
                ready.set()
                await stop.wait()
        except Exception as exc:
            startup_exc = exc
            ready.set()
            raise

    manager_task = asyncio.create_task(_run_session_manager())
    await ready.wait()
    if startup_exc is not None:
        await asyncio.gather(manager_task, return_exceptions=True)
        raise startup_exc

    async def cleanup(_app):
        stop.set()
        await manager_task
        logger.info("MCP session manager stopped (lifespan)")

    event.app.on_cleanup.insert(0, cleanup)
    logger.info("MCP session manager started (lifespan)")
