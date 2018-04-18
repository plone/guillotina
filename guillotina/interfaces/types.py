from zope.interface import Interface


class IConstrainTypes(Interface):  # pylint: disable=E0239

    def __init__(self, context, default=None):  # noqa: N805
        '''
        '''

    def is_type_allowed(self, type_id: str) -> bool:  # noqa: N805
        '''
        return true if type is allowed
        '''

    def get_allowed_types(self) -> list:
        '''
        get all allowed types
        '''
