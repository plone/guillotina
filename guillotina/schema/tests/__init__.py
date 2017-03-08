#
# This file is necessary to make this directory a package.

from zope.testing import renormalizing

import re


py3_checker = renormalizing.RENormalizing([
    (re.compile(r"u'([^']*)'"), r"'\1'"),
    (re.compile(r"^b'([^']*)'"), r"'\1'"),
    (re.compile(r"([^'])b'([^']*)'"), r"\1'\2'"),
    (re.compile(r"<class 'bytes'>"), r"<type 'str'>"),
    (re.compile(r"<class 'str'>"), r"<type 'unicode'>"),
    (re.compile(
        r"guillotina.schema._bootstrapinterfaces.InvalidValue"),
        r"InvalidValue"),
    (re.compile(
        r"guillotina.schema.interfaces.InvalidId: '([^']*)'"),
        r"InvalidId: \1"),
    (re.compile(
        r"guillotina.schema.interfaces.InvalidId:"),
        r"InvalidId:"),
    (re.compile(
        r"guillotina.schema.interfaces.InvalidURI: '([^']*)'"),
        r"InvalidURI: \1"),
    (re.compile(
        r"guillotina.schema.interfaces.InvalidURI:"),
        r"InvalidURI:"),
    (re.compile(
        r"guillotina.schema.interfaces.InvalidDottedName: '([^']*)'"),
        r"InvalidDottedName: \1"),
    (re.compile(
        r"guillotina.schema.interfaces.InvalidDottedName:"),
        r"InvalidDottedName:"),
    (re.compile(
        r"guillotina.schema._bootstrapinterfaces.ConstraintNotSatisfied: '([^']*)'"),
        r"ConstraintNotSatisfied: \1"),
    (re.compile(
        r"guillotina.schema._bootstrapinterfaces.ConstraintNotSatisfied:"),
        r"ConstraintNotSatisfied:"),
    (re.compile(
        r"guillotina.schema._bootstrapinterfaces.WrongType:"),
        r"WrongType:"),
  ])
