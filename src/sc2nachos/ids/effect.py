"""Effect identifiers.

Hand-maintained: filtered to what multiplayer needs, named for readability. Each member is defined by a raw
catalog member, never a literal id. Unknown ids raise.
"""

from sc2nachos._enum import ReadableIntEnum
from sc2nachos.ids.raw import RawEffectId


class EffectId(ReadableIntEnum):
    """Effect ids used in multiplayer games."""

    CORROSIVE_BILE = RawEffectId.RavagerCorrosiveBileCP
    PSI_STORM = RawEffectId.PsiStormPersistent
