
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

import sys


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

    def get_existing_value(self, field_context):
        existing = getattr(field_context, self.field.__name__, None)
        if existing is None:
            existing = BucketListValue(
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
        self.annotations_metadata = {
            0: {
                'len': 0,
                'range': (0, sys.maxunicode)
            }
        }
        self.annotation_prefix = annotation_prefix
        self.bucket_len = bucket_len

    def __len__(self):
        total = 0
        for metadata in self.annotations_metadata.values():
            total += metadata.get('len', 0)
        return total

    def _find_annotation_index(self, key):
        first_chr = ord(str(key)[0])
        for idx, metadata in self.annotations_metadata.items():
            start_chr, end_chr = metadata['range']
            if first_chr >= start_chr and first_chr <= end_chr:
                return idx

    def _get_annotation_name(self, index):
        return f'{self.annotation_prefix}{index}'

    async def get_annotation(self, context, key, create=True):
        annotation_index = self._find_annotation_index(key)
        if annotation_index is None:
            raise KeyError(f'Could not find annotation index for key: {key}')
        annotation_name = self.get_annotation_name(annotation_index)

        annotations_container = IAnnotations(context)
        annotation = annotations_container.get(annotation_name, _default)
        if annotation is _default:
            annotation = await annotations_container.async_get(
                annotation_name, _default)
        if annotation is _default:
            if not create:
                return
            annotation = AnnotationData()
            await annotations_container.async_set(annotation_name, annotation)
        if annotation_index not in self.annotations_metadata:
            self.annotations_metadata[annotation_index] = {}
        return annotation

    async def assign(self, context, key, value):
        annotation = await self.get_annotation(context, key)
        annotation_idx = self._find_annotation_index(key)
        annotation_metadata = self.annotations_metadata[annotation_idx]

        if len(annotation) >= self.bucket_len:
            # split bucket before we append here...
            bstart, bend = annotation_metadata['range']
            new_bend = int(bend / 2)
            annotation_metadata['range'] = (bstart, new_bend)

            new_annotation_index = len(self.annotations_metadata)
            new_ann_start = new_bend + 1
            new_annotation_metadata = self.annotations_metadata[new_annotation_index] = {
                'len': 0,
                'range': (new_ann_start, bend)
            }
            new_annotation = await self.get_annotation(context, key)

            # split dictionaries up
            for k in list(annotation.keys()):
                first_chr = ord(str(k)[0])
                if first_chr >= new_ann_start:
                    new_annotation[k] = annotation[k]
                    del annotation[k]

            annotation._p_register()
            new_annotation_metadata['len'] = len(new_annotation)
            annotation_metadata['len'] = len(new_annotation)

            curr_key_first_chr = ord(str(key)[0])
            if curr_key_first_chr >= new_ann_start:
                annotation = new_annotation
                annotation_metadata = new_annotation_metadata
                annotation_idx = self._find_annotation_index(key)

        annotation[key] = value
        annotation_metadata[annotation_idx] = len(annotation)
        annotation._p_register()

    async def get(self, context, key):
        annotation = await self.get_annotation(context, key, create=False)
        if annotation is None:
            return None
        return annotation.get(key)

    async def remove(self, context, key):
        annotation = await self.get_annotation(context, key, create=False)
        if annotation is None:
            return

        if key in annotation:
            del annotation[key]
            annotation._p_register()
            annotation_idx = self._find_annotation_index(key)
            self.annotations_metadata[annotation_idx]['len'] = len(annotation)


@implementer(IBucketDictField)
class BucketDictField(BucketListField):
    key_type = value_type = None

    def __init__(self, *args, key_type=None, value_type=None,
                 bucket_len=1000, annotation_prefix='bucketdict-', **kwargs):
        self.key_type = key_type
        super().__init__(*args, value_type=value_type, bucket_len=1000,
                         annotation_prefix=annotation_prefix, **kwargs)


@configure.adapter(
    for_=IBucketDictField,
    provides=IPatchFieldOperation,
    name='assign')
class PatchBucketDictSet(PatchBucketListAppend):
    async def __call__(self, field_context, context, value):
        if 'key' not in value or 'value' not in value:
            raise ValueDeserializationError(self.field, value, 'Not valid patch value')

        if self.field.key_type:
            self.field.key_type.validate(value['key'])

        existing = self.get_existing_value(field_context)
        existing_item = await existing.get(value['key'])

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

            existing_item = await existing.get(item['key'])

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


@configure.value_serializer(BucketDictValue)
@configure.value_serializer(BucketListValue)
def value_converter(value):
    if value is None:
        return
    return {
        'len': len(value),
        'buckets': len(value.annotations_metadata)
    }
