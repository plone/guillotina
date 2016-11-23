

class RootUserIdentifier(object):
    def __init__(self, request):
        self.request = request

    async def get_user(self, token):
        return self.request.application.root_user
