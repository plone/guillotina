from guillotina import configure
from guillotina import schema
from guillotina.annotations import AnnotationData
from guillotina.component import query_adapter
from guillotina.exceptions import ValueDeserializationError
from guillotina.fields.interfaces import IBucketListField
from guillotina.fields.interfaces import IPatchFieldOperation
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IContentBehavior
from zope.interface import implementer
from guillotina.fields import patch


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

    def __init__(self, *args, value_type=None, bucket_len=5000, **kwargs):
        self.bucket_len = bucket_len
        self.value_type = value_type
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


@configure.value_deserializer(IBucketListField)
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
def dynamic_list_converter(value):
    if value is None:
        return
    return {
        'len': len(value),
        'buckets': len(value.annotations_metadata)
    }


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
                annotation_prefix='bucketlist-' + self.field.__key_name__)
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
