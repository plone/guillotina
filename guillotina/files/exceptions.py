class RangeException(Exception):
    def __init__(self, *, field=None, blob=None):
        super().__init__()
        self.field = field
        self.blob = blob


class RangeNotSupported(RangeException):
    """
    Request request is not supported
    """


class RangeNotFound(RangeException):
    def __init__(self, *, field=None, blob=None, start=None, end=None):
        super().__init__(field=field, blob=blob)
        self.start = start
        self.end = end
