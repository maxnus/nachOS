"""Buff identifiers.

Hand-maintained: filtered to what multiplayer needs, named for readability. Each member is defined by a raw
catalog member, never a literal id. Unknown ids raise.
"""

from sc2nachos._enum import ReadableIntEnum
from sc2nachos.ids.raw import RawBuffId


class BuffId(ReadableIntEnum):
    """Buff ids used in multiplayer games."""

    CARRYING_GAS = RawBuffId.CarryHarvestableVespeneGeyserGas
    CARRYING_GAS_PROTOSS = RawBuffId.CarryHarvestableVespeneGeyserGasProtoss
    CARRYING_GAS_ZERG = RawBuffId.CarryHarvestableVespeneGeyserGasZerg
    CARRYING_MINERALS = RawBuffId.CarryMineralFieldMinerals
    CARRYING_MINERALS_RICH = RawBuffId.CarryHighYieldMineralFieldMinerals
    CONCUSSIVE_SHELLS_SLOW = RawBuffId.DutchMarauderSlow
    FUNGAL_GROWTH = RawBuffId.FungalGrowth
    GRAVITON_BEAM = RawBuffId.GravitonBeam
    GUARDIAN_SHIELD = RawBuffId.GuardianShield
    IMMORTAL_BARRIER = RawBuffId.ImmortalOverload
    PRISMATIC_ALIGNMENT = RawBuffId.VoidRaySwarmDamageBoost
    SLOW = RawBuffId.Slow
    STIMPACK = RawBuffId.Stimpack
    STIMPACK_MARAUDER = RawBuffId.StimpackMarauder
