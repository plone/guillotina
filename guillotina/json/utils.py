from guillotina.component import get_multi_adapter
from guillotina.exceptions import RequestNotFound
from guillotina.interfaces import ISchemaSerializeToJson
from guillotina.utils import get_current_request

import logging


logger = logging.getLogger('guillotina')


def convert_interfaces_to_schema(interfaces):
    properties = {}
    try:
        request = get_current_request()
    except RequestNotFound:
        from guillotina.tests.utils import get_mocked_request
        request = get_mocked_request()

    for iface in interfaces:
        serializer = get_multi_adapter(
            (iface, request), ISchemaSerializeToJson)
        properties[iface.__identifier__] = serializer.serialize()
    return properties
