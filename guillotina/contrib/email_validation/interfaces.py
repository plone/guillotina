from zope.interface import Interface
from guillotina import schema


class IValidationSettings(Interface):

    site_url = schema.Text(
        title="Public frontend site url",
        description="Full url without tailing /",
        default="http://localhost:4200"
    )

    validation_template = schema.Text(
        title="Validation template",
        description="Template id or path to object",
        default="validate.html"
    )

    validation_url = schema.Text(
        title="Validation frontend tail url",
        description="Tail url starting with /",
        default="/@@validation"
    )
