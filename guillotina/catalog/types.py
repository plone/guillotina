from mypy_extensions import TypedDict

import typing


class BasicParsedQueryInfo(TypedDict):
    sort_on: typing.Optional[str]
    sort_dir: typing.Optional[str]
    _from: int
    size: int
    fullobjects: bool
    metadata: typing.Optional[typing.List[str]]
    excluded_metadata: typing.Optional[typing.List[str]]
    params: typing.Dict[str, typing.Any]
