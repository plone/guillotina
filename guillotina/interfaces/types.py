from zope.interface import Interface


class IConstrainTypes(Interface):

    def __init__(context):  # noqa: N805
        pass

    def is_type_allowed(type_id: str) -> bool:  # noqa: N805
        pass

    def get_allowed_types():
        pass
