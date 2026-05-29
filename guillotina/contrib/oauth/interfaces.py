from zope.interface import Interface


class IOAuthStorageUtility(Interface):
    """Utility that initializes OAuth storage backends and runs periodic cleanup."""
