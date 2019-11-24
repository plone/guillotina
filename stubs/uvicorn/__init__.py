from typing import Any
from typing import Dict


class Config(object):
    def __init__(self, app: Any, **kwargs: Dict):
        ...


class Server(object):
    def __init__(self, config: Config):
        ...