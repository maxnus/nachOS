"""Effect identifiers.

Hand-maintained: filtered to what multiplayer needs, named for readability. Each member is defined by a raw
catalog member, never a literal id. Unknown ids raise.
"""

from sc2nachos._enum import ReadableIntEnum
from sc2nachos.ids.raw import RawEffectId


class EffectId(ReadableIntEnum):
    """Effect ids used in multiplayer games."""

    BLINDING_CLOUD = RawEffectId.BlindingCloudCP
    COLOSSUS_BEAM = RawEffectId.ThermalLancesForward  # "Thermal Lances" in game
    CORROSIVE_BILE = RawEffectId.RavagerCorrosiveBileCP
    GUARDIAN_SHIELD = RawEffectId.GuardianShieldPersistent
    LIBERATOR_ZONE = RawEffectId.LiberatorTargetMorphPersistent
    LIBERATOR_ZONE_PENDING = RawEffectId.LiberatorTargetMorphDelayPersistent  # placed, firing in 2 seconds
    LURKER_SPINES = RawEffectId.LurkerMP
    NUKE = RawEffectId.NukePersistent
    PSI_STORM = RawEffectId.PsiStormPersistent
    SCANNER_SWEEP = RawEffectId.ScannerSweep
    TIME_WARP = RawEffectId.TemporalFieldAfterBubbleCreatePersistent
    TIME_WARP_PENDING = RawEffectId.TemporalFieldGrowingBubbleCreatePersistent  # cast, slowing in 1.8 seconds
