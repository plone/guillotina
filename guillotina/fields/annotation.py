from guillotina import configure
from guillotina import schema
from guillotina.annotations import AnnotationData
from guillotina.component import query_adapter
from guillotina.exceptions import ValueDeserializationError
from guillotina.fields import patch
from guillotina.fields.interfaces import IBucketDictField
from guillotina.fields.interfaces import IBucketListField
from guillotina.fields.interfaces import IPatchFieldOperation
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IContentBehavior
from zope.interface import implementer

import bisect
import time
import typing
import uuid


_default = object()


class BucketListValue:

    def __init__(self, annotation_prefix='bucketlist-', bucket_len=5000):
        self.current_annotation_index = 0
        self.annotations_metadata = {}
        self.annotation_prefix = annotation_prefix
        self.bucket_len = bucket_len

    def get_annotation_name(self, index):
        return f'{self.annotation_prefix}{index}'

    async def get_annotation(self, context, annotation_index, create=True):
        annotation_name = self.get_annotation_name(annotation_index)
        annotations_container = IAnnotations(context)
        annotation = annotations_container.get(annotation_name, _default)
        if annotation is _default:
            annotation = await annotations_container.async_get(
                annotation_name, _default)
        if annotation is _default:
            if not create:
                return
            # create
            annotation = AnnotationData()
            annotation.update({
                'items': []
            })
            await annotations_container.async_set(annotation_name, annotation)
        if annotation_index not in self.annotations_metadata:
            self.annotations_metadata[annotation_index] = {}
        return annotation

    async def append(self, context, value):
        if self.current_annotation_index in self.annotations_metadata:
            metadata = self.annotations_metadata[self.current_annotation_index]
            if metadata.get('len', 0) >= self.bucket_len:
                # split here
                self.current_annotation_index += 1

        annotation = await self.get_annotation(context, self.current_annotation_index)
        metadata = self.annotations_metadata[self.current_annotation_index]
        metadata['len'] = metadata.get('len', 0) + 1
        annotation['items'].append(value)
        annotation._p_register()

    async def extend(self, context, value):
        for item in value:
            await self.append(context, item)

    def __len__(self):
        total = 0
        for metadata in self.annotations_metadata.values():
            total += metadata.get('len', 0)
        return total

    async def get(self, context, bucket_index, item_index):
        annotation = await self.get_annotation(
            context, bucket_index, create=False)
        if annotation is None:
            return

        try:
            return annotation['items'][item_index]
        except IndexError:
            pass

    async def remove(self, context, bucket_index, item_index):
        annotation = await self.get_annotation(
            context, bucket_index, create=False)
        if annotation is None:
            return

        if len(annotation['items']) >= item_index:
            del annotation['items'][item_index]
            metadata = self.annotations_metadata[bucket_index]
            metadata['len'] = metadata.get('len', 0) - 1
            annotation._p_register()

    async def iter_buckets(self, context):
        for index in sorted(self.annotations_metadata.keys()):
            annotation_name = self.get_annotation_name(index)
            annotations_container = IAnnotations(context)
            annotation = annotations_container.get(annotation_name, _default)
            if annotation is _default:
                annotation = await annotations_container.async_get(
                    annotation_name, _default)
                if annotation is _default:
                    continue
            yield annotation

    async def iter_items(self, context):
        async for bucket in self.iter_buckets(context):
            for item in bucket['items']:
                yield item


@implementer(IBucketListField)
class BucketListField(schema.Field):
    value_type = None

    def __init__(self, *args, value_type=None, bucket_len=5000,
                 annotation_prefix='bucketlist-', **kwargs):
        self.bucket_len = bucket_len
        self.value_type = value_type
        self.annotation_prefix = annotation_prefix
        super().__init__(*args, **kwargs)

    async def set(self, obj, value):
        obj._p_register()
        if IContentBehavior.providedBy(obj):
            anno_context = obj.__dict__['context']
            self.__key_name__ = obj.__dict__['schema'].__identifier__ + '.' + self.__name__
        else:
            anno_context = obj
            self.__key_name__ = self.__name__

        operation_name = value['op']
        bound_field = self.bind(obj)
        operation = query_adapter(bound_field, IPatchFieldOperation, name=operation_name)
        await operation(obj, anno_context, value['value'])


@configure.adapter(
    for_=IBucketListField,
    provides=IPatchFieldOperation,
    name='append')
class PatchBucketListAppend(patch.PatchListAppend):
    value_factory = BucketListValue

    def get_existing_value(self, field_context):
        existing = getattr(field_context, self.field.__name__, None)
        if existing is None:
            existing = self.value_factory(
                bucket_len=self.field.bucket_len,
                annotation_prefix=self.field.annotation_prefix + self.field.__key_name__)
            setattr(field_context, self.field.__name__, existing)
        return existing

    async def __call__(self, field_context, context, value):
        value = self.get_value(value, None)
        if self.field.value_type:
            self.field.value_type.validate(value)
        existing = self.get_existing_value(field_context)
        await existing.append(context, value)


@configure.adapter(
    for_=IBucketListField,
    provides=IPatchFieldOperation,
    name='extend')
class PatchBucketListExtend(PatchBucketListAppend):
    async def __call__(self, field_context, context, value):
        existing = self.get_existing_value(field_context)
        if not isinstance(value, list):
            raise ValueDeserializationError(self.field, value, 'Not valid list')

        values = []
        for item in value:
            if self.field.value_type:
                item_value = self.get_value(
                    item, None, field_type=self.field.value_type)
                self.field.value_type.validate(item_value)
                values.append(item_value)

        await existing.extend(context, values)


@configure.adapter(
    for_=IBucketListField,
    provides=IPatchFieldOperation,
    name='del')
class PatchBucketListRemove(PatchBucketListAppend):
    async def __call__(self, field_context, context, value):
        existing = self.get_existing_value(field_context)
        if 'bucket_index' not in value or 'item_index' not in value:
            raise ValueDeserializationError(self.field, value, 'Not valid remove request')
        try:
            await existing.remove(context, value['bucket_index'], value['item_index'])
        except IndexError:
            raise ValueDeserializationError(self.field, value, 'Not valid index value')


class BucketDictValue:
    '''
    metadata for managing bucket dict values
    '''

    def __init__(self, annotation_prefix='bucketdict-', bucket_len=1000):
        self.buckets = [
            {
                'id': uuid.uuid4().hex,  # random gen
                'len': 0,
                'created': time.time(),
                'start': None  # first one has no bound here
            }
        ]
        self.annotation_prefix = annotation_prefix
        self.bucket_len = bucket_len

    def _find_bucket(self, key) -> typing.Tuple[int, dict]:
        found = (0, self.buckets[0])
        for idx, bucket in enumerate(self.buckets[1:]):
            if key < bucket['start']:
                # searched as far as we need to go
                break
            found = (idx + 1, bucket)
        return found

    def get_annotation_name(self, bucket_id: str) -> str:
        return f'{self.annotation_prefix}{bucket_id}'

    async def get_annotation(self, context, key=None,
                             anno_id=None, create=True) -> typing.Optional[AnnotationData]:
        if anno_id is None:
            bidx, bucket = self._find_bucket(key)
            annotation_name = self.get_annotation_name(bucket['id'])
        else:
            annotation_name = self.get_annotation_name(anno_id)

        annotations_container = IAnnotations(context)
        annotation = annotations_container.get(annotation_name, _default)
        if annotation is _default:
            annotation = await annotations_container.async_get(
                annotation_name, _default)
        if annotation is _default:
            if not create:
                return
            annotation = AnnotationData({
                'keys': [],
                'values': []
            })
            await annotations_container.async_set(annotation_name, annotation)
        return annotation

    async def assign(self, context, key, value):
        annotation = await self.get_annotation(context, key)

        if len(annotation['keys']) >= self.bucket_len:
            # we need to split this bucket
            bidx, bucket = self._find_bucket(key)
            middle_idx = int(self.bucket_len / 2)
            middle_key = annotation['keys'][middle_idx]
            new_bucket = {
                'id': uuid.uuid4().hex,
                'start': middle_key,
                'created': time.time(),
            }
            self.buckets.insert(bidx + 1, new_bucket)
            new_annotation = await self.get_annotation(context, middle_key)
            # rebalance now
            new_annotation['keys'] = annotation['keys'][middle_idx:]
            new_annotation['values'] = annotation['values'][middle_idx:]
            new_bucket['len'] = len(new_annotation['keys'])

            annotation['keys'] = annotation['keys'][:middle_idx]
            annotation['values'] = annotation['values'][:middle_idx]
            bucket['len'] = len(annotation['keys'])

            # get annotation for this key again
            annotation = await self.get_annotation(context, key)

        if key in annotation['keys']:
            # change existing value
            idx = annotation['keys'].index(key)
            annotation['values'][idx] = value
        else:
            insert_idx = bisect.bisect_left(annotation['keys'], key)
            annotation['keys'].insert(insert_idx, key)
            annotation['values'].insert(insert_idx, value)
            _, bucket = self._find_bucket(key)
            bucket['len'] = len(annotation['keys'])
        annotation._p_register()

    async def get(self, context, key):
        annotation = await self.get_annotation(context, key, create=False)
        if annotation is None:
            return None
        try:
            idx = annotation['keys'].index(key)
        except ValueError:
            return None
        return annotation['values'][idx]

    async def remove(self, context, key):
        annotation = await self.get_annotation(context, key, create=False)
        if annotation is None:
            return

        try:
            idx = annotation['keys'].index(key)
        except ValueError:
            return None
        del annotation['keys'][idx]
        del annotation['values'][idx]
        _, bucket = self._find_bucket(key)
        bucket['len'] = len(annotation['keys'])
        annotation._p_register()

    def __len__(self):
        total = 0
        for bucket in self.buckets:
            total += bucket.get('len', 0)
        return total


@implementer(IBucketDictField)
class BucketDictField(BucketListField):
    key_type = value_type = None

    def __init__(self, *args, key_type=None, value_type=None,
                 bucket_len=1000, annotation_prefix='bucketdict-', **kwargs):
        self.key_type = key_type
        super().__init__(*args, value_type=value_type, bucket_len=bucket_len,
                         annotation_prefix=annotation_prefix, **kwargs)


@configure.adapter(
    for_=IBucketDictField,
    provides=IPatchFieldOperation,
    name='assign')
class PatchBucketDictSet(PatchBucketListAppend):
    value_factory = BucketDictValue

    async def __call__(self, field_context, context, value):
        if 'key' not in value or 'value' not in value:
            raise ValueDeserializationError(self.field, value, 'Not valid patch value')

        if self.field.key_type:
            self.field.key_type.validate(value['key'])

        existing = self.get_existing_value(field_context)
        existing_item = await existing.get(context, value['key'])

        new_value = self.get_value(value['value'], existing_item)
        if self.field.value_type:
            self.field.value_type.validate(new_value)

        await existing.assign(context, value['key'], new_value)


@configure.adapter(
    for_=IBucketDictField,
    provides=IPatchFieldOperation,
    name='update')
class PatchBucketDictExtend(PatchBucketDictSet):
    async def __call__(self, field_context, context, value):
        if not isinstance(value, list):
            raise ValueDeserializationError(
                self.field, value,
                f'Invalid type patch data, must be list of updates')

        existing = self.get_existing_value(field_context)

        for item in value:
            if 'key' not in item or 'value' not in item:
                raise ValueDeserializationError(self.field, value, 'Not valid patch value')

            if self.field.key_type:
                self.field.key_type.validate(item['key'])

            existing_item = await existing.get(context, item['key'])

            new_value = self.get_value(item['value'], existing_item)
            if self.field.value_type:
                self.field.value_type.validate(new_value)

            await existing.assign(context, item['key'], new_value)


@configure.adapter(
    for_=IBucketDictField,
    provides=IPatchFieldOperation,
    name='del')
class PatchBucketDictDel(PatchBucketDictSet):
    async def __call__(self, field_context, context, value):
        if self.field.key_type:
            self.field.key_type.validate(value)

        existing = self.get_existing_value(field_context)
        try:
            await existing.remove(context, value)
        except (IndexError, KeyError):
            raise ValueDeserializationError(self.field, value, 'Not valid index value')


@configure.value_deserializer(IBucketListField)
@configure.value_deserializer(IBucketDictField)
def field_converter(field, value, context):
    if not isinstance(value, dict):
        raise ValueDeserializationError(field, value, 'Not an object')
    operation_name = value.get('op', 'undefined')
    operation = query_adapter(field, IPatchFieldOperation, name=operation_name)
    if operation is None:
        raise ValueDeserializationError(
            field, value, f'"{operation_name}" not a valid operation')
    if 'value' not in value:
        raise ValueDeserializationError(
            field, value, f'Mising value')
    return value


@configure.value_serializer(BucketListValue)
def value_converter(value):
    if value is None:
        return
    return {
        'len': len(value),
        'buckets': len(value.annotations_metadata)
    }


@configure.value_serializer(BucketDictValue)
def value_dict_converter(value):
    return {
        'len': len(value),
        'buckets': len(value.buckets)
    }
