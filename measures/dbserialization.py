from google.protobuf import json_format
from measures.protobuf.test_pb2 import DublinCore

import pickle
import string
import time


ITERATIONS = 10000

TEST_PAYLOAD = {
    "tags": 10 * ["" for i in zip(string.ascii_letters, string.ascii_letters)],
    "creation_date": "2020-01-02T19:07:48.748922Z",
    "effective_date": "2020-01-02T19:07:48.748922Z",
    "expiration_date": "2020-01-02T19:07:48.748922Z",
    "creators": ["".join(i) for i in zip(string.ascii_letters, string.ascii_letters)],
}


def test_pickle(obj, iterations):
    for idx in range(iterations):
        obj.tags.append("foobar" + str(idx))
        pickle.dumps(obj)


def test_protobuf(obj, iterations):
    for idx in range(iterations):
        obj.tags.append("foobar" + str(idx))
        obj.SerializeToString()


async def run():
    for name, test in (("protobuf", test_protobuf), ("pickle", test_pickle)):
        core = DublinCore()
        json_format.ParseDict(TEST_PAYLOAD, core)

        start = time.time()
        test(core, ITERATIONS)
        print(f"Done {name} in {time.time() - start}")
