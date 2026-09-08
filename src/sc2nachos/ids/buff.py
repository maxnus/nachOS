"""Buff identifiers.

Hand-maintained: filtered to what multiplayer needs, named for readability. Each member is defined by a raw
catalog member, never a literal id. Unknown ids raise.
"""

from sc2nachos._enum import ReadableIntEnum
from sc2nachos.ids.raw import RawBuffId


class BuffId(ReadableIntEnum):
    """Buff ids used in multiplayer games."""

    CONCUSSIVE_SHELLS_SLOW = RawBuffId.DutchMarauderSlow
    GUARDIAN_SHIELD = RawBuffId.GuardianShield
    IMMORTAL_BARRIER = RawBuffId.ImmortalOverload
    SLOW = RawBuffId.Slow
    STIMPACK = RawBuffId.Stimpack
    STIMPACK_MARAUDER = RawBuffId.StimpackMarauder
