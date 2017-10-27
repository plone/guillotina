from zope.interface import Interface


class IConstrainTypes(Interface):

    def __init__(context):  # noqa: N805
        '''
        '''

    def is_type_allowed(type_id: str) -> bool:  # noqa: N805
        '''
        return true if type is allowed
        '''

    def get_allowed_types():
        '''
        get all allowed types
        '''
