from guillotina.schema.interfaces import IField
from zope.interface import Interface


class IPatchField(IField):
    pass


class IDynamicField(IField):
    pass


class IBucketListField(IField):
    pass


class IBucketDictField(IField):
    pass


class IPatchFieldOperation(Interface):
    def __init__(field):
        """
        Adapter against original field patch is being made on
        """

    def __call__(ob, value):
        """
        set the value on the object
        """


class IDynamicFieldOperation(IPatchFieldOperation):
    """
    """
