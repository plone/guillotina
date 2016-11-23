

class RootUserIdentifier(object):
    def __init__(self, request):
        self.request = request

    async def get_user(self):
        return self.request.application.root_user
