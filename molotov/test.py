"""

This Molotov script has 2 scenario

"""
from molotov import setup, global_setup, scenario

_HEADERS = {}

_API = "http://localhost:8080/df/container2"


@global_setup()
def init_test(args):
    _HEADERS["Authorization"] = "Basic cm9vdDpyb290"


@setup()
async def init_worker(worker_id, args):
    return {"headers": _HEADERS}


@scenario(weight=0)
async def scenario_one(session):
    async with session.get(_API) as resp:
        assert resp.status == 200


@scenario(weight=100)
async def scenario_two(session):
    data = {"@type": "Item", "title": "hola"}

    async with session.post(_API, json=data) as resp:
        assert resp.status == 201
