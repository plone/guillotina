import asyncio

from plone.server.traversal.abc import AbstractView


class View(AbstractView):
    def __init__(self, request, resource, tail):
        self.request = request
        self.resource = resource
        self.tail = tail

    @asyncio.coroutine
    def __call__(self):
        raise NotImplementedError
