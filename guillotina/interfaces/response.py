from zope.interface import Interface
from zope.interface import Attribute


class IResponse(Interface):
    status_code = Attribute('status code')
    content = Attribute('content')
    headers = Attribute('headers')

    def __init__(content=None, headers=None):
        '''
        '''


class IAioHTTPResponse(Interface):
    '''
    Mark aiohttp responses with interface
    '''
