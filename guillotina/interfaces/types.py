from zope.interface import Interface


class IConstrainTypes(Interface):

    def __init__(context):
        pass

    def is_type_allowed(type_id: str) -> bool:
        pass

    def get_allowed_types():
        pass
