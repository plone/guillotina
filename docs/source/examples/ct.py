from guillotina import configure
from guillotina import content
from guillotina import Interface
from guillotina import schema

class IMyType(Interface):
    foobar = schema.TextLine()

@configure.contenttype(
    type_name="MyType",
    schema=IMyType,
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"])
class Foobar(content.Item):
    pass
