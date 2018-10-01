from typing import Any
from typing import Dict
from typing import List
from typing import Tuple
from typing import TypeVar

import types


ResolvableType = TypeVar(
    'ResolvableType', types.ModuleType, types.FunctionType, type)

ConfigurationType = List[Tuple[str, Dict[str, Any]]]
ResourceType = 'guillotina.content.Resource'
