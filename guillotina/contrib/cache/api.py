from guillotina import configure
from guillotina.component import get_utility
from guillotina.interfaces import ICacheUtility
from guillotina.interfaces import IContainer


@configure.service(context=IContainer, name="@cache-stats", method="GET", permission="guillotina.CacheManage")
async def stats(context, request):
    utility = get_utility(ICacheUtility)
    return await utility.get_stats()


@configure.service(
    context=IContainer, name="@cache-clear", method="POST", permission="guillotina.CacheManage"
)
async def clear(context, request):
    utility = get_utility(ICacheUtility)
    await utility.clear()
    return {"success": True}
