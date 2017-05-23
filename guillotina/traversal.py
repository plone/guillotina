# -*- coding: utf-8 -*-
"""Main routing traversal class."""
from aiohttp.abc import AbstractMatchInfo
from aiohttp.abc import AbstractRouter
from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_exceptions import HTTPUnauthorized
from guillotina import _
from guillotina import app_settings
from guillotina import logger
from guillotina.api.content import DefaultOPTIONS
from guillotina.auth.participation import AnonymousParticipation
from guillotina.browser import ErrorResponse
from guillotina.browser import Response
from guillotina.browser import UnauthorizedResponse
from guillotina.component import getUtility
from guillotina.component import queryMultiAdapter
from guillotina.contentnegotiation import content_type_negotiation
from guillotina.contentnegotiation import language_negotiation
from guillotina.exceptions import ConflictError
from guillotina.exceptions import TIDConflictError
from guillotina.exceptions import Unauthorized
from guillotina.interfaces import ACTIVE_LAYERS_KEY
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IApplication
from guillotina.interfaces import IAsyncContainer
from guillotina.interfaces import IContainer
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IDefaultLayer
from guillotina.interfaces import IInteraction
from guillotina.interfaces import IOPTIONS
from guillotina.interfaces import IParticipation
from guillotina.interfaces import IPermission
from guillotina.interfaces import IRendered
from guillotina.interfaces import IRequest
from guillotina.interfaces import ITranslated
from guillotina.interfaces import ITraversable
from guillotina.interfaces import ITraversableView
from guillotina.interfaces import SUBREQUEST_METHODS
from guillotina.interfaces import WRITING_VERBS
from guillotina.registry import REGISTRY_DATA_KEY
from guillotina.security.utils import get_view_permission
from guillotina.transactions import abort
from guillotina.transactions import commit
from guillotina.utils import apply_cors
from guillotina.utils import get_authenticated_user_id
from guillotina.utils import import_class
from zope.interface import alsoProvides

import aiohttp
import asyncio
import json
import traceback
import uuid


async def do_traverse(request, parent, path):
    """Traverse for the code API."""
    if not path:
        return parent, path

    assert request is not None  # could be used for permissions, etc

    if IContainer.providedBy(parent) and \
       path[0] != request._db_id:
        # Tried to access a container outside the request
        raise HTTPUnauthorized()

    if IApplication.providedBy(parent) and \
       path[0] != request._container_id:
        # Tried to access a container outside the request
        raise HTTPUnauthorized()

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


async def subrequest(
        orig_request, path, relative_to_container=True,
        headers={}, body=None, params=None, method='GET'):
    """Subrequest, initial implementation doing a real request."""
    async with aiohttp.ClientSession() as session:
        method = method.lower()
        if method not in SUBREQUEST_METHODS:
            raise AttributeError('No valid method ' + method)
        caller = getattr(session, method)

        for head in orig_request.headers:
            if head not in headers:
                headers[head] = orig_request.headers[head]

        params = {
            'headers': headers,
            'params': params
        }
        if method in ['put', 'patch']:
            params['data'] = body

        return caller(path, **params)


async def traverse(request, parent, path):
    """Do not use outside the main router function."""
    if IApplication.providedBy(parent):
        request.application = parent

    if not path:
        return parent, path

    assert request is not None  # could be used for permissions, etc

    if not ITraversable.providedBy(parent):
        # not a traversable context
        return parent, path
    try:
        if path[0].startswith('_'):
            raise HTTPUnauthorized()
        if IAsyncContainer.providedBy(parent):
            context = await parent.async_get(path[0])
            if context is None:
                return parent, path
        else:
            context = parent[path[0]]
    except (TypeError, KeyError, AttributeError):
        return parent, path

    if IDatabase.providedBy(context):
        request._db_write_enabled = request.method in WRITING_VERBS
        request._db_id = context.id
        # Add a transaction Manager to request
        tm = request._tm = context.get_transaction_manager()
        # Start a transaction
        txn = await tm.begin(request=request)
        # Get the root of the tree
        context = await tm.get_root(txn=txn)

    if IContainer.providedBy(context):
        request._container_id = context.id
        request.container = context
        annotations_container = IAnnotations(request.container)
        request.container_settings = await annotations_container.async_get(REGISTRY_DATA_KEY)
        layers = request.container_settings.get(ACTIVE_LAYERS_KEY, [])
        for layer in layers:
            try:
                alsoProvides(request, import_class(layer))
            except ModuleNotFoundError:
                logger.error('Can not apply layer ' + layer)

    return await traverse(request, context, path[1:])


def _url(request):
    try:
        return request.url.human_repr()
    except AttributeError:
        # older version of aiohttp
        return request.path


def generate_unauthorized_response(e, request):
    # We may need to check the roles of the users to show the real error
    eid = uuid.uuid4().hex
    message = _('Not authorized to render operation') + ' ' + eid
    user = get_authenticated_user_id(request)
    extra = {
        'r': _url(request),
        'u': user
    }
    logger.error(
        message,
        exc_info=e,
        extra=extra)
    return UnauthorizedResponse(message)


def generate_error_response(e, request, error, status=400):
    # We may need to check the roles of the users to show the real error
    eid = uuid.uuid4().hex
    message = _('Error on execution of view') + ' ' + eid
    user = get_authenticated_user_id(request)
    extra = {
        'r': _url(request),
        'u': user
    }
    logger.error(
        message,
        exc_info=e,
        extra=extra)

    return ErrorResponse(
        error,
        message,
        status
    )


class MatchInfo(AbstractMatchInfo):
    """Function that returns from traversal request on aiohttp."""

    def __init__(self, resource, request, view, rendered):
        """Value that comes from the traversing."""
        self.request = request
        self.resource = resource
        self.view = view
        self.rendered = rendered
        self._apps = []
        self._frozen = False

    async def handler(self, request):
        """Main handler function for aiohttp."""
        if request.method in WRITING_VERBS:
            try:
                # We try to avoid collisions on the same instance of
                # guillotina
                view_result = await self.view()
                if isinstance(view_result, ErrorResponse) or \
                        isinstance(view_result, UnauthorizedResponse):
                    # If we don't throw an exception and return an specific
                    # ErrorReponse just abort
                    await abort(request)
                else:
                    await commit(request, warn=False)

            except Unauthorized as e:
                await abort(request)
                view_result = generate_unauthorized_response(e, request)
            except (ConflictError, TIDConflictError) as e:
                # bubble this error up
                raise
            except Exception as e:
                await abort(request)
                view_result = generate_error_response(
                    e, request, 'ServiceError')
        else:
            try:
                view_result = await self.view()
            except Unauthorized as e:
                view_result = generate_unauthorized_response(e, request)
            except Exception as e:
                view_result = generate_error_response(e, request, 'ViewError')
            finally:
                await abort(request)

        # Make sure its a Response object to send to renderer
        if not isinstance(view_result, Response):
            view_result = Response(view_result)
        elif view_result is None:
            # Always provide some response to work with
            view_result = Response({})

        # Apply cors if its needed
        cors_headers = apply_cors(request)
        cors_headers.update(view_result.headers)
        view_result.headers = cors_headers
        retry_attempts = getattr(request, '_retry_attempt', 0)
        if retry_attempts > 0:
            view_result.headers['X-Retry-Transaction-Count'] = str(retry_attempts)

        resp = await self.rendered(view_result)
        if not resp.prepared:
            await resp.prepare(request)
        await resp.write_eof()
        resp._body = None
        resp.force_close()

        futures_to_wait = request._futures.values()
        if futures_to_wait:
            await asyncio.gather(*[f for f in futures_to_wait])

        return resp

    def get_info(self):
        return {
            'request': self.request,
            'resource': self.resource,
            'view': self.view,
            'rendered': self.rendered
        }

    @property
    def apps(self):
        return tuple(self._apps)

    def add_app(self, app):
        if self._frozen:
            raise RuntimeError("Cannot change apps stack after .freeze() call")
        self._apps.insert(0, app)

    def freeze(self):
        self._frozen = True

    async def expect_handler(self, request):
        return None

    async def http_exception(self):
        return None


class TraversalRouter(AbstractRouter):
    """Custom router for guillotina."""

    _root = None

    def __init__(self, root=None):
        """On traversing aiohttp sets the root object."""
        self.set_root(root)

    def set_root(self, root):
        """Warpper to set the root object."""
        self._root = root

    async def resolve(self, request):
        result = None
        try:
            result = await self.real_resolve(request)
        except Exception as e:
            logger.error(
                "Exception on resolve execution",
                exc_info=e)
            await abort(request)
            raise e
        if result is not None:
            return result
        else:
            await abort(request)
            raise HTTPNotFound()

    async def real_resolve(self, request):
        """Main function to resolve a request."""
        alsoProvides(request, IRequest)
        alsoProvides(request, IDefaultLayer)

        request._futures = {}

        security = IInteraction(request)

        method = app_settings['http_methods'][request.method]

        language = language_negotiation(request)
        language_object = language(request)

        try:
            resource, tail = await self.traverse(request)
        except Exception as _exc:
            request.resource = request.tail = None
            request.exc = _exc
            # XXX should only should traceback if in some sort of dev mode?
            raise HTTPBadRequest(text=json.dumps({
                'success': False,
                'exception_message': str(_exc),
                'exception_type': getattr(type(_exc), '__name__', str(type(_exc))),  # noqa
                'traceback': traceback.format_exc()
            }))

        request.resource = resource
        request.tail = tail

        if request.resource is None:
            raise HTTPBadRequest(text='Resource not found')

        traverse_to = None
        if tail and len(tail) == 1:
            view_name = tail[0]
        elif tail is None or len(tail) == 0:
            view_name = ''
        else:
            view_name = tail[0]
            traverse_to = tail[1:]

        await self.apply_authorization(request)

        translator = queryMultiAdapter(
            (language_object, resource, request),
            ITranslated)
        if translator is not None:
            resource = translator.translate()

        # Add anonymous participation
        if len(security.participations) == 0:
            # logger.info("Anonymous User")
            security.add(AnonymousParticipation(request))

        # container registry lookup
        try:
            view = queryMultiAdapter(
                (resource, request), method, name=view_name)
        except AttributeError:
            view = None

        # Traverse view if its needed
        if traverse_to is not None and view is not None:
            if not ITraversableView.providedBy(view):
                return None
            else:
                try:
                    view = await view.publish_traverse(traverse_to)
                except Exception as e:
                    logger.error(
                        "Exception on view execution",
                        exc_info=e)
                    return None

        permission = getUtility(IPermission, name='guillotina.AccessContent')

        if not security.check_permission(permission.id, resource):
            # Check if its a CORS call:
            if IOPTIONS != method or not app_settings['cors']:
                # Check if the view has permissions explicit
                if view is None or not view.__allow_access__:
                    logger.warning("No access content {content} with {auths}".format(
                        content=resource,
                        auths=str([x.principal.id
                                   for x in security.participations])))
                    raise HTTPUnauthorized()

        if view is None and method == IOPTIONS:
            view = DefaultOPTIONS(resource, request)

        if view:
            ViewClass = view.__class__
            view_permission = get_view_permission(ViewClass)
            if not security.check_permission(view_permission, view):
                logger.warning("No access for view {content} with {auths}".format(
                    content=resource,
                    auths=str([x.principal.id
                               for x in security.participations])))
                raise HTTPUnauthorized()

        renderer = content_type_negotiation(request, resource, view)
        renderer_object = renderer(request)

        rendered = queryMultiAdapter(
            (renderer_object, view, request), IRendered)

        if rendered is not None:
            return MatchInfo(resource, request, view, rendered)
        else:
            return None

    async def traverse(self, request):
        """Wrapper that looks for the path based on aiohttp API."""
        path = tuple(p for p in request.path.split('/') if p)
        root = self._root
        return await traverse(request, root, path)

    async def apply_authorization(self, request):
        # User participation
        participation = IParticipation(request)
        # Lets extract the user from the request
        await participation()
        if participation.principal is not None:
            request.security.add(participation)
