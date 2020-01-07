from google.protobuf import json_format
from guillotina.behaviors.dublincore import IDublinCore
from guillotina.json.deserialize_value import schema_compatible
from measures.protobuf.test_pb2 import DublinCore

import capnp
import jsonschema
import string
import time


capnp.remove_import_hook()
test_capnp = capnp.load("measures/capnp/test.capnp")

ITERATIONS = 1000

TEST_PAYLOAD = {
    "tags": 10 * ["".join(i) for i in zip(string.ascii_letters, string.ascii_letters)],
    "creation_date": "2020-01-02T19:07:48.748922Z",
    "effective_date": "2020-01-02T19:07:48.748922Z",
    "expiration_date": "2020-01-02T19:07:48.748922Z",
    "creators": ["".join(i) for i in zip(string.ascii_letters, string.ascii_letters)],
}


JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "tags": {"type": "array", "items": {"type": "string"}},
        "creation_date": {"type": "string", "format": "date-time"},
        "effective_date": {"type": "string", "format": "date-time"},
        "expiration_date": {"type": "string", "format": "date-time"},
        "creators": {"type": "array", "items": {"type": "string"}},
    },
}
jschema_validator = jsonschema.validators.validator_for(JSON_SCHEMA)(JSON_SCHEMA)


CAP_TEST_PAYLOAD = TEST_PAYLOAD.copy()
for old, new in (
    ("creation_date", "creationDate"),
    ("effective_date", "effectiveDate"),
    ("expiration_date", "expirationDate"),
):
    # CAP_TEST_PAYLOAD[new] = CAP_TEST_PAYLOAD[old]
    del CAP_TEST_PAYLOAD[old]


def test_python_schema(iterations):
    for _ in range(iterations):
        schema_compatible(TEST_PAYLOAD, IDublinCore)


def test_json_schema(iterations):
    for _ in range(iterations):
        jschema_validator.validate(TEST_PAYLOAD)


def test_protobuf_schema(iterations):
    for _ in range(iterations):
        json_format.ParseDict(CAP_TEST_PAYLOAD, DublinCore())


def test_capnp_schema(iterations):
    for _ in range(iterations):
        test_capnp.DublinCore.new_message(**CAP_TEST_PAYLOAD)


async def run():
    for name, test in (
        ("capnp", test_capnp_schema),
        ("protobuf", test_protobuf_schema),
        ("python", test_python_schema),
        ("jsonschema", test_json_schema),
    ):
        start = time.time()
        test(ITERATIONS)
        print(f"Done {name} in {time.time() - start}")
