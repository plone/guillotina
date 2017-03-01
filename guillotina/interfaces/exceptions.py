from zope.interface import Interface


class ISerializableException(Interface):
    """
    An exception that can be deserialized
    """

    def json_data():
        """
        return json serializable data to be used
        with exception data in responses
        """
