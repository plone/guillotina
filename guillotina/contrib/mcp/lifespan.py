from contextlib import AsyncExitStack
from guillotina import configure
from guillotina.component import ComponentLookupError
from guillotina.component import get_utility
from guillotina.contrib.mcp.interfaces import IMCPUtility
from guillotina.events import ApplicationInitializedEvent

import logging


logger = logging.getLogger("guillotina")


@configure.subscriber(for_=ApplicationInitializedEvent)
async def mcp_lifespan_startup(event):
    try:
        mcp_utility = get_utility(IMCPUtility)
    except ComponentLookupError:
        return
    session_manager = mcp_utility.server.session_manager
    exit_stack = AsyncExitStack()
    await exit_stack.enter_async_context(session_manager.run())

    async def cleanup(_app):
        await exit_stack.aclose()
        logger.info("MCP session manager stopped (lifespan)")

    event.app.on_cleanup.insert(0, cleanup)
    logger.info("MCP session manager started (lifespan)")
