from guillotina import configure
from guillotina.content import get_cached_factory
from guillotina.interfaces import IConstrainTypes
from zope.interface import Interface


@configure.adapter(
    for_=Interface,
    provides=IConstrainTypes)
class FTIConstrainAllowedTypes(object):

    def __init__(self, context: Interface):
        self.context = context

    def is_type_allowed(self, type_id: str) -> bool:
        allowed = self.get_allowed_types()
        if allowed is None:
            # not define
            return True
        return type_id in allowed

    def get_allowed_types(self) -> list:
        tn = getattr(self.context, 'type_name', None)
        if tn:
            factory = get_cached_factory(tn)
            return factory.allowed_types
        return None
