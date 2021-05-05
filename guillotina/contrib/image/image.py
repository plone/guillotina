from guillotina.contrib.image.interfaces import IImageFile
from guillotina.interfaces.files import ICloudFileField
from guillotina.schema import Object
from zope.interface import implementer


class ICloudImageFileField(ICloudFileField):
    """Image on the cloud file"""


@implementer(ICloudImageFileField)
class CloudImageFileField(Object):
    schema = IImageFile

    def __init__(self, **kw):
        super().__init__(schema=self.schema, **kw)

    def set(self, object, value):
        if self.readonly:
            raise TypeError(
                "Can't set values on read-only fields "
                "(name=%s, class=%s.%s)"
                % (self.__name__, object.__class__.__module__, object.__class__.__name__)
            )
        if hasattr(value, "previews"):
            value.previews = {}
        setattr(object, self.__name__, value)
