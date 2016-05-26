# -*- coding: utf-8 -*-
from aiohttp.abc import AbstractMatchInfo
from aiohttp.abc import AbstractRouter
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_exceptions import HTTPUnauthorized
from plone.registry.interfaces import IRegistry
from plone.server import DICT_METHODS
from plone.server import DICT_RENDERS
from plone.server.api.layer import IDefaultLayer
from plone.server.contentnegotiation import content_negotiation
from plone.server.interfaces import IRendered
from plone.server.interfaces import IRequest
from plone.server.interfaces import ITranslated
from plone.server.interfaces import ITraversableView
from plone.server.interfaces import IView
from plone.server.registry import ACTIVE_LAYERS_KEY
from plone.server.security import DexterityPermissionChecker
from plone.server.utils import import_class
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.component import queryMultiAdapter
from zope.component.interfaces import ISite
from zope.interface import alsoProvides
from zope.security.checker import getCheckerForInstancesOf
from zope.security.checker import selectChecker
from zope.security.interfaces import IInteraction
from zope.security.interfaces import IParticipation
from zope.security.interfaces import IPermission
from zope.security.proxy import ProxyFactory


async def traverse(request, parent, path):
    if not path:
        return parent, path

    assert request is not None  # could be used for permissions, etc

    try:
        if path[0].startswith('_'):
            raise HTTPUnauthorized()
        context = parent[path[0]]
    except TypeError:
        return parent, path
    except KeyError:
        return parent, path

    context._v_parent = parent

    if ISite.providedBy(context):
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
    def __init__(self, request, resource, view, rendered):
        self.request = request
        self.resource = resource
        self.view = view
        self.rendered = rendered

    async def handler(self, request):
        view_result = await self.view()
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
    _root_factory = None

    def __init__(self, root_factory=None):
        self.set_root_factory(root_factory)

    def set_root_factory(self, root_factory):
        self._root_factory = root_factory

    async def resolve(self, request):
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

        traverse_to = None
        if tail and len(tail) == 1:
            view_name = tail[0]
        elif tail is None or len(tail) == 0:
            view_name = ''
        else:
            view_name = tail[0]
            traverse_to = tail[1:]

        method = DICT_METHODS[request.method]

        renderer, language = content_negotiation(request)
        language_object = language(request)

        translator = queryMultiAdapter(
            (language_object, resource, request),
            ITranslated)
        if translator is not None:
            resource = translator.translate()

        # permission_tool = IPermissionTool(request)
        # if not checkPermission(resource, 'Access content'):
        #     raise HTTPUnauthorized('No access to content')

        permission = getUtility(IPermission, name='plone.AccessContent')

        allowed = request.security.checkPermission(permission.id, resource)

        if not allowed:
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
        renderer_object = renderer(request)

        rendered = queryMultiAdapter(
            (renderer_object, view, request), IRendered)

        if rendered is not None:
            return MatchInfo(resource, request, view, rendered)
        else:
            raise HTTPNotFound()

    async def traverse(self, request):
        path = tuple(p for p in request.path.split('/') if p)
        root = self._root_factory()
        if path:
            return await traverse(request, root, path)
        else:
            return root, path
