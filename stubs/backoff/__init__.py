from typing import Callable
from typing import Optional
from typing import Tuple
from typing import Type


expo = "expo"


def on_exception(
    type_,
    exceptions: Tuple[Type[Exception], ...],
    max_time: Optional[int] = None,
    max_tries: Optional[int] = None,
) -> Callable:
    ...
