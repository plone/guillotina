from guillotina import task_vars


class ServiceExecutor:
    """
    Its always the last middleware and is responsible to call the actual
    guillotina service (the view resolved during the traversal)
    """

    async def __call__(self, scope, receive, send):
        service_handler = task_vars.service.get()
        request = task_vars.request.get()
        return await service_handler(request)
