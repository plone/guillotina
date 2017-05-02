from guillotina import configure
from guillotina.component import queryMultiAdapter
from guillotina.db.interfaces import IConflictResolver
from guillotina.exceptions import UnresolvableConflict
from guillotina.interfaces import IAnnotationData
from guillotina.interfaces import IResource
from guillotina.interfaces import IResourceFieldSerializer
from guillotina.utils import apply_coroutine


MISSING_VALUE = object()


def get_change_key(field):
    return '{}.{}'.format(field.interface.__identifier__, field.__name__)


def record_object_change(obj, field=None, value=MISSING_VALUE, key=None):
    if key is None:
        key = get_change_key(field)
    if key in obj.__changes__:
        # already registered, we're good
        return
    obj.__changes__[key] = {
        'field': field,
        'value': value
    }


class BaseResolver:

    def __init__(self, object_to_write, conflicted_object):
        # object we're trying to write
        # This will be an object registered in our transaction so it will have
        # a reference to our transaction object
        self.object_to_write = object_to_write

        # object from db we're in conflict with
        # This will not have a transaction reference
        self.conflicted_object = conflicted_object

    async def resolve(self):
        """
        return our object with resolved conflicts.
        This would mean it has the merged data from other...
        """
        raise UnresolvableConflict(self.object_to_write, self.conflicted_object)


@configure.adapter(
    for_=(IResource, IResource),
    provides=IConflictResolver)
class ResourceConflictResolver(BaseResolver):

    async def resolve(self):
        # we're looking at a snapshot of what the value was originally before
        # it started getting edited.
        # so we look to see if data in the conflicted_object differs from
        # what is registered here because then we know that the data
        # was changed in both places and it's a legit conflict
        for key, change in self.object_to_write.__changes__.items():
            field = change['field']
            original_value = change['value']
            field_serializer = queryMultiAdapter(
                (field, self.conflicted_object, self.conflicted_object),
                IResourceFieldSerializer)
            conflicted_value = await field_serializer.get_value(default=MISSING_VALUE)
            if conflicted_value is not MISSING_VALUE and conflicted_value != original_value:
                # field also changed in conflicted object, this is not resolvable
                raise UnresolvableConflict(self.object_to_write, self.conflicted_object)

            # update conflicted object with new value
            field_serializer = queryMultiAdapter(
                (field, self.object_to_write, self.object_to_write),
                IResourceFieldSerializer)
            new_value = await field_serializer.get_value(default=MISSING_VALUE)
            try:
                await apply_coroutine(field.set, self.conflicted_object, new_value)
            except Exception:
                setattr(self.conflicted_object, field.__name__, new_value)

        # no conflicts found
        # we use the conflicted object as the new replacement object.
        # why? well, because we don't know what changed specifically on the
        # conflicted object, so we use it and apply the changes here onto it.
        return self.conflicted_object


@configure.adapter(
    for_=(IAnnotationData, IAnnotationData),
    provides=IConflictResolver)
class AnnotationConflictResolver(BaseResolver):

    async def resolve(self):
        for key, change in self.object_to_write.__changes__.items():
            original_value = change['value']
            if key in self.conflicted_object:
                conflicted_value = self.conflicted_object[key]
                if conflicted_value != original_value:
                    # field also changed in conflicted object, this is not resolvable
                    raise UnresolvableConflict(self.object_to_write,
                                               self.conflicted_object)
            self.conflicted_object[key] = self.object_to_write[key]

        # conflicted_object was updated with changed data
        return self.conflicted_object
