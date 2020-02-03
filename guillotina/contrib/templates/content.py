from guillotina.content import Resource
from guillotina import configure
from guillotina.contrib.templates.interfaces import IJinjaTemplate


@configure.contenttype(
    type_name="JinjaTemplate",
    schema=IJinjaTemplate,
    add_permission="guillotina.AddJinjaTemplate",
    behaviors=["guillotina.behaviors.interfaces.IDublinCore"],
    allowed_types=[],
)
class JinjaTemplate(Resource):
    pass
