from typing import Any
from typing import Dict


class Validator:
    def check_schema(self, schema: Dict[str, Any]):
        ...

    def __call__(self, schema: Dict[str, Any]) -> "Validator":
        ...


def validator_for(schema: Dict[str, Any]) -> Validator:
    ...
