from typing import Any, Type, TypeVar

_T = TypeVar("_T")

Inject = object()
NoCache = object()


class Impl:
    def __init__(self, type_: Any):
        self.type = type_

    def __class_getitem__(cls, item: Type) -> "Impl":
        return cls(item)
