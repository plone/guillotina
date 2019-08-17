##############################################################################
#
# Copyright (c) 2002 Zope Foundation and Contributors.
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
import guillotina.schema
import zope.interface.verify


def getFieldNames(schema):
    """Return a list of all the Field names in a schema.
    """
    from guillotina.schema.interfaces import IField

    return [name for name in schema if IField.providedBy(schema[name])]


def get_fields(schema):
    """Return a dictionary containing all the Fields in a schema.
    """
    from guillotina.schema.interfaces import IField

    fields = {}
    for name in schema:
        attr = schema[name]
        if IField.providedBy(attr):
            fields[name] = attr
    return fields


def get_fields_in_order(schema, _field_key=lambda x: x[1].order):
    """Return a list of (name, value) tuples in native schema order.
    """
    return sorted(get_fields(schema).items(), key=_field_key)


def getFieldNamesInOrder(schema):
    """Return a list of all the Field names in a schema in schema order.
    """
    return [name for name, field in get_fields_in_order(schema)]


def getValidationErrors(schema, object):
    """Return a list of all validation errors.
    """
    errors = getSchemaValidationErrors(schema, object)
    if errors:
        return errors

    # Only validate invariants if there were no previous errors. Previous
    # errors could be missing attributes which would most likely make an
    # invariant raise an AttributeError.
    invariant_errors = []
    try:
        schema.validateInvariants(object, invariant_errors)
    except zope.interface.exceptions.Invalid:
        # Just collect errors
        pass
    errors = [(None, e) for e in invariant_errors]
    return errors


def getSchemaValidationErrors(schema, object):
    errors = []
    for name in schema.names(all=True):
        if zope.interface.interfaces.IMethod.providedBy(schema[name]):
            continue
        attribute = schema[name]
        if not guillotina.schema.interfaces.IField.providedBy(attribute):
            continue
        try:
            value = getattr(object, name)
        except AttributeError as error:
            # property for the given name is not implemented
            errors.append((name, guillotina.schema.exceptions.SchemaNotFullyImplemented(error)))
        else:
            try:
                attribute.bind(object).validate(value)
            except guillotina.schema.ValidationError as e:
                errors.append((name, e))
    return errors
