
class NoPermissionToAdd(Exception):

    def __init__(self, container, content_type):
        self.container = container
        self.content_type = content_type

    def __repr__(self):
        return "Not permission to add {content_type} on {path}".format(
            content_type=self.content_type,
            path=self.path)


class NotAllowedContentType(Exception):

    def __init__(self, container, content_type):
        self.container = container
        self.content_type = content_type

    def __repr__(self):
        return "Not allowed {content_type} on {path}".format(
            content_type=self.content_type,
            path=self.path)
