from guillotina.contrib.proto.interfaces import IProtoInterface
from guillotina.contrib.proto.behavior import ProtoBehavior
from guillotina.tests.proto.test_pb2 import DublinCore as DublinCoreProto


class IDublinCore(IProtoInterface):

    __plass__ = DublinCoreProto


@configure.behavior(
    title="Dublin Core fields (Proto)",
    provides=IDublinCore,
    for_="guillotina.interfaces.IResource",
)
class DublinCoreProto(ProtoBehavior):
    auto_serialize = True

    title = ContextProperty("title", None)
    creators = ContextProperty("creators", ())
    contributors = ContextProperty("contributors", ())
    creation_date = ContextProperty("creation_date", None)
    modification_date = ContextProperty("modification_date", None)
    tags = ContextProperty("tags", None)

    def __init__(self, context):
        self.__dict__["context"] = context
        super(DublinCore, self).__init__(context)



pytestmark = pytest.mark.asyncio

async def test_create_contenttype_with_date(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Item", "title": "Item1", "id": "item1"})
        )
        assert status == 201
        date_to_test = "2016-11-30T14:39:07.394273+01:00"
        _, status = await requester(
            "PATCH",
            "/db/guillotina/item1",
            data=json.dumps(
                {
                    "guillotina.behaviors.dublincore.IDublinCore": {
                        "creation_date": date_to_test,
                        "expiration_date": date_to_test,
                    }
                }
            ),
        )

        root = await utils.get_root(db=requester.db)
        async with transaction(db=requester.db, abort_when_done=True):
            container = await root.async_get("guillotina")
            obj = await container.async_get("item1")
            from guillotina.behaviors.dublincore import IDublinCore

            behavior = IDublinCore(obj)
            await behavior.load()
            assert behavior.creation_date.isoformat() == date_to_test  # pylint: disable=E1101
            assert behavior.expiration_date.isoformat() == date_to_test  # pylint: disable=E1101
