from guillotina.interfaces import ICloudFileField
from guillotina.interfaces import IFile
from guillotina.schema import Object
from zope.interface import implementer


@implementer(ICloudFileField)
class CloudFileField(Object):
    """
    A cloud file hosted file.

    Its configured on config.json with :

    "cloud_storage": "guillotina.interfaces.IS3FileField"

    or

    "cloud_storage": "guillotina_gcloudstorage.interfaces.IGCloudFileField"

    """

    schema = IFile

    def __init__(self, **kw):
        super().__init__(schema=self.schema, **kw)
