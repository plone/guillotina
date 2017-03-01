# -*- coding: utf-8 -*-
from guillotina.transactions import get_current_request
from zope.interface import implementer
from zope.security.checker import _available_by_default
from zope.security.checker import CheckerPublic
from zope.security.checker import CheckerPy
from zope.security.checker import TracebackSupplement
from zope.security.interfaces import ForbiddenAttribute
from zope.security.interfaces import IChecker
from zope.security.interfaces import IInteraction
from zope.security.interfaces import Unauthorized


_marker = object()


@implementer(IChecker)
class ViewPermissionChecker(CheckerPy):
    """ This checker proxy is set on traversal to the view.

    The definition is set on the __call__ on Service definition

    """
    def check_setattr(self, obj, name):
        if self.set_permissions:
            permission = self.set_permissions.get(name)
        else:
            permission = None

        if permission is not None:
            if permission is CheckerPublic:
                return  # Public

            request = get_current_request()
            if IInteraction(request).check_permission(permission, obj):
                return  # allowed
            else:
                __traceback_supplement__ = (TracebackSupplement, obj)
                raise Unauthorized(obj, name, permission)

        __traceback_supplement__ = (TracebackSupplement, obj)
        raise ForbiddenAttribute(name, obj)

    def check(self, obj, name):
        permission = self.get_permissions.get(name)
        if permission is not None:
            if permission is CheckerPublic:
                return  # Public
            request = get_current_request()
            if IInteraction(request).check_permission(permission, obj):
                return
            else:
                __traceback_supplement__ = (TracebackSupplement, obj)
                raise Unauthorized(obj, name, permission)
        elif name in _available_by_default:
            return

        if name != '__iter__' or hasattr(obj, name):
            __traceback_supplement__ = (TracebackSupplement, obj)
            raise ForbiddenAttribute(name, obj)

    check_getattr = check

    # IChecker.proxy
    def proxy(self, obj):
        return obj
        # TODO: Figure out, how to not wrap __providedBy__, __call__ etc
        # Once they have been checked
