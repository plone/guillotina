from typing import Any
from typing import Dict


class RefResolver:
    @classmethod
    def from_schema(cls, schema) -> "RefResolver":
        ...


class Validator:
    def __init__(self):
        ...

    def check_schema(self, schema: Dict[str, Any]):
        ...

    def __call__(self, schema: Dict[str, Any], resolver: RefResolver) -> "Validator":
        ...


def validator_for(schema: Dict[str, Any]) -> Validator:
    ...
