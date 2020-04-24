from datetime import datetime
from guillotina import fields
from guillotina import schema
from guillotina.component import get_adapter
from guillotina.component import get_multi_adapter
from guillotina.exceptions import ValueDeserializationError
from guillotina.fields import patch
from guillotina.fields.interfaces import IPatchFieldOperation
from guillotina.files.dbfile import DBFile
from guillotina.interfaces import IJSONToValue
from guillotina.interfaces import IResourceDeserializeFromJson
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.json import deserialize_value
from guillotina.json.deserialize_value import schema_compatible
from guillotina.json.serialize_value import json_compatible
from guillotina.json.utils import validate_invariants
from guillotina.schema.exceptions import WrongType
from guillotina.tests.utils import create_content
from guillotina.tests.utils import login
from zope.interface import Interface
from zope.interface import Invalid
from zope.interface.interface import invariant

import pytest
import uuid


async def test_serialize_resource(dummy_request, mock_txn):
    content = create_content()
    serializer = get_multi_adapter((content, dummy_request), IResourceSerializeToJson)
    result = await serializer()
    assert "guillotina.behaviors.dublincore.IDublinCore" in result


async def test_serialize_resource_omit_behavior(dummy_request, mock_txn):
    content = create_content()
    serializer = get_multi_adapter((content, dummy_request), IResourceSerializeToJson)
    result = await serializer(omit=["guillotina.behaviors.dublincore.IDublinCore"])
    assert "guillotina.behaviors.dublincore.IDublinCore" not in result


async def test_serialize_resource_omit_field(dummy_request, mock_txn):
    content = create_content()
    serializer = get_multi_adapter((content, dummy_request), IResourceSerializeToJson)
    result = await serializer(omit=["guillotina.behaviors.dublincore.IDublinCore.creators"])
    assert "creators" not in result["guillotina.behaviors.dublincore.IDublinCore"]


async def test_serialize_resource_include_field(dummy_request, mock_txn):
    from guillotina.test_package import FileContent

    obj = create_content(FileContent, type_name="File")
    obj.file = DBFile(filename="foobar.json", size=25, md5="foobar")
    serializer = get_multi_adapter((obj, dummy_request), IResourceSerializeToJson)
    result = await serializer(include=["guillotina.behaviors.dublincore.IDublinCore.creators"])
    assert "creators" in result["guillotina.behaviors.dublincore.IDublinCore"]
    assert len(result["guillotina.behaviors.dublincore.IDublinCore"]) == 1
    assert "file" not in result


async def test_serialize_omit_main_interface_field(dummy_request, mock_txn):
    from guillotina.test_package import FileContent

    obj = create_content(FileContent, type_name="File")
    obj.file = DBFile(filename="foobar.json", size=25, md5="foobar")
    serializer = get_multi_adapter((obj, dummy_request), IResourceSerializeToJson)
    result = await serializer(omit=["file"])
    assert "file" not in result
    result = await serializer()
    assert "file" in result


async def test_serialize_cloud_file(dummy_request, mock_txn):
    from guillotina.test_package import FileContent, IFileContent
    from guillotina.interfaces import IFileManager

    obj = create_content(FileContent)
    obj.file = DBFile(filename="foobar.json", md5="foobar")

    fm = get_multi_adapter((obj, dummy_request, IFileContent["file"].bind(obj)), IFileManager)
    await fm.dm.load()
    await fm.file_storage_manager.start(fm.dm)

    async def _data():
        yield b'{"foo": "bar"}'

    await fm.file_storage_manager.append(fm.dm, _data(), 0)
    await fm.file_storage_manager.finish(fm.dm)
    await fm.dm.finish()
    value = json_compatible(obj.file)
    assert value["filename"] == "foobar.json"
    assert value["size"] == 14
    assert value["md5"] == "foobar"


async def test_deserialize_cloud_file(dummy_request, mock_txn):
    from guillotina.test_package import IFileContent, FileContent

    obj = create_content(FileContent)
    obj.file = None
    await get_adapter(
        IFileContent["file"].bind(obj),
        IJSONToValue,
        args=["data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7", obj],
    )
    assert isinstance(obj.file, DBFile)
    assert obj.file.size == 42


class IObjectA(Interface):
    foo = schema.Text(required=False)


class IObjectB(Interface):
    bar = schema.Text(required=False)


class INestFieldSchema(Interface):
    foo = schema.Text(required=False)
    bar = schema.Int(required=False)
    foobar_list = schema.List(required=False, value_type=schema.Text())
    nested_int = fields.PatchField(schema.Int(required=False))


class ITestSchema(Interface):

    text = schema.TextLine(required=False)
    integer = schema.Int(required=False)
    floating = schema.Float(required=False)
    list_of_text = schema.List(value_type=schema.TextLine(), required=False)
    tuple_of_text = schema.Tuple(value_type=schema.TextLine(), required=False)
    set_of_text = schema.Set(value_type=schema.TextLine(), required=False)
    frozenset_of_text = schema.FrozenSet(value_type=schema.TextLine(), required=False)
    dict_value = schema.Dict(key_type=schema.TextLine(), value_type=schema.TextLine(), required=False)
    datetime = schema.Datetime(required=False)
    date = schema.Date(required=False)
    time = schema.Time(required=False)

    patch_list = fields.PatchField(
        schema.List(value_type=schema.Dict(key_type=schema.Text(), value_type=schema.Text()), required=False)
    )
    patch_list_int = fields.PatchField(schema.List(value_type=schema.Int(), required=False))
    patch_list_float = fields.PatchField(schema.List(value_type=schema.Float(), required=False))
    patch_dict = fields.PatchField(
        schema.Dict(key_type=schema.Text(), value_type=schema.Text()), required=False
    )

    patch_int = fields.PatchField(schema.Int(default=22), required=False)

    patch_int_no_default = fields.PatchField(schema.Int(), required=False)

    bucket_list = fields.BucketListField(
        bucket_len=10,
        required=False,
        value_type=schema.Dict(key_type=schema.Text(), value_type=schema.Text()),
    )

    datetime_bucket_list = fields.BucketListField(bucket_len=10, required=False, value_type=schema.Datetime())

    union_field = schema.UnionField(schema.Datetime(), schema.Int(), required=False)
    union_field_obj = schema.UnionField(
        schema.Object(IObjectA), schema.Object(schema=IObjectB), required=False
    )

    nested_patch = fields.PatchField(
        schema.Dict(
            required=False,
            key_type=schema.Text(),
            value_type=fields.PatchField(schema.List(value_type=schema.Object(schema=INestFieldSchema))),
        )
    )

    dict_of_obj = schema.Dict(
        required=False, key_type=schema.Text(), value_type=schema.Object(schema=INestFieldSchema)
    )

    patch_dict_of_obj = fields.PatchField(
        schema.Dict(required=False, key_type=schema.Text(), value_type=schema.Object(schema=INestFieldSchema))
    )

    patch_tuple = fields.PatchField(
        schema.Tuple(required=False, value_type=schema.Text(schema=INestFieldSchema))
    )

    bucket_dict = fields.BucketDictField(
        bucket_len=10, required=False, key_type=schema.Text(), value_type=schema.Text()
    )


async def test_deserialize_text(dummy_guillotina):
    assert schema_compatible("foobar", ITestSchema["text"]) == "foobar"


async def test_deserialize_int(dummy_guillotina):
    assert schema_compatible(5, ITestSchema["integer"]) == 5


async def test_deserialize_float(dummy_guillotina):
    assert int(schema_compatible(5.5534, ITestSchema["floating"])) == 5


async def test_deserialize_float_convert_int(dummy_guillotina):
    assert int(schema_compatible(5, ITestSchema["floating"])) == 5


async def test_sub_field_float_convert_int(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    errors = []
    await deserializer.set_schema(ITestSchema, content, {"patch_list_float": [1, 2]}, errors)
    assert errors == []


async def test_deserialize_list(dummy_guillotina):
    assert schema_compatible(["foo", "bar"], ITestSchema["list_of_text"]) == ["foo", "bar"]


async def test_deserialize_tuple(dummy_guillotina):
    assert schema_compatible(["foo", "bar"], ITestSchema["tuple_of_text"]) == ("foo", "bar")


async def test_deserialize_set(dummy_guillotina):
    assert len(schema_compatible(["foo", "bar"], ITestSchema["set_of_text"])) == 2


async def test_deserialize_frozenset(dummy_guillotina):
    assert len(schema_compatible(["foo", "bar"], ITestSchema["frozenset_of_text"])) == 2


async def test_deserialize_dict(dummy_guillotina):
    assert schema_compatible({"foo": "bar"}, ITestSchema["dict_value"]) == {"foo": "bar"}


async def test_deserialize_union(dummy_guillotina):
    assert schema_compatible(123456789, ITestSchema["union_field"]) == 123456789
    now = datetime.utcnow()
    converted = schema_compatible(now.isoformat(), ITestSchema["union_field"])
    assert converted.minute == now.minute

    with pytest.raises(ValueDeserializationError):
        schema_compatible("invalid-date", ITestSchema["union_field"])


async def test_deserialize_union_of_obj(dummy_guillotina):
    assert schema_compatible({"foo": "oooo"}, ITestSchema["union_field_obj"]) == {"foo": "oooo"}
    assert schema_compatible({"bar": "aaar"}, ITestSchema["union_field_obj"]) == {"bar": "aaar"}

    with pytest.raises(ValueDeserializationError):
        schema_compatible({"inexisting"}, ITestSchema["union_field_obj"])


async def test_deserialize_datetime(dummy_guillotina):
    now = datetime.utcnow()
    converted = schema_compatible(now.isoformat(), ITestSchema["datetime"])
    assert converted.minute == now.minute


async def test_check_permission_deserialize_content(dummy_request):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    assert deserializer.check_permission("guillotina.ViewContent")
    assert deserializer.check_permission("guillotina.ViewContent")  # with cache


async def test_patch_list_field_normal_patch(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    await deserializer.set_schema(ITestSchema, content, {"patch_list": [{"foo": "bar"}]}, [])
    assert len(content.patch_list) == 1


async def test_patch_list_field(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    await deserializer.set_schema(
        ITestSchema, content, {"patch_list": {"op": "append", "value": {"foo": "bar"}}}, []
    )

    assert len(content.patch_list) == 1
    assert content.patch_list[0] == {"foo": "bar"}

    await deserializer.set_schema(
        ITestSchema, content, {"patch_list": {"op": "append", "value": {"foo2": "bar2"}}}, []
    )

    assert len(content.patch_list) == 2
    assert content.patch_list[1] == {"foo2": "bar2"}

    await deserializer.set_schema(
        ITestSchema,
        content,
        {"patch_list": {"op": "extend", "value": [{"foo3": "bar3"}, {"foo4": "bar4"}]}},
        [],
    )

    assert len(content.patch_list) == 4
    assert content.patch_list[-1] == {"foo4": "bar4"}

    await deserializer.set_schema(
        ITestSchema,
        content,
        {"patch_list": {"op": "update", "value": {"index": 3, "value": {"fooupdated": "barupdated"}}}},
        [],
    )

    assert len(content.patch_list) == 4
    assert content.patch_list[-1] == {"fooupdated": "barupdated"}

    await deserializer.set_schema(ITestSchema, content, {"patch_list": {"op": "del", "value": 3}}, [])
    assert len(content.patch_list) == 3

    await deserializer.set_schema(ITestSchema, content, {"patch_list": {"op": "clear"}}, [])
    assert len(content.patch_list) == 0


async def test_patch_tuple_field(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    await deserializer.set_schema(ITestSchema, content, {"patch_tuple": {"op": "append", "value": "foo"}}, [])

    assert len(content.patch_tuple) == 1
    assert content.patch_tuple[0] == "foo"

    await deserializer.set_schema(
        ITestSchema, content, {"patch_tuple": {"op": "appendunique", "value": "foo"}}, []
    )

    assert len(content.patch_tuple) == 1

    await deserializer.set_schema(
        ITestSchema, content, {"patch_tuple": {"op": "extend", "value": ["bar"]}}, []
    )

    assert len(content.patch_tuple) == 2
    assert content.patch_tuple[1] == "bar"

    await deserializer.set_schema(
        ITestSchema, content, {"patch_tuple": {"op": "extendunique", "value": ["bar"]}}, []
    )

    assert len(content.patch_tuple) == 2

    await deserializer.set_schema(
        ITestSchema,
        content,
        {"patch_tuple": {"op": "update", "value": {"index": 1, "value": "barupdated"}}},
        [],
    )

    assert len(content.patch_tuple) == 2
    assert content.patch_tuple[1] == "barupdated"

    await deserializer.set_schema(ITestSchema, content, {"patch_tuple": {"op": "del", "value": 1}}, [])
    assert len(content.patch_tuple) == 1

    await deserializer.set_schema(ITestSchema, content, {"patch_tuple": {"op": "clear"}}, [])
    assert len(content.patch_tuple) == 0


async def test_patch_list_field_invalid_type(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    errors = []
    await deserializer.set_schema(ITestSchema, content, {"patch_list": {"op": "append", "value": 1}}, errors)

    assert len(getattr(content, "patch_list", [])) == 0
    assert len(errors) == 1
    assert isinstance(errors[0]["error"], ValueDeserializationError)


async def test_patch_dict_field_normal_patch(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    await deserializer.set_schema(ITestSchema, content, {"patch_dict": {"foo": "bar"}}, [])
    assert len(content.patch_dict) == 1


async def test_patch_dict_field(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    await deserializer.set_schema(
        ITestSchema, content, {"patch_dict": {"op": "assign", "value": {"key": "foo", "value": "bar"}}}, []
    )

    assert len(content.patch_dict) == 1
    assert content.patch_dict["foo"] == "bar"

    await deserializer.set_schema(
        ITestSchema, content, {"patch_dict": {"op": "assign", "value": {"key": "foo2", "value": "bar2"}}}, []
    )

    assert len(content.patch_dict) == 2
    assert content.patch_dict["foo2"] == "bar2"

    await deserializer.set_schema(ITestSchema, content, {"patch_dict": {"op": "del", "value": "foo2"}}, [])

    assert len(content.patch_dict) == 1
    assert "foo2" not in content.patch_dict

    await deserializer.set_schema(ITestSchema, content, {"patch_dict": {"op": "clear"}}, [])

    assert len(content.patch_dict) == 0


async def test_patch_dict_field_invalid_type(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    errors = []
    await deserializer.set_schema(
        ITestSchema, content, {"patch_dict": {"op": "assign", "value": {"key": 1, "value": "bar2"}}}, errors
    )

    assert len(getattr(content, "patch_dict", {})) == 0
    assert len(errors) == 1
    assert isinstance(errors[0]["error"], WrongType)


async def test_patch_int_field_normal_path(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    await deserializer.set_schema(ITestSchema, content, {"patch_int": 2}, [])
    assert content.patch_int == 2


async def test_patch_int_field(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    # Increment it and check it adds to default value
    await deserializer.set_schema(ITestSchema, content, {"patch_int": {"op": "inc", "value": 3}}, [])
    assert content.patch_int == 25
    # Check that increments 1 if no value is passed
    await deserializer.set_schema(ITestSchema, content, {"patch_int": {"op": "inc"}}, [])
    assert content.patch_int == 26

    # Decrements 1 by default
    await deserializer.set_schema(ITestSchema, content, {"patch_int": {"op": "dec"}}, [])
    assert content.patch_int == 25
    # Decrement it
    await deserializer.set_schema(ITestSchema, content, {"patch_int": {"op": "dec", "value": 5}}, [])
    assert content.patch_int == 20
    # Check that we can have negative integers
    await deserializer.set_schema(ITestSchema, content, {"patch_int": {"op": "dec", "value": 25}}, [])
    assert content.patch_int == -5

    # Reset it to default value if not specified
    await deserializer.set_schema(ITestSchema, content, {"patch_int": {"op": "reset"}}, [])
    assert content.patch_int == 22

    # Reset it to specified value
    await deserializer.set_schema(ITestSchema, content, {"patch_int": {"op": "reset", "value": 400}}, [])
    assert content.patch_int == 400

    # Check that assumes value as 0 if there is no existing value and
    # no default value either
    assert getattr(content, "patch_int_no_default", None) is None
    await deserializer.set_schema(ITestSchema, content, {"patch_int_no_default": {"op": "inc"}}, [])
    assert content.patch_int_no_default == 1

    content.patch_int_no_default = None
    await deserializer.set_schema(ITestSchema, content, {"patch_int_no_default": {"op": "dec"}}, [])
    assert content.patch_int_no_default == -1
    content.patch_int_no_default = None
    await deserializer.set_schema(ITestSchema, content, {"patch_int_no_default": {"op": "reset"}}, [])
    assert content.patch_int_no_default == 0


async def test_patch_int_field_invalid_type(dummy_request):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    for op in ("inc", "dec", "reset"):
        errors = []
        await deserializer.set_schema(ITestSchema, content, {"patch_int": {"op": op, "value": 3.3}}, errors)
        assert getattr(content, "patch_int", 0) == 0
        assert len(errors) == 1
        assert isinstance(errors[0]["error"], WrongType)


async def test_bucket_list_field(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    await deserializer.set_schema(
        ITestSchema, content, {"bucket_list": {"op": "append", "value": {"key": "foo", "value": "bar"}}}, []
    )
    assert content.bucket_list.annotations_metadata[0]["len"] == 1
    assert await content.bucket_list.get(content, 0, 0) == {"key": "foo", "value": "bar"}
    assert await content.bucket_list.get(content, 0, 1) is None
    assert await content.bucket_list.get(content, 1, 0) is None

    for _ in range(100):
        await deserializer.set_schema(
            ITestSchema,
            content,
            {"bucket_list": {"op": "append", "value": {"key": "foo", "value": "bar"}}},
            [],
        )

    assert len(content.bucket_list.annotations_metadata) == 11
    assert content.bucket_list.annotations_metadata[0]["len"] == 10
    assert content.bucket_list.annotations_metadata[5]["len"] == 10
    assert content.bucket_list.annotations_metadata[10]["len"] == 1

    await content.bucket_list.remove(content, 10, 0)
    assert content.bucket_list.annotations_metadata[10]["len"] == 0
    await content.bucket_list.remove(content, 9, 0)
    assert content.bucket_list.annotations_metadata[9]["len"] == 9

    assert len(content.bucket_list) == 99

    await deserializer.set_schema(
        ITestSchema,
        content,
        {
            "bucket_list": {
                "op": "extend",
                "value": [{"key": "foo", "value": "bar"}, {"key": "foo", "value": "bar"}],
            }
        },
        [],
    )

    assert len(content.bucket_list) == 101

    assert json_compatible(content.bucket_list) == {"len": 101, "buckets": 11}

    assert len([b async for b in content.bucket_list.iter_buckets(content)]) == 11
    assert len([i async for i in content.bucket_list.iter_items(content)]) == 101

    assert "bucketlist-bucket_list0" in content.__gannotations__


async def test_bucket_list_field_clear(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)

    for _ in range(100):
        await deserializer.set_schema(
            ITestSchema,
            content,
            {"bucket_list": {"op": "append", "value": {"key": "foo", "value": "bar"}}},
            [],
        )
    assert len(content.bucket_list) == 100
    assert len(content.bucket_list.annotations_metadata) == 10

    await deserializer.set_schema(ITestSchema, content, {"bucket_list": {"op": "clear"}}, [])
    assert len(content.bucket_list) == 0
    assert len(content.bucket_list.annotations_metadata) == 0


async def test_patch_multi(dummy_request):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)

    await deserializer.set_schema(
        ITestSchema,
        content,
        {
            "patch_dict": {
                "op": "multi",
                "value": [
                    {"op": "assign", "value": {"key": "foo", "value": "bar"}},
                    {"op": "assign", "value": {"key": "foo2", "value": "bar2"}},
                ],
            }
        },
        [],
    )
    assert len(content.patch_dict) == 2
    assert content.patch_dict["foo"] == "bar"
    assert content.patch_dict["foo2"] == "bar2"

    await deserializer.set_schema(
        ITestSchema,
        content,
        {
            "patch_dict": {
                "op": "multi",
                "value": [
                    {"op": "del", "value": "foo2"},
                    {"op": "assign", "value": {"key": "foo3", "value": "bar3"}},
                ],
            }
        },
        [],
    )
    assert len(content.patch_dict) == 2
    assert "foo2" not in content.patch_dict
    assert content.patch_dict["foo"] == "bar"
    assert content.patch_dict["foo3"] == "bar3"


async def test_default_value_deserialize(dummy_request):
    content = create_content()
    assert {"text": "foobar"} == deserialize_value.default_value_converter(
        ITestSchema, {"text": "foobar"}, content
    )


async def test_nested_patch_deserialize(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    errors = []
    await deserializer.set_schema(
        ITestSchema,
        content,
        {
            "nested_patch": {
                "op": "assign",
                "value": {
                    "key": "foobar",
                    "value": {
                        "op": "append",
                        "value": {
                            "foo": "bar",
                            "bar": 1,
                            "foobar_list": None,
                            "nested_int": {"op": "reset", "value": 5},
                        },
                    },
                },
            }
        },
        errors,
    )
    assert len(errors) == 0
    assert len(content.nested_patch) == 1
    assert content.nested_patch["foobar"][0]["foo"] == "bar"
    assert content.nested_patch["foobar"][0]["bar"] == 1
    assert content.nested_patch["foobar"][0]["nested_int"] == 5

    await deserializer.set_schema(
        ITestSchema,
        content,
        {
            "nested_patch": {
                "op": "assign",
                "value": {"key": "foobar", "value": {"op": "append", "value": {"foo": "bar2", "bar": 2}}},
            }
        },
        errors,
    )
    assert len(errors) == 0
    assert content.nested_patch["foobar"][1]["foo"] == "bar2"
    assert content.nested_patch["foobar"][1]["bar"] == 2

    await deserializer.set_schema(
        ITestSchema,
        content,
        {
            "nested_patch": {
                "op": "assign",
                "value": {
                    "key": "foobar",
                    "value": {
                        "op": "update",
                        "value": {
                            "index": 1,
                            "value": {"foo": "bar3", "bar": 3, "nested_int": {"op": "inc"}},
                        },
                    },
                },
            }
        },
        errors,
    )
    assert len(errors) == 0
    assert content.nested_patch["foobar"][1]["foo"] == "bar3"
    assert content.nested_patch["foobar"][1]["bar"] == 3
    assert content.nested_patch["foobar"][1]["nested_int"] == 1


async def test_dates_bucket_list_field(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    await deserializer.set_schema(
        ITestSchema,
        content,
        {"datetime_bucket_list": {"op": "append", "value": "2018-06-05T12:35:30.865745+00:00"}},
        [],
    )
    assert content.datetime_bucket_list.annotations_metadata[0]["len"] == 1
    await deserializer.set_schema(
        ITestSchema,
        content,
        {
            "datetime_bucket_list": {
                "op": "extend",
                "value": ["2019-06-05T12:35:30.865745+00:00", "2020-06-05T12:35:30.865745+00:00"],
            }
        },
        [],
    )
    assert content.datetime_bucket_list.annotations_metadata[0]["len"] == 3


async def test_patchfield_notdefined_field(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    errors = []
    await deserializer.set_schema(
        ITestSchema,
        content,
        {
            "dict_of_obj": {
                "key1": {
                    "foo": "bar",
                    "bar": 1,
                    # Value not found in schema
                    "not_defined_field": "arbitrary-value",
                }
            },
            "patch_dict_of_obj": {
                "key1": {
                    "foo": "bar",
                    "bar": 1,
                    # Value not found in schema
                    "not_defined_field": "arbitrary-value",
                }
            },
        },
        errors,
    )

    assert len(errors) == 0

    # 'not_defined_field' is not part of INestFieldSchema so should not serialized and stored
    assert "not_defined_field" not in content.dict_of_obj["key1"]
    assert "not_defined_field" not in content.patch_dict_of_obj["key1"]

    await deserializer.set_schema(
        ITestSchema,
        content,
        {
            "patch_dict_of_obj": {
                "op": "assign",
                "value": {
                    "key": "key1",
                    "value": {
                        "op": "append",
                        "value": {
                            "foo": "bar",
                            "bar": 1,
                            # Value not found in schema
                            "not_defined_field": "arbitrary-value",
                        },
                    },
                },
            }
        },
        errors,
    )

    assert len(errors) == 0
    assert "not_defined_field" not in content.dict_of_obj["key1"]
    assert "not_defined_field" not in content.patch_dict_of_obj["key1"]


async def test_delete_by_value_field(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    errors = []
    await deserializer.set_schema(ITestSchema, content, {"patch_list_int": [1, 2]}, errors)
    assert errors == []
    assert getattr(content, "patch_list_int", []) == [1, 2]
    await deserializer.set_schema(
        ITestSchema, content, {"patch_list_int": {"op": "remove", "value": 2}}, errors
    )
    assert errors == []
    assert getattr(content, "patch_list_int", []) == [1]

    await deserializer.set_schema(
        ITestSchema, content, {"patch_list_int": {"op": "remove", "value": 99}}, errors
    )
    assert len(errors) == 1
    assert errors[0]["field"] == "patch_list_int"


async def test_bucket_dict_field(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    await deserializer.set_schema(
        ITestSchema, content, {"bucket_dict": {"op": "assign", "value": {"key": "foo", "value": "bar"}}}, []
    )
    assert content.bucket_dict.buckets[0]["len"] == 1
    assert await content.bucket_dict.get(content, "foo") == "bar"
    assert await content.bucket_dict.get(content, "bar") is None

    inserted = {"foo": "bar"}
    for idx in range(100):
        key = uuid.uuid4().hex
        inserted[key] = str(idx)
        await deserializer.set_schema(
            ITestSchema,
            content,
            {"bucket_dict": {"op": "assign", "value": {"key": key, "value": str(idx)}}},
            [],
        )

    # number of buckets and sizes of each is random depending on keys
    assert len(content.bucket_dict) == 101
    removed = list(inserted.keys())[-1]
    del inserted[removed]
    await content.bucket_dict.remove(content, removed)
    assert len(content.bucket_dict) == 100

    one = list(inserted.keys())[-1]
    two = list(inserted.keys())[-2]
    await deserializer.set_schema(
        ITestSchema,
        content,
        {"bucket_dict": {"op": "update", "value": [{"key": one, "value": "1"}, {"key": two, "value": "2"}]}},
        [],
    )

    inserted[one] = "1"
    inserted[two] = "2"
    assert len(content.bucket_dict) == 100
    assert await content.bucket_dict.get(content, one) == "1"
    assert await content.bucket_dict.get(content, two) == "2"

    assert json_compatible(content.bucket_dict)["len"] == 100

    assert len(content.bucket_dict.buckets) == len(
        [name for name in content.__gannotations__.keys() if name.startswith("bucketdict-")]
    )

    # test everything completely sorted
    all_keys = []
    all_values = []
    for bucket in content.bucket_dict.buckets:
        annotation = await content.bucket_dict.get_annotation(content, anno_id=bucket["id"])
        assert annotation["keys"] == sorted(annotation["keys"])
        all_keys.extend(annotation["keys"])
        all_values.extend(annotation["values"])
    assert all_keys == sorted(all_keys)
    assert all_keys == sorted(inserted.keys())

    # check all values as well
    for idx, key in enumerate(all_keys):
        assert inserted[key] == all_values[idx]


async def test_unhandled_exceptions_in_bucket_dict_field_do_not_write_to_object(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    errors = []
    await deserializer.set_schema(
        ITestSchema, content, {"bucket_dict": {"op": "assign", "value": None}}, errors
    )
    assert not hasattr(content, "bucket_dict")
    assert len(errors) == 1


async def test_bucket_dict_field_splitting(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    for idx in range(10):
        key = str(idx)
        await deserializer.set_schema(
            ITestSchema,
            content,
            {"bucket_dict": {"op": "assign", "value": {"key": key, "value": str(idx)}}},
            [],
        )
    assert len(mock_txn.added) == 1  # should all be in one bucket
    mock_txn.added.clear()
    # now test inserting one that will split the buckets and insert into new bucket.
    await deserializer.set_schema(
        ITestSchema,
        content,
        {"bucket_dict": {"op": "assign", "value": {"key": "ZZZZZ", "value": "foobar"}}},
        [],
    )
    assert len(mock_txn.added) == 2  # should write to existing bucket and new one


async def test_bucket_dict_field_clear(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)

    inserted = {"foo": "bar"}
    for idx in range(100):
        key = uuid.uuid4().hex
        inserted[key] = str(idx)
        await deserializer.set_schema(
            ITestSchema,
            content,
            {"bucket_dict": {"op": "assign", "value": {"key": key, "value": str(idx)}}},
            [],
        )
    assert len(content.bucket_dict) == 100

    await deserializer.set_schema(ITestSchema, content, {"bucket_dict": {"op": "clear"}}, [])
    assert len(content.bucket_dict) == 0
    assert len(content.bucket_dict.buckets) == 1


class ITestValidation(Interface):

    foo = schema.Text(required=False)
    bar = schema.Text(required=False)

    constrained = schema.Text(required=False, constraint=lambda val: val != "foobar")

    validated_text = schema.Text(required=False)

    @invariant
    def text_should_not_be_foobar(ob):
        if getattr(ob, "foo", None) == "foo" and getattr(ob, "bar", None) == "bar":
            raise Invalid(ob)

    @validated_text.validator
    def validate_not_foo(field, value):
        if getattr(field.context, "foo", None) == "foo" and value == "foo":
            raise Invalid("Must not be foo")


async def test_invariant_error(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    errors = []
    await deserializer.set_schema(
        ITestValidation, content, {"foo": "foo", "bar": "bar"}, errors, validate_all=True
    )
    assert len(errors) == 1

    errors = []
    await deserializer.set_schema(
        ITestValidation, content, {"foo": "foo", "bar": "blah"}, errors, validate_all=True
    )
    assert len(errors) == 0


async def test_constraint_error(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    errors = []
    await deserializer.set_schema(ITestValidation, content, {"constrained": "foobar"}, errors)
    assert len(errors) == 1

    errors = []
    await deserializer.set_schema(ITestValidation, content, {"constrained": "not foobar"}, errors)
    assert len(errors) == 0


async def test_validator_error(dummy_request, mock_txn):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    errors = []
    await deserializer.set_schema(ITestValidation, content, {"validated_text": "foo", "foo": "foo"}, errors)
    assert len(errors) == 1

    errors = []
    content = create_content()
    await deserializer.set_schema(ITestValidation, content, {"validated_text": "foo"}, errors)
    assert len(errors) == 0


async def test_patch_list_mutli_patch_validation(dummy_guillotina):
    field = fields.PatchField(schema.List(), max_ops=2)
    multi = patch.MultiPatch(field)
    content = create_content()
    with pytest.raises(ValueDeserializationError):
        multi(content, [[]])
    with pytest.raises(ValueDeserializationError):
        multi(content, [""])


async def test_patch_list_mutli_patch_max_ops(dummy_guillotina):
    field = fields.PatchField(schema.List(), max_ops=1)
    multi = patch.MultiPatch(field)
    content = create_content()
    multi(content, [{"op": "append", "value": "foobar"}])
    with pytest.raises(ValueDeserializationError):
        multi(content, [{"op": "append", "value": "foobar"}, {"op": "append", "value": "foobar"}])


async def test_patch_dict_mutli_patch_max_ops(dummy_guillotina):
    field = fields.PatchField(schema.Dict(), max_ops=1)
    multi = patch.MultiPatch(field)
    content = create_content()
    multi(content, [{"op": "update", "value": [{"key": "foo", "value": "bar"}]}])
    with pytest.raises(ValueDeserializationError):
        multi(
            content,
            [
                {"op": "update", "value": [{"key": "foo", "value": "bar"}]},
                {"op": "update", "value": [{"key": "foo", "value": "bar"}]},
            ],
        )


async def test_patch_list_extend_max_ops(dummy_guillotina):
    field = fields.PatchField(schema.List(), max_ops=1)
    op = patch.PatchListExtend(field.field)
    content = create_content()
    op(content, ["foobar"])
    with pytest.raises(ValueDeserializationError):
        op(content, ["foo", "bar"])


async def test_patch_dict_update_max_ops(dummy_guillotina):
    field = fields.PatchField(schema.Dict(key_type=schema.Text(), value_type=schema.Text()), max_ops=1)
    field.__name__ = field.field.__name__ = "foobar"
    op = patch.PatchDictUpdate(field.field)
    content = create_content()
    op(content, [{"key": "foo", "value": "bar"}])
    with pytest.raises(ValueDeserializationError):
        op(content, [{"key": "foo", "value": "bar"}, {"key": "foo", "value": "bar"}])


async def test_bucket_list_invalid_op(dummy_guillotina, mock_txn):
    field = fields.BucketListField(bucket_len=10, required=False, value_type=schema.Text())
    content = create_content()
    with pytest.raises(ValueDeserializationError):
        await field.set(content, {"op": "foobar", "value": ["foobar"]})


async def test_patch_dict_validation(dummy_guillotina):
    field = fields.PatchField(schema.Dict(key_type=schema.Text(), value_type=schema.Text()), max_ops=1)
    field.__name__ = field.field.__name__ = "foobar"
    op = patch.PatchDictUpdate(field.field)
    content = create_content()
    with pytest.raises(ValueDeserializationError):
        op(content, [{"foo": "bar"}])


async def test_bucket_list_max_ops(dummy_guillotina, mock_txn):
    field = fields.BucketListField(bucket_len=10, required=False, max_ops=1, value_type=schema.Text())
    field.__name__ = "foobar"
    content = create_content()
    await field.set(content, {"op": "extend", "value": ["foobar"]})
    with pytest.raises(ValueDeserializationError):
        await field.set(content, {"op": "extend", "value": ["foo", "bar"]})


async def test_bucket_dict_max_ops(dummy_guillotina, mock_txn):
    field = fields.BucketDictField(bucket_len=10, required=False, max_ops=1, value_type=schema.Text())
    field.__name__ = "foobar"
    content = create_content()
    await field.set(content, {"op": "update", "value": [{"key": "foo", "value": "bar"}]})
    with pytest.raises(ValueDeserializationError):
        await field.set(
            content,
            {"op": "update", "value": [{"key": "foo", "value": "bar"}, {"key": "foo", "value": "bar"}]},
        )


class ITestSchemaWithInvariant(Interface):
    foobar = schema.Text()

    @invariant
    async def validate_obj(obj):
        if obj.foobar == "foobar":
            raise Invalid("Value is foobar")
        else:
            raise schema.ValidationError(value=obj.foobar, field_name="foobar", errors=["Wrong value"])


async def test_async_invariant():
    content = create_content()
    content.foobar = "foobar"
    assert len(await validate_invariants(ITestSchemaWithInvariant, content)) == 1

    content = create_content()
    content.foobar = "not foobar"
    assert len(await validate_invariants(ITestSchemaWithInvariant, content)) == 1


async def test_async_invariant_deserializer(dummy_guillotina, mock_txn, dummy_request):
    login()
    content = create_content()
    deserializer = get_multi_adapter((content, dummy_request), IResourceDeserializeFromJson)
    errors = []
    await deserializer.set_schema(ITestSchemaWithInvariant, content, {"foobar": "foobar"}, errors)
    assert len(errors) == 1
    assert errors[0]["message"] == "Value is foobar"

    errors = []
    await deserializer.set_schema(ITestSchemaWithInvariant, content, {"foobar": "not foobar"}, errors)
    assert len(errors) == 1
    assert errors[0]["error"][0] == "Wrong value"


async def test_patch_dict_json_field(dummy_request):
    field = schema.JSONField(required=False, schema={"type": "object"})
    field.__name__ = "foobar"
    field.max_ops = 100

    get_adapter(field, IPatchFieldOperation, name="assign")(
        create_content(foobar={"foo": "bar", "bar": "foo"}), {"key": "foo", "value": "bar"}
    ) == {"foo": "bar", "bar": "foo"}

    get_adapter(field, IPatchFieldOperation, name="update")(
        create_content(foobar={"foo": "bar", "bar": "foo"}),
        [{"key": "foo", "value": "bar"}, {"key": "bar", "value": "FOO"}],
    ) == {"foo": "bar", "bar": "FOO"}

    get_adapter(field, IPatchFieldOperation, name="clear")(
        create_content(foobar={"foo": "bar", "bar": "foo"}), None
    ) == {}

    get_adapter(field, IPatchFieldOperation, name="del")(
        create_content(foobar={"foo": "bar", "bar": "foo"}), "foo"
    ) == {"bar": "foo"}


async def test_patch_list_json_field(dummy_request):
    field = schema.JSONField(required=False, schema={"type": "array", "items": {"type": "string"}})
    field.__name__ = "foobar"
    field.max_ops = 100

    get_adapter(field, IPatchFieldOperation, name="append")(create_content(foobar=["foo", "bar"]), "foo") == [
        "foo",
        "bar",
        "foo",
    ]
    get_adapter(field, IPatchFieldOperation, name="extend")(
        create_content(foobar=["foo", "bar"]), ["foo2", "bar2"]
    ) == ["foo", "bar", "foo2", "bar2"]
    get_adapter(field, IPatchFieldOperation, name="appendunique")(
        create_content(foobar=["foo", "bar"]), "foo"
    ) == ["foo", "bar", "foo"]
    get_adapter(field, IPatchFieldOperation, name="clear")(create_content(foobar=["foo", "bar"]), None) == []
    get_adapter(field, IPatchFieldOperation, name="assign")(
        create_content(foobar=["foo", "bar"]), {"key": 0, "value": "FOO"}
    ) == ["FOO", "bar"]
    get_adapter(field, IPatchFieldOperation, name="del")(create_content(foobar=["foo", "bar"]), 0) == ["bar"]
