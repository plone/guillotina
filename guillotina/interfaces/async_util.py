from zope.interface import Interface


class IAsyncUtility(Interface):

    async def initialize():
        '''
        Method that is called on startup and used to create task.
        '''

    async def finalize():
        '''
        Called to shut down and cleanup the task
        '''


class IQueueUtility(IAsyncUtility):
    pass


class IAsyncJobPool(IAsyncUtility):
    pass
