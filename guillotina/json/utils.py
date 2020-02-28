from guillotina.component import get_multi_adapter
from guillotina.db.orm.interfaces import IBaseObject
from guillotina.exceptions import RequestNotFound
from guillotina.interfaces import ISchemaSerializeToJson
from guillotina.utils import get_current_request
from typing import Any
from typing import Dict
from typing import List
from typing import Type
from zope.interface import Interface
from zope.interface import Invalid

import asyncio
import logging


logger = logging.getLogger("guillotina")


def convert_interfaces_to_schema(interfaces: List[Type[Interface]]) -> Dict[str, Any]:
    properties = {}
    try:
        request = get_current_request()
    except RequestNotFound:
        from guillotina.tests.utils import get_mocked_request

        request = get_mocked_request()

    for iface in interfaces:
        serializer = get_multi_adapter((iface, request), ISchemaSerializeToJson)
        properties[iface.__identifier__] = serializer.serialize()
    return properties


async def validate_invariants(schema: Type[Interface], obj: IBaseObject) -> List[Invalid]:
    """
    Validate invariants on a schema with async invariant support.
    """
    errors = []
    for call in schema.queryTaggedValue("invariants", []):
        try:
            if asyncio.iscoroutinefunction(call):
                await call(obj)
            else:
                call(obj)
        except Invalid as e:
            errors.append(e)
    for base in schema.__bases__:
        errors.extend(await validate_invariants(base, obj))
    return errors
