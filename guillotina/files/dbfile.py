from .field import BaseCloudFile
from guillotina.blob import Blob
from guillotina.interfaces import IDBFile
from typing import Optional
from zope.interface import implementer


@implementer(IDBFile)
class DBFile(BaseCloudFile):
    """File stored in a DB using blob storage"""

    _blob: Optional[Blob] = None

    @property
    def valid(self):
        return self._blob is not None

    def get_actual_size(self):
        if self._blob is not None:
            return self._blob.size
        return 0

    @property
    def size(self):
        if self._blob is not None:
            return self._blob.size
        return 0

    @size.setter
    def size(self, val):
        pass

    @property
    def chunks(self) -> int:
        if self._blob is not None:
            return self._blob.chunks
        return 0
