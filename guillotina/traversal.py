"""Main routing traversal class."""
from aiohttp.abc import AbstractMatchInfo
from aiohttp.abc import AbstractRouter
from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp.web_exceptions import HTTPMethodNotAllowed
from aiohttp.web_exceptions import HTTPException
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_exceptions import HTTPUnauthorized
from guillotina import logger
from guillotina._settings import app_settings
from guillotina.api.content import DefaultOPTIONS
from guillotina.auth.participation import AnonymousParticipation
from guillotina.browser import ErrorResponse
from guillotina.browser import Response
from guillotina.browser import UnauthorizedResponse
from guillotina.component import get_adapter
from guillotina.component import get_utility
from guillotina.component import query_adapter
from guillotina.component import query_multi_adapter
from guillotina.contentnegotiation import content_type_negotiation
from guillotina.contentnegotiation import language_negotiation
from guillotina.event import notify
from guillotina.events import ObjectLoadedEvent
from guillotina.exceptions import ConflictError
from guillotina.exceptions import TIDConflictError
from guillotina.exceptions import Unauthorized
from guillotina.i18n import default_message_factory as _
from guillotina.interfaces import ACTIVE_LAYERS_KEY
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IApplication
from guillotina.interfaces import IAsyncContainer
from guillotina.interfaces import IContainer
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IInteraction
from guillotina.interfaces import IOPTIONS
from guillotina.interfaces import IParticipation
from guillotina.interfaces import IPermission
from guillotina.interfaces import IRendered
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource
from guillotina.interfaces import ITranslated
from guillotina.interfaces import ITraversable
from guillotina.interfaces import ITraversableView
from guillotina.interfaces import SUBREQUEST_METHODS
from guillotina.profile import profilable
from guillotina.registry import REGISTRY_DATA_KEY
from guillotina.security.utils import get_view_permission
from guillotina.transactions import abort
from guillotina.transactions import commit
from guillotina.utils import import_class
from zope.interface import alsoProvides

import aiohttp
import traceback
import ujson
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
        if path[0].startswith('_') or path[0] in ('.', '..'):
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
        if path[0].startswith('_') or path[0] in ('.', '..'):
            raise HTTPUnauthorized()
        if IAsyncContainer.providedBy(parent):
            context = await parent.async_get(path[0], suppress_events=True)
            if context is None:
                return parent, path
        else:
            context = parent[path[0]]
    except (TypeError, KeyError, AttributeError):
        return parent, path

    if IDatabase.providedBy(context):
        request._db_write_enabled = app_settings['check_writable_request'](request)
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
                logger.error('Can not apply layer ' + layer, request=request)

    return await traverse(request, context, path[1:])


def generate_unauthorized_response(e, request):
    # We may need to check the roles of the users to show the real error
    eid = uuid.uuid4().hex
    message = _('Not authorized to render operation') + ' ' + eid
    logger.error(message, exc_info=e, eid=eid, request=request)
    return UnauthorizedResponse(message)


def generate_error_response(e, request, error, status=500):
    # We may need to check the roles of the users to show the real error
    eid = uuid.uuid4().hex
    message = _('Error on execution of view') + ' ' + eid
    logger.error(message, exc_info=e, eid=eid, request=request)
    return ErrorResponse(error, message, status)


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

    @profilable
    async def handler(self, request):
        """Main handler function for aiohttp."""
        request._view_error = False
        if app_settings['check_writable_request'](request):
            try:
                # We try to avoid collisions on the same instance of
                # guillotina
                view_result = await self.view()
                request.record('view')
                if isinstance(view_result, ErrorResponse) or \
                        isinstance(view_result, UnauthorizedResponse):
                    # If we don't throw an exception and return an specific
                    # ErrorReponse just abort
                    await abort(request)
                    request._view_error = True
                else:
                    await commit(request, warn=False)

            except Unauthorized as e:
                await abort(request)
                view_result = generate_unauthorized_response(e, request)
                request._view_error = True
            except (ConflictError, TIDConflictError) as e:
                # bubble this error up
                raise
            except HTTPException as exc:
                await abort(request)
                return exc
            except Exception as e:
                await abort(request)
                view_result = generate_error_response(
                    e, request, 'ServiceError')
                request._view_error = True
        else:
            try:
                view_result = await self.view()
            except Unauthorized as e:
                request._view_error = True
                view_result = generate_unauthorized_response(e, request)
            except HTTPException as exc:
                return exc
            except Exception as e:
                request._view_error = True
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
        cors_renderer = app_settings['cors_renderer'](request)
        cors_headers = await cors_renderer.get_headers()
        cors_headers.update(view_result.headers)
        view_result.headers = cors_headers
        retry_attempts = getattr(request, '_retry_attempt', 0)
        if retry_attempts > 0:
            view_result.headers['X-Retry-Transaction-Count'] = str(retry_attempts)

        resp = await self.rendered(view_result)
        request.record('rendered')

        if not resp.prepared:
            await resp.prepare(request)
        await resp.write_eof()
        resp._body = None
        resp.force_close()

        request.execute_futures()

        request.record('finish')
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


class BasicMatchInfo(AbstractMatchInfo):
    """Function that returns from traversal request on aiohttp."""

    def __init__(self, request, resp):
        """Value that comes from the traversing."""
        self.request = request
        self.resp = resp
        self._apps = []
        self._frozen = False

    @profilable
    async def handler(self, request):
        """Main handler function for aiohttp."""
        request.record('finish')
        return self.resp

    def get_info(self):
        return {
            'request': self.request,
            'resp': self.resp
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

    def __init__(self, root: IApplication=None):
        """On traversing aiohttp sets the root object."""
        self.set_root(root)

    def set_root(self, root: IApplication):
        """Warpper to set the root object."""
        self._root = root

    async def resolve(self, request: IRequest) -> MatchInfo:
        '''
        Resolve a request
        '''
        request.record('start')
        result = None
        try:
            result = await self.real_resolve(request)
        except HTTPException as exc:
            await abort(request)
            return BasicMatchInfo(request, exc)
        except Exception as e:
            logger.error("Exception on resolve execution", exc_info=e, request=request)
            await abort(request)
            raise e
        if result is not None:
            return result
        else:
            await abort(request)
            return BasicMatchInfo(request, HTTPNotFound())

    @profilable
    async def real_resolve(self, request: IRequest) -> MatchInfo:
        """Main function to resolve a request."""
        security = get_adapter(request, IInteraction)

        if request.method not in app_settings['http_methods']:
            raise HTTPMethodNotAllowed()
        method = app_settings['http_methods'][request.method]

        language = language_negotiation(request)
        language_object = language(request)

        try:
            resource, tail = await self.traverse(request)
        except ConflictError:
            # can also happen from connection errors so we bubble this...
            raise
        except Exception as _exc:
            request.resource = request.tail = None
            request.exc = _exc
            data = {
                'success': False,
                'exception_message': str(_exc),
                'exception_type': getattr(type(_exc), '__name__', str(type(_exc))),  # noqa
            }
            if app_settings.get('debug'):
                data['traceback'] = traceback.format_exc()
            # XXX should only should traceback if in some sort of dev mode?
            raise HTTPBadRequest(text=ujson.dumps(data))

        request.record('traversed')

        await notify(ObjectLoadedEvent(resource))
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
        request.record('authentication')

        translator = query_adapter(language_object, ITranslated,
                                   args=[resource, request])
        if translator is not None:
            resource = translator.translate()

        # Add anonymous participation
        if len(security.participations) == 0:
            security.add(AnonymousParticipation(request))

        # container registry lookup
        try:
            view = query_multi_adapter(
                (resource, request), method, name=view_name)
        except AttributeError:
            view = None

        request.found_view = view
        request.view_name = view_name

        # Traverse view if its needed
        if traverse_to is not None and view is not None:
            if not ITraversableView.providedBy(view):
                return None
            else:
                try:
                    view = await view.publish_traverse(traverse_to)
                except KeyError:
                    return None  # not found, it's okay.
                except Exception as e:
                    logger.error("Exception on view execution", exc_info=e,
                                 request=request)
                    return None

        permission = get_utility(IPermission, name='guillotina.AccessContent')

        if not security.check_permission(permission.id, resource):
            # Check if its a CORS call:
            if IOPTIONS != method:
                # Check if the view has permissions explicit
                if view is None or not view.__allow_access__:
                    logger.warning("No access content {content} with {auths}".format(
                        content=resource,
                        auths=str([x.principal.id
                                   for x in security.participations])),
                        request=request)
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
                               for x in security.participations])),
                    request=request)
                raise HTTPUnauthorized()

        request.record('authorization')

        renderer = content_type_negotiation(request, resource, view)
        renderer_object = renderer(request)

        rendered = query_multi_adapter(
            (renderer_object, view, request), IRendered)

        if rendered is not None:
            return MatchInfo(resource, request, view, rendered)
        else:
            return None

    async def traverse(self, request: IRequest) -> IResource:
        """Wrapper that looks for the path based on aiohttp API."""
        path = tuple(p for p in request.path.split('/') if p)
        root = self._root
        return await traverse(request, root, path)

    @profilable
    async def apply_authorization(self, request: IRequest):
        # User participation
        participation = IParticipation(request)
        # Lets extract the user from the request
        await participation()
        if participation.principal is not None:
            request.security.add(participation)
