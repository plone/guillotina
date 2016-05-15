from BTrees._OOBTree import OOBTree


class Container(OOBTree):
    @property
    def __parent__(self):
        return getattr(self, '_v_parent', None)

    async def __getchild__(self, name):
        if name not in self:
            self[name] = Container()
            self[name]['__name__'] = name
            self[name]['__visited__'] = Length()
        self[name]._v_parent = self
        return self[name]