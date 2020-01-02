from google.protobuf import json_format
from guillotina.behaviors.dublincore import IDublinCore
from guillotina.json.deserialize_value import schema_compatible
from measures.protobuf.test_pb2 import DublinCore

import jsonschema
import string
import time


ITERATIONS = 1000

TEST_PAYLOAD = {
    "tags": 10 * ["" for i in zip(string.ascii_letters, string.ascii_letters)],
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


def test_python_schema(iterations):
    for _ in range(iterations):
        schema_compatible(TEST_PAYLOAD, IDublinCore)


def test_json_schema(iterations):
    for _ in range(iterations):
        jschema_validator.validate(TEST_PAYLOAD)


def test_protobuf_schema(iterations):
    for _ in range(iterations):
        json_format.ParseDict(TEST_PAYLOAD, DublinCore())


async def run():
    for name, test in (
        ("protobuf", test_protobuf_schema),
        ("python", test_python_schema),
        ("jsonschema", test_json_schema),
    ):
        start = time.time()
        test(ITERATIONS)
        print(f"Done {name} in {time.time() - start}")
