from guillotina.interfaces import IAsyncUtility
from guillotina.interfaces import IItem
from guillotina import schema


class IJinjaUtility(IAsyncUtility):
    pass


class IJinjaTemplate(IItem):

    template = schema.Text(title='Jinja Template')
