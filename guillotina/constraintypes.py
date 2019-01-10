from guillotina import app_settings
from guillotina import configure
from guillotina.content import get_cached_factory
from guillotina.interfaces import IConstrainTypes
from guillotina.interfaces import IDatabase
from zope.interface import Interface


@configure.adapter(
    for_=Interface,
    provides=IConstrainTypes)
class FTIConstrainAllowedTypes:

    def __init__(self, context: Interface) -> None:
        self.context = context

    def is_type_allowed(self, type_id: str) -> bool:
        if type_id in app_settings['container_types']:
            return False
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
        return []


@configure.adapter(
    for_=IDatabase,
    provides=IConstrainTypes)
class DatabaseAllowedTypes:
    '''
    Can only add containers to databases
    '''

    def __init__(self, context: Interface) -> None:
        self.context = context

    def is_type_allowed(self, type_id: str) -> bool:
        return type_id in app_settings['container_types']

    def get_allowed_types(self) -> list:
        return app_settings['container_types']
