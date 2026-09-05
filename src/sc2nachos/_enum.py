"""Base class for the package's enums."""

from enum import IntEnum


class ReadableIntEnum(IntEnum):
    """An `IntEnum` that prints as its name rather than its value.

    Python 3.11 made `IntEnum` format as a bare number, so logs read `48` instead of `UnitTypeId.MARINE`. An
    explicit format spec still formats the integer.
    """

    def __str__(self) -> str:
        return f"{type(self).__name__}.{self.name}"

    def __repr__(self) -> str:
        return f"<{type(self).__name__}.{self.name}: {self.value}>"

    def __format__(self, format_spec: str) -> str:
        if format_spec:
            return int.__format__(int(self), format_spec)
        return str(self)
