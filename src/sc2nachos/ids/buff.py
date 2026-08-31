"""Buff identifiers.

Hand-maintained: filtered to what multiplayer needs, named for readability. Each member is defined by a raw
catalog member, never a literal id. Unknown ids raise.
"""

from sc2nachos.ids._base import ReadableIntEnum
from sc2nachos.ids.raw import RawBuffId


class BuffId(ReadableIntEnum):
    """Buff ids used in multiplayer games."""

    DUTCHMARAUDERSLOW = RawBuffId.DutchMarauderSlow
    GUARDIANSHIELD = RawBuffId.GuardianShield
    IMMORTALOVERLOAD = RawBuffId.ImmortalOverload
    SLOW = RawBuffId.Slow
    STIMPACK = RawBuffId.Stimpack
    STIMPACKMARAUDER = RawBuffId.StimpackMarauder
