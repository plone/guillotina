import typing

from mypy_extensions import TypedDict


class BasicParsedQueryInfo(TypedDict):
    sort_on: typing.Optional[str]
    sort_dir: typing.Optional[str]
    from_: int
    size: int
    full_objects: bool
    metadata: typing.Optional[typing.List[str]]
    excluded_metadata: typing.Optional[typing.List[str]]
    params: typing.Dict[str, typing.Any]
