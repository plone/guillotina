# -*- coding: utf-8 -*-


class View(object):
    def __init__(self, request, context):
        self.request = request
        self.context= context

    async def __call__(self):
        raise NotImplementedError
