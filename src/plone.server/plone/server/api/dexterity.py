
from plone.server.api.service import Service
from plone.server.browser import get_physical_path


class DefaultGET(Service):
    async def __call__(self):
        return {
            'context': str(self.context),
            'path': '/'.join(get_physical_path(self.context)),
            'portal_type': self.context.portal_type
        }


class DefaultPOST(Service):
    pass


class DefaultPUT(Service):
    pass


class DefaultPATCH(Service):
    pass


class SharingPOST(Service):
    pass


class DefaultDELETE(Service):
    pass

