"""Ability identifiers.

Hand-maintained: filtered to what multiplayer needs, named for readability. Each member is defined by a raw
catalog member, never a literal id. Unknown ids raise.
"""

from sc2nachos._enum import ReadableIntEnum
from sc2nachos.ids.raw import RawAbilityId


class AbilityId(ReadableIntEnum):
    """Ability ids used in multiplayer games."""

    ARCHON_WARP_TARGET = RawAbilityId.Archon_Warp_Target
    ATTACK = RawAbilityId.Attack
    ATTACK_ATTACK = RawAbilityId.attack_Attack
    BUILD_INTERCEPTORS = RawAbilityId.Build_Interceptors
    BUILD_TECHLAB = RawAbilityId.Build_TechLab
    CALLDOWNMULE_CALLDOWNMULE = RawAbilityId.CalldownMULE_CalldownMULE
    CANCEL = RawAbilityId.Cancel
    EFFECT_MEDIVACIGNITEAFTERBURNERS = RawAbilityId.Effect_MedivacIgniteAfterburners
    EFFECT_REPAIR = RawAbilityId.Effect_Repair
    EFFECT_STIM = RawAbilityId.Effect_Stim
    EFFECT_STIM_MARAUDER = RawAbilityId.Effect_Stim_Marauder
    EFFECT_STIM_MARINE = RawAbilityId.Effect_Stim_Marine
    HALT = RawAbilityId.Halt
    HARVEST_GATHER = RawAbilityId.Harvest_Gather
    HARVEST_GATHER_DRONE = RawAbilityId.Harvest_Gather_Drone
    HARVEST_GATHER_MULE = RawAbilityId.Harvest_Gather_Mule
    HARVEST_GATHER_PROBE = RawAbilityId.Harvest_Gather_Probe
    HARVEST_GATHER_SCV = RawAbilityId.Harvest_Gather_SCV
    HARVEST_RETURN = RawAbilityId.Harvest_Return
    HARVEST_RETURN_DRONE = RawAbilityId.Harvest_Return_Drone
    HARVEST_RETURN_MULE = RawAbilityId.Harvest_Return_Mule
    HARVEST_RETURN_PROBE = RawAbilityId.Harvest_Return_Probe
    HARVEST_RETURN_SCV = RawAbilityId.Harvest_Return_SCV
    LAND = RawAbilityId.Land
    LIFT = RawAbilityId.Lift
    MEDIVACHEAL_HEAL = RawAbilityId.MedivacHeal_Heal
    MORPHTORAVAGER_RAVAGER = RawAbilityId.MorphToRavager_Ravager
    MORPHZERGLINGTOBANELING_BANELING = RawAbilityId.MorphZerglingToBaneling_Baneling
    MORPH_LURKER = RawAbilityId.Morph_Lurker
    MORPH_SUPPLYDEPOT_LOWER = RawAbilityId.Morph_SupplyDepot_Lower
    MORPH_SUPPLYDEPOT_RAISE = RawAbilityId.Morph_SupplyDepot_Raise
    MOVE = RawAbilityId.Move
    MOVE_MOVE = RawAbilityId.Move_Move
    NULL_NULL = RawAbilityId.Null_Null
    PROTOSSBUILD_ASSIMILATOR = RawAbilityId.ProtossBuild_Assimilator
    SCANNERSWEEP_SCAN = RawAbilityId.ScannerSweep_Scan
    SMART = RawAbilityId.Smart
    SPAWNCHANGELING_SPAWNCHANGELING = RawAbilityId.SpawnChangeling_SpawnChangeling
    TERRANBUILD_ARMORY = RawAbilityId.TerranBuild_Armory
    TERRANBUILD_BARRACKS = RawAbilityId.TerranBuild_Barracks
    TERRANBUILD_COMMANDCENTER = RawAbilityId.TerranBuild_CommandCenter
    TERRANBUILD_ENGINEERINGBAY = RawAbilityId.TerranBuild_EngineeringBay
    TERRANBUILD_FACTORY = RawAbilityId.TerranBuild_Factory
    TERRANBUILD_REFINERY = RawAbilityId.TerranBuild_Refinery
    TERRANBUILD_SUPPLYDEPOT = RawAbilityId.TerranBuild_SupplyDepot
    UNLOADALL_BUNKER = RawAbilityId.UnloadAll_Bunker
    ZERGBUILD_EXTRACTOR = RawAbilityId.ZergBuild_Extractor
