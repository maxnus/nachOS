"""Ability identifiers.

Hand-maintained: filtered to what multiplayer needs, named for readability. Each member is defined by a raw
catalog member, never a literal id. Unknown ids raise.
"""

from sc2nachos._enum import ReadableIntEnum
from sc2nachos.ids.raw import RawAbilityId


class AbilityId(ReadableIntEnum):
    """Ability ids used in multiplayer games."""

    ARCHON_WARP_TARGET = RawAbilityId.Archon_Warp_Target
    ATTACK = RawAbilityId.Attack  # the order you give; a unit reports ATTACK_EXACT
    ATTACK_EXACT = RawAbilityId.attack_Attack  # the order a unit reports running; you give ATTACK
    BUILD_ARMORY = RawAbilityId.TerranBuild_Armory
    BUILD_ASSIMILATOR = RawAbilityId.ProtossBuild_Assimilator
    BUILD_BARRACKS = RawAbilityId.TerranBuild_Barracks
    BUILD_COMMAND_CENTER = RawAbilityId.TerranBuild_CommandCenter
    BUILD_ENGINEERING_BAY = RawAbilityId.TerranBuild_EngineeringBay
    BUILD_EXTRACTOR = RawAbilityId.ZergBuild_Extractor
    BUILD_FACTORY = RawAbilityId.TerranBuild_Factory
    BUILD_INTERCEPTORS = RawAbilityId.Build_Interceptors
    BUILD_REFINERY = RawAbilityId.TerranBuild_Refinery
    BUILD_SUPPLY_DEPOT = RawAbilityId.TerranBuild_SupplyDepot
    BUILD_TECH_LAB = RawAbilityId.Build_TechLab
    CALLDOWN_MULE = RawAbilityId.CalldownMULE_CalldownMULE
    CANCEL = RawAbilityId.Cancel
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
    LOWER_SUPPLY_DEPOT = RawAbilityId.Morph_SupplyDepot_Lower
    MEDIVAC_BOOST = RawAbilityId.Effect_MedivacIgniteAfterburners
    MEDIVAC_HEAL = RawAbilityId.MedivacHeal_Heal
    MORPH_TO_BANELING = RawAbilityId.MorphZerglingToBaneling_Baneling
    MORPH_TO_LURKER = RawAbilityId.Morph_Lurker
    MORPH_TO_RAVAGER = RawAbilityId.MorphToRavager_Ravager
    MOVE = RawAbilityId.Move  # the order you give; a unit reports MOVE_EXACT
    MOVE_EXACT = RawAbilityId.Move_Move  # the order a unit reports running; you give MOVE
    NULL = RawAbilityId.Null_Null
    RAISE_SUPPLY_DEPOT = RawAbilityId.Morph_SupplyDepot_Raise
    REPAIR = RawAbilityId.Effect_Repair
    SCANNER_SWEEP = RawAbilityId.ScannerSweep_Scan
    SMART = RawAbilityId.Smart  # the right-click order
    SPAWN_CHANGELING = RawAbilityId.SpawnChangeling_SpawnChangeling
    STIM = RawAbilityId.Effect_Stim
    STIM_MARAUDER = RawAbilityId.Effect_Stim_Marauder
    STIM_MARINE = RawAbilityId.Effect_Stim_Marine
    UNLOAD_ALL_BUNKER = RawAbilityId.UnloadAll_Bunker
