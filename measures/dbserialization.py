from google.protobuf import json_format
from measures.protobuf.test_pb2 import DublinCore

import capnp
import pickle
import string
import time


capnp.remove_import_hook()
test_capnp = capnp.load("measures/capnp/test.capnp")

ITERATIONS = 10000

TEST_PAYLOAD = {
    "tags": 10 * ["".join(i) for i in zip(string.ascii_letters, string.ascii_letters)],
    # "creation_date": "2020-01-02T19:07:48.748922Z",
    # "effective_date": "2020-01-02T19:07:48.748922Z",
    # "expiration_date": "2020-01-02T19:07:48.748922Z",
    "creators": ["".join(i) for i in zip(string.ascii_letters, string.ascii_letters)],
}


def test_pickle(obj, iterations):
    for _ in range(iterations):
        pickle.dumps(obj)


def test_protobuf(obj, iterations):
    for _ in range(iterations):
        obj.SerializeToString()


def test_capnp_timed(obj, iterations):
    for _ in range(iterations):
        obj.to_bytes()


async def run():
    pb_ob = DublinCore()
    json_format.ParseDict(TEST_PAYLOAD, pb_ob)

    cap_ob = test_capnp.DublinCore.new_message(**TEST_PAYLOAD)

    for name, test, ob in (
        ("capnp", test_capnp_timed, cap_ob),
        ("protobuf", test_protobuf, pb_ob),
        ("pickle", test_pickle, pb_ob),
    ):
        start = time.time()
        test(ob, ITERATIONS)
        print(f"Done {name} in {time.time() - start}")
