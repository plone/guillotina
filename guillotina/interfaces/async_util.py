from zope.interface import Interface
from typing import Dict
from typing import Optional


class IAsyncUtility(Interface):
    async def initialize():
        """
        Method that is called on startup and used to create task.
        """

    async def finalize():
        """
        Called to shut down and cleanup the task
        """


class IQueueUtility(IAsyncUtility):
    pass


class IAsyncJobPool(IAsyncUtility):
    pass


class ICacheUtility(IAsyncUtility):
    pass


class IPubSubUtility(IAsyncUtility):
    pass


class IAuthValidationUtility(IAsyncUtility):

    async def start(
            as_user: str,
            email: str,
            from_user: str,
            task_description: str,
            task_id: str,
            redirect_url: Optional[str] = None,
            context_description: Optional[str] = None,
            ttl: Optional[int] = 3660,
            data: Optional[Dict] = None):
        pass

    async def schema(token: str):
        pass

    async def finish(token: str, payload: Optional[Dict] = None):
        pass
