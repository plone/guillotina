from guillotina.interfaces.files import ICloudFileField
from guillotina.interfaces.files import IFileField
from guillotina.schema import Object
from zope.interface import implementer


class ICloudPreviewImageFileField(ICloudFileField):
    """Preview on the cloud file"""


@implementer(ICloudPreviewImageFileField)
class CloudPreviewImageFileField(Object):
    schema = IFileField

    def __init__(self, **kw):
        self.file = kw.get("file", None)
        super().__init__(schema=self.schema, **kw)

    def get(self, object):
        if hasattr(self.file, "previews") and self.__name__ in self.file.previews:
            return self.file.previews[self.__name__]

    def set(self, object, value):
        if self.readonly:
            raise TypeError(
                "Can't set values on read-only fields "
                "(name=%s, class=%s.%s)"
                % (self.__name__, object.__class__.__module__, object.__class__.__name__)
            )
        if self.file is None:
            return

        if not hasattr(self.file, "previews"):
            self.file.previews = {}

        self.file.previews[self.__name__] = value
