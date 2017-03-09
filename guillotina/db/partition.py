from guillotina import configure
from guillotina.db.interfaces import IPartition
from guillotina.interfaces import IResource


@configure.adapter(
    for_=IResource,
    provides=IPartition)
class PartitionDataAdapter(object):

    def __init__(self, content):
        self.content = content

    def __call__(self):
        if hasattr(self.content, 'parent_datasource'):
            return self.content.parent_datasource
        else:
            return None
