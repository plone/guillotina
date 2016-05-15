from BTrees._OOBTree import OOBTree
from BTrees.Length import Length
from plone.server.exceptions import NoElement


class Container(OOBTree):
    @property
    def __parent__(self):
        return getattr(self, '_v_parent', None)

    async def get(self, name):
        import pdb; pdb.set_trace()
        if name not in self:
            raise NoElement()
        self[name]._v_parent = self
        return self[name]
