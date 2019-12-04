from typing import Any
from typing import Dict, Optional, Union
from multidict import CIMultiDict


class TestClient(object):
    def __init__(
        self,
        application: Any,
        use_cookies: bool = True,
        timeout: Optional[int] = None,
        headers: Optional[Union[dict, CIMultiDict]] = None,
    ):
        ...
