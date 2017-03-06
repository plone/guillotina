##############################################################################
#
# Copyright (c) 2003 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Utilities for the 'nested directive' section in the narrative docs.
"""

from zope.interface import Attribute
from zope.interface import Interface
from zope.interface import implementer
from guillotina.schema import BytesLine
from guillotina.schema import Id
from guillotina.schema import Int
from guillotina.schema import Text
from guillotina.schema import TextLine
from guillotina.configuration.config import GroupingContextDecorator
from guillotina.configuration.config import IConfigurationContext
from guillotina.configuration.fields import Bool
from guillotina.configuration._compat import u


schema_registry = {}

class ISchemaInfo(Interface):
    """Parameter schema for the schema directive
    """

    name = TextLine(
        title=u("The schema name"),
        description=u("This is a descriptive name for the schema."),
        )

    id = Id(title=u("The unique id for the schema"))

class ISchema(Interface):
    """Interface that distinguishes the schema directive
    """

    fields = Attribute("Dictionary of field definitions")
    

@implementer(IConfigurationContext, ISchema)
class Schema(GroupingContextDecorator):
    """Handle schema directives
    """


    def __init__(self, context, name, id):
        self.context, self.name, self.id = context, name, id
        self.fields = {}

    def after(self):
        schema = Interface.__class__(
            self.name,
            (Interface, ),
            self.fields
            )
        schema.__doc__ = self.info.text.strip()
        self.action(
            discriminator=('schema', self.id),
            callable=schema_registry.__setitem__,
            args=(self.id, schema),
            )
        

class IFieldInfo(Interface):

    name = BytesLine(
        title=u("The field name"),
        )

    title = TextLine(
        title=u("Title"),
        description=u("A short summary or label"),
        default=u(""),
        required=False,
        )

    required = Bool(
        title=u("Required"),
        description=u("Determines whether a value is required."),
        default=True)

    readonly = Bool(
        title=u("Read Only"),
        description=u("Can the value be modified?"),
        required=False,
        default=False)

class ITextInfo(IFieldInfo):

    min_length = Int(
        title=u("Minimum length"),
        description=u("Value after whitespace processing cannot have less than "
                      "min_length characters. If min_length is None, there is "
                      "no minimum."),
        required=False,
        min=0, # needs to be a positive number
        default=0)

    max_length = Int(
        title=u("Maximum length"),
        description=u("Value after whitespace processing cannot have greater "
                      "or equal than max_length characters. If max_length is "
                      "None, there is no maximum."),
        required=False,
        min=0, # needs to be a positive number
        default=None)

def field(context, constructor, name, **kw):

    # Compute the field
    field = constructor(description=context.info.text.strip(), **kw)

    # Save it in the schema's field dictionary
    schema = context.context
    if name in schema.fields:
        raise ValueError("Duplicate field", name)
    schema.fields[name] = field

    
def textField(context, **kw):
    field(context, Text, **kw)

class IIntInfo(IFieldInfo):

    min = Int(
        title=u("Start of the range"),
        required=False,
        default=None
        )

    max = Int(
        title=u("End of the range (excluding the value itself)"),
        required=False,
        default=None
        )
    
def intField(context, **kw):
    field(context, Int, **kw)
