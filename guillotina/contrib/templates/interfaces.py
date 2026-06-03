from guillotina import schema
from guillotina.interfaces import IAsyncUtility, IItem


class IJinjaUtility(IAsyncUtility):
    pass


class IJinjaTemplate(IItem):

    template = schema.Text(title="Jinja Template")
