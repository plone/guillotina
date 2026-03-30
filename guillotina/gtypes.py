import types
from typing import Any, Dict, List, Tuple, TypeVar


ResolvableType = TypeVar("ResolvableType", types.ModuleType, types.FunctionType, type)

ConfigurationType = List[Tuple[str, Dict[str, Any]]]
ResourceType = "guillotina.content.Resource"
