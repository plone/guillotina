# -*- coding: utf-8 -*-
from BTrees.OOBTree import OOBTree


class Container(OOBTree):
    @property
    def __parent__(self):
        return getattr(self, '_v_parent', None)  # set by traverser
