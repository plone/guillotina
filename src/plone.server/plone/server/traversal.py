# -*- coding: utf-8 -*-
"""Main routing traversal class."""
from aiohttp.abc import AbstractMatchInfo
from aiohttp.abc import AbstractRouter
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_exceptions import HTTPUnauthorized
from aiohttp.web_exceptions import HTTPBadRequest
from plone.registry.interfaces import IRegistry
from plone.server import DICT_METHODS
from plone.server.api.layer import IDefaultLayer
from plone.server.contentnegotiation import content_type_negotiation
from plone.server.contentnegotiation import language_negotiation
from plone.server.interfaces import IRendered
from plone.server.interfaces import IRequest
from plone.server.interfaces import ITranslated
from plone.server.interfaces import ITraversableView
from plone.server.interfaces import IDataBase
from plone.server.interfaces import IApplication
from plone.server.interfaces import IOPTIONS
from plone.server.registry import ACTIVE_LAYERS_KEY
from plone.server.registry import CORS_KEY
from plone.server.auth.participation import AnonymousParticipation
from plone.server.utils import import_class
from plone.server.utils import locked
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.component import queryMultiAdapter
from zope.component.interfaces import ISite
from zope.interface import alsoProvides
from zope.security.checker import getCheckerForInstancesOf
from zope.security.interfaces import IInteraction
from zope.security.interfaces import IParticipation
from zope.security.interfaces import IPermission
from zope.security.interfaces import Unauthorized
from zope.security.proxy import ProxyFactory
from plone.server.utils import sync

WRITING_VERBS = ['POST', 'PUT', 'PATCH', 'DELETE']


async def do_traverse(request, parent, path):
    """Traverse for the code API."""
    if not path:
        return parent, path

    assert request is not None  # could be used for permissions, etc

    if ISite.providedBy(parent) and \
       path[0] != request._db_id:
        raise HTTPUnauthorized('Tried to access a site outsite the request')

    if IApplication.providedBy(parent) and \
       path[0] != request._site_id:
        raise HTTPUnauthorized('Tried to access a site outsite the request')

    try:
        if path[0].startswith('_'):
            raise HTTPUnauthorized()
        context = parent[path[0]]
    except TypeError:
        return parent, path
    except KeyError:
        return parent, path

    context._v_parent = parent

    return await traverse(request, context, path[1:])


async def traverse(request, parent, path):
    """Do not use outside the main router function."""
    if IApplication.providedBy(parent):
        participation = parent.root_participation(request)
        if participation:
            request.security.add(participation)

    if not path:
        return parent, path

    assert request is not None  # could be used for permissions, etc

    dbo = None
    if IDataBase.providedBy(parent):
        # Look on the PersistentMapping from the DB
        dbo = parent
        parent = parent._conn.root()

    try:
        if path[0].startswith('_'):
            raise HTTPUnauthorized()
        context = parent[path[0]]
    except TypeError:
        return parent, path
    except KeyError:
        return parent, path

    if dbo is not None:
        context._v_parent = dbo
    else:
        context._v_parent = parent

    if IDataBase.providedBy(context):
        request.conn = context.conn
        request._db_id = context.id

    if ISite.providedBy(context):
        request._site_id = context.id
        request.site = context
        request.site_components = context.getSiteManager()
        request.site_settings = request.site_components.getUtility(IRegistry)
        participation = IParticipation(request)
        # Lets extract the user from the request
        await participation()
        request.security.add(participation)
        layers = request.site_settings.get(ACTIVE_LAYERS_KEY, [])
        for layer in layers:
            alsoProvides(request, import_class(layer))

    return await traverse(request, context, path[1:])


class MatchInfo(AbstractMatchInfo):
    """Function that returns from traversal request on aiohttp."""

    def __init__(self, request, resource, view, rendered):
        """Value that comes from the traversing."""
        self.request = request
        self.resource = resource
        self.view = view
        self.rendered = rendered

    async def handler(self, request):
        """Main handler function for aiohttp."""
        if request.method in WRITING_VERBS:
            txn = request.conn.transaction_manager.begin(request)
            async with locked(self.resource):
                try:
                    view_result = await self.view()
                except Unauthorized:
                    view_result = HTTPUnauthorized()
            try:
                await sync(request)(txn.commit)
            except Unauthorized:
                view_result = HTTPUnauthorized()
            except Exception as e:
                view_result = HTTPBadRequest(text=str(e))
        else:
            try:
                view_result = await self.view()
            except Unauthorized:
                view_result = HTTPUnauthorized()
        print(self.rendered)
        return await self.rendered(view_result)

    def get_info(self):
        return {
            'request': self.request,
            'resource': self.resource,
            'view': self.view,
            'rendered': self.rendered
        }

    async def expect_handler(self, request):
        return None

    async def http_exception(self):
        return None


class TraversalRouter(AbstractRouter):
    """Custom router for plone.server."""

    _root = None

    def __init__(self, root=None):
        """On traversing aiohttp sets the root object."""
        self.set_root(root)

    def set_root(self, root):
        """Warpper to set the root object."""
        self._root = root

    async def resolve(self, request):
        """Main function to resolve a request."""
        alsoProvides(request, IRequest)
        alsoProvides(request, IDefaultLayer)
        request.site_components = getGlobalSiteManager()
        request.security = IInteraction(request)

        try:
            resource, tail = await self.traverse(request)
            exc = None
        except Exception as _exc:
            resource = None
            tail = None
            exc = _exc

        request.resource = resource
        request.tail = tail
        request.exc = exc

        if request.resource is None:
            raise HTTPBadRequest(text=str(request.exc))

        traverse_to = None
        if tail and len(tail) == 1:
            view_name = tail[0]
        elif tail is None or len(tail) == 0:
            view_name = ''
        else:
            view_name = tail[0]
            traverse_to = tail[1:]

        method = DICT_METHODS[request.method]

        language = language_negotiation(request)
        language_object = language(request)

        translator = queryMultiAdapter(
            (language_object, resource, request),
            ITranslated)
        if translator is not None:
            resource = translator.translate()

        # Add anonymous participation
        if len(request.security.participations) == 0:
            request.security.add(AnonymousParticipation(request))

        permission = getUtility(IPermission, name='plone.AccessContent')

        allowed = request.security.checkPermission(permission.id, resource)

        if not allowed:
            # Check if its a CORS call:
            if IOPTIONS != method or \
               not request.site_settings.get(CORS_KEY, False):
                raise HTTPUnauthorized()

        # Site registry lookup
        try:
            view = request.site_components.queryMultiAdapter(
                (resource, request), method, name=view_name)
        except AttributeError:
            view = None

        # Global registry lookup
        if view is None:
            view = queryMultiAdapter(
                (resource, request), method, name=view_name)

        # Traverse view if its needed
        if traverse_to is not None:
            if view is None or not ITraversableView.providedBy(view):
                return HTTPNotFound('No view defined')
            else:
                view = view.publishTraverse(traverse_to)

        checker = getCheckerForInstancesOf(view.__class__)
        if checker is not None:
            view = ProxyFactory(view, checker)
        # We want to check for the content negotiation

        renderer = content_type_negotiation(request, resource, view)
        print(renderer)
        renderer_object = renderer(request)

        rendered = queryMultiAdapter(
            (renderer_object, view, request), IRendered)

        if rendered is not None:
            return MatchInfo(resource, request, view, rendered)
        else:
            raise HTTPNotFound()

    async def traverse(self, request):
        """Wrapper that looks for the path based on aiohttp API."""
        path = tuple(p for p in request.path.split('/') if p)
        root = self._root
        return await traverse(request, root, path)
