import asyncio
import logging
import sys

log = logging.getLogger(__name__)


@asyncio.coroutine
def traverse(root, path):
    """ Find resource for path
    :param root: instance of Resource
    :param list path: `('events', 'event_id', 'sets', 'set_id')`
    :return: `(resource, tail)`
    """
    if not path:
        return root, tuple(path)

    path = list(path)
    traverser = root[path.pop(0)]

    while path:
        traverser = traverser[path.pop(0)]

    return (yield from traverser.traverse())


class Traverser:
    _is_coroutine = True

    def __init__(self, resource, path):
        self.resource = resource
        self.path = path

    def __getitem__(self, item):
        return Traverser(self.resource, self.path + (item,))

    def __iter__(self):
        """ This object is coroutine
        For this:
            yield from app.get_root()['a']['b']['c']
        """
        resource, tail = yield from self.traverse()

        if tail:
            raise KeyError(tail[0])
        else:
            return resource

    if sys.version_info >= (3, 5):
        __await__ = __iter__

    @asyncio.coroutine
    def traverse(self):
        """ Main traversal algorithm
        :return: tuple `(resource, tail)`
        """
        last, current = None, self.resource
        path = list(self.path)

        while path:
            item = path[0]
            last, current = current, (yield from current.__getchild__(item))

            if current is None:
                return last, tuple(path)

            del path[0]

        return current, tuple(path)


def lineage(resource):
    """ Return a generator representing the lineage
        of the resource object implied by the resource argument
    """
    while resource is not None:
        yield resource
        resource = resource.__parent__


def find_root(resource):
    """ Find root resource
    """
    return list(lineage(resource))[-1]