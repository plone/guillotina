# -*- coding: utf-8 -*-
from plone.server.interfaces import CATALOG_KEY
from plone.server.interfaces import FIELDSETS_KEY
from plone.server.interfaces import INDEX_KEY
from plone.server.interfaces import READ_PERMISSIONS_KEY
from plone.server.interfaces import WRITE_PERMISSIONS_KEY
from zope.interface.interface import TAGGED_DATA

import sys


class Fieldset(object):

    def __init__(self, __name__, label=None, description=None, fields=None):
        self.__name__ = __name__
        self.label = label or __name__
        self.description = description

        if fields:
            self.fields = fields
        else:
            self.fields = []

    def __repr__(self):
        return "<Fieldset '%s' of %s>" % (self.__name__, ', '.join(self.fields))  # noqa


class DirectiveClass(type):
    """A Directive is used to apply tagged values to a Schema
    """

    def __init__(self, name, bases, attrs):
        attrs.setdefault('finalize', None)
        super(DirectiveClass, self).__init__(name, bases, attrs)
        self.__instance = super(DirectiveClass, self).__call__()

    def __call__(self, *args, **kw):
        instance = self.__instance
        frame = sys._getframe(1)
        tags = frame.f_locals.setdefault(TAGGED_DATA, {})
        value = instance.factory(*args, **kw)
        instance.store(tags, value)

Directive = DirectiveClass('Directive', (), dict(__module__='plone.server.directives',),)  # noqa


class MetadataListDirective(Directive):
    """Store a list value in the tagged value under the key.
    """
    key = None

    def store(self, tags, value):
        tags.setdefault(self.key, []).extend(value)


def mergedTaggedValueList(schema, name):
    """Look up the tagged value 'name' in schema and all its bases, assuming
    that the value under 'name' is a list. Return a list that consists of
    all elements from all interfaces and base interfaces, with values from
    more-specific interfaces appearing at the end of the list.
    """
    tv = []
    for iface in reversed(schema.__iro__):
        tv.extend(iface.queryTaggedValue(name, []))
    return tv


class MetadataDictDirective(Directive):
    """Store a dict value in the tagged value under the key.
    """
    key = None

    def store(self, tags, value):
        tags.setdefault(self.key, {}).update(value)


def mergedTaggedValueDict(iface, name):
    """Look up the tagged value 'name' in schema and all its bases, assuming
    that the value under 'name' is a dict. Return a dict that consists of
    all dict items, with those from more-specific interfaces overriding those
    from more-general ones.
    """
    tv = {}
    for iface in reversed(iface.__iro__):
        tv.update(iface.queryTaggedValue(name, {}))
    return tv


class fieldset(MetadataListDirective):
    """Directive used to create fieldsets
    """
    key = FIELDSETS_KEY

    def factory(self, name, label=None, description=None, fields=None, **kw):
        fieldset = Fieldset(name, label=label, description=description, fields=fields)  # noqa
        for (key, value) in kw.items():
            setattr(fieldset, key, value)
        return [fieldset]


class read_permission(MetadataDictDirective):
    """Directive used to set a field read permission
    """
    key = READ_PERMISSIONS_KEY

    def factory(self, **kw):
        return kw


class write_permission(read_permission):
    """Directive used to set a field write permission
    """
    key = WRITE_PERMISSIONS_KEY


class catalog(MetadataDictDirective):
    """Directive used to set a field read permission
    """
    key = CATALOG_KEY

    def factory(self, **kw):
        return kw


class index(MetadataDictDirective):
    """Directive used to set a field read permission
    """
    key = INDEX_KEY

    def factory(self, **kw):
        return kw
