from typing import Any
from zope.interface.interface import Element
from zope.interface.interface import TAGGED_DATA

import sys


class DirectiveClass(type):
    """A Directive is used to apply tagged values to a Schema
    """

    def __init__(self, name, bases, attrs):
        attrs.setdefault("finalize", None)
        super(DirectiveClass, self).__init__(name, bases, attrs)
        self.__instance = super(DirectiveClass, self).__call__()

    def __call__(self, *args, **kw):
        instance = self.__instance
        frame = sys._getframe(1)
        tags = frame.f_locals.setdefault(TAGGED_DATA, {})
        value = instance.factory(*args, **kw)
        instance.store(tags, value)
        return self

    def apply(self, IClass, *args, **kw):  # noqa: N803
        instance = self.__instance
        existing = Element.queryTaggedValue(IClass, instance.key, default=None)
        tags = {}
        if existing:
            tags[instance.key] = existing
        value = instance.factory(*args, **kw)
        instance.store(tags, value)
        Element.setTaggedValue(IClass, instance.key, tags[instance.key])
        # IClass.setTaggedValue(instance.key, tags[instance.key])
        return self


Directive: Any = DirectiveClass("Directive", (), dict(__module__="guillotina.directives"))


class MetadataListDirective(Directive):
    """Store a list value in the tagged value under the key.
    """

    key: str

    def store(self, tags, value):
        tags.setdefault(self.key, []).extend(value)


def merged_tagged_value_list(schema, name):
    """Look up the tagged value 'name' in schema and all its bases, assuming
    that the value under 'name' is a list. Return a list that consists of
    all elements from all interfaces and base interfaces, with values from
    more-specific interfaces appearing at the end of the list.
    """
    tv = []
    for iface in reversed(schema.__iro__):
        tv.extend(Element.queryTaggedValue(iface, name, default=[]))
    return list(set(tv))


class MetadataDictDirective(Directive):
    """Store a dict value in the tagged value under the key.
    """

    key: str

    def store(self, tags, value):
        tags.setdefault(self.key, {}).update(value)


def merged_tagged_value_dict(schema, name):
    """Look up the tagged value 'name' in schema and all its bases, assuming
    that the value under 'name' is a dict. Return a dict that consists of
    all dict items, with those from more-specific interfaces overriding those
    from more-general ones.
    """
    tv = {}
    for iface in reversed(schema.__iro__):
        tv.update(Element.queryTaggedValue(iface, name, default={}))
    return tv


class read_permission(MetadataDictDirective):  # noqa: N801
    """Directive used to set a field read permission
    """

    key = "guillotina.directives.read-permissions"

    def factory(self, **kw):
        return kw


class write_permission(read_permission):  # noqa: N801
    """Directive used to set a field write permission
    """

    key = "guillotina.directives.write-permissions"


class metadata(MetadataListDirective):  # noqa: N801
    """
    define data to be included and stored with the indexing data
    but is not able to be queried
    """

    key = "guillotina.directives.metadata"

    def factory(self, *names):
        return names


class index_field(MetadataDictDirective):  # noqa: N801
    """
    Directive used to set indexed attributes.

    Allowed options:
        - type
        - accessor
    """

    key = "guillotina.directives.index"

    allowed_types = (
        "searchabletext",
        "text",
        "keyword",
        "textkeyword",
        "int",
        "date",
        "boolean",
        "binary",
        "object",
        "float",
        "long",
        "nested",
        "completion",
        "path",
    )

    def factory(self, name, **kw):
        if "fields" not in kw and "field" in kw:
            # be able to specify multiple fields that affect indexing operations
            kw["fields"] = [kw["field"]]
        kw.setdefault("type", "text")
        if kw.get("type") not in self.allowed_types:
            raise Exception(
                "Invalid index type {}. Avilable types are: {}".format(name, ", ".join(self.allowed_types))
            )
        return {name: kw}

    @classmethod
    def with_accessor(cls, *args, **kwargs):
        """
        decorator to specify a different method to get the data
        """

        def _func(func):
            kwargs["accessor"] = func
            cls.apply(*args, **kwargs)  # pylint: disable=E1101
            return func

        return _func


index = index_field  # b/w compat
