"""Naming an id one of the game's tables points at."""

from sc2nachos._enum import ReadableIntEnum


def curated[IdT: ReadableIntEnum](enum: type[IdT], value: int) -> IdT | None:
    """The member of `enum` that `value` names, or `None` where it is zero or the enum leaves it out."""
    if not value:
        return None
    try:
        return enum(value)
    except ValueError:
        return None
