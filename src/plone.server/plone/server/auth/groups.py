from plone.server.auth.users import PloneUser


class PloneGroup(PloneUser):
    def __init__(self, request, ident):
        super(PloneGroup, self).__init__(request)
        self.id = ident

        if ident == 'Managers':
            # Special Case its a Root Manager user
            self._roles['plone.SiteAdmin'] = 1
            self._roles['plone.SiteDeleter'] = 1
            self._roles['plone.Owner'] = 1
            self._roles['plone.Member'] = 1
