from .content import IResource
from zope.interface import Interface


class IConstrainTypes(Interface):  # pylint: disable=E0239
    def __init__(context: IResource, default=None):  # noqa: N805
        """
        """

    def is_type_allowed(type_id: str) -> bool:  # noqa: N805
        """
        return true if type is allowed
        """

    def get_allowed_types() -> list:
        """
        get all allowed types
        """
