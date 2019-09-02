from guillotina import configure
from guillotina import task_vars
from guillotina.component import adapter
from guillotina.interfaces import IAbsoluteURL
from guillotina.interfaces import ILocation
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource
from guillotina.interfaces import IView
from guillotina.utils import get_current_request
from guillotina.utils import get_url
from zope.interface import implementer


def get_physical_path(context):
    parts = [context.__name__]
    parent = context.__parent__
    while parent is not None and parent.__name__ is not None:
        parts.append(parent.__name__)
        parent = parent.__parent__
    parts.append("")
    return [x for x in reversed(parts)]


@adapter(IResource, IRequest)
@implementer(IView, ILocation)
class View:

    __name__ = "view"

    # An attribute that marks that a view should not
    # be unauthorized by AccessContent on the object
    # Should always be False unless you provide auth
    # by another mechanism on the view

    __allow_access__ = False

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def __parent__(self):
        return self.context

    async def __call__(self):
        return {"context": str(self.context), "path": "/".join(get_physical_path(self.context))}


@configure.adapter(for_=(IResource, IRequest), provides=IAbsoluteURL)  # noqa: N801
class Absolute_URL(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, relative=False, container_url=False):
        if container_url:
            # we want the url relative to container so remove the container
            path = [x for x in get_physical_path(self.context)]
            path.pop(1)
            path = "/".join(path)
        else:
            path = "/".join(get_physical_path(self.context))

        if container_url:
            return path
        elif relative:
            db = task_vars.db.get()
            return "/" + db.id + path
        else:
            db = task_vars.db.get()
            return get_url(self.request, db.id + path)


@configure.adapter(for_=IResource, provides=IAbsoluteURL)  # noqa: N801
class Absolute_URL_ObtainRequest(Absolute_URL):
    def __init__(self, context):
        request = get_current_request()
        super().__init__(context, request)
