

class Message(str):
    """
    XXX nothing right now, implement i18n here...
    """

    def __new__(cls, ustr, domain=None, default=None, mapping=None):
        self = str.__new__(cls, ustr)
        if isinstance(ustr, self.__class__):
            domain = ustr.domain and ustr.domain[:] or domain
            default = ustr.default and ustr.default[:] or default
            mapping = ustr.mapping and ustr.mapping.copy() or mapping
            ustr = str(ustr)
        self.domain = domain
        if default is None:
            # MessageID does: self.default = ustr
            self.default = default
        else:
            self.default = str(default)
        self.mapping = mapping
        self._readonly = True
        return self


class MessageFactory(object):
    """Factory for creating i18n messages."""

    def __init__(self, domain):
        self._domain = domain

    def __call__(self, ustr, default=None, mapping=None):
        return Message(ustr, self._domain, default, mapping)
