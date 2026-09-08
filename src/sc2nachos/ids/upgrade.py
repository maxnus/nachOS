"""Upgrade identifiers.

Hand-maintained: filtered to what multiplayer needs, named for readability. Each member is defined by a raw
catalog member, never a literal id. Unknown ids raise.
"""

from sc2nachos._enum import ReadableIntEnum
from sc2nachos.ids.raw import RawUpgradeId


class UpgradeId(ReadableIntEnum):
    """Upgrade ids used in multiplayer games."""

    BANSHEE_CLOAK = RawUpgradeId.BansheeCloak  # "Cloaking Field" in game
    BANSHEE_SPEED = RawUpgradeId.BansheeSpeed  # "Hyperflight Rotors" in game
    BUILDING_ARMOR = RawUpgradeId.TerranBuildingArmor
    COMBAT_SHIELD = RawUpgradeId.ShieldWall
    CONCUSSIVE_SHELLS = RawUpgradeId.PunisherGrenades
    DRILLING_CLAWS = RawUpgradeId.DrillClaws
    ENHANCED_SHOCKWAVES = RawUpgradeId.EnhancedShockwaves
    HISEC_AUTO_TRACKING = RawUpgradeId.HiSecAutoTracking
    INFANTRY_ARMOR_1 = RawUpgradeId.TerranInfantryArmorsLevel1
    INFANTRY_ARMOR_2 = RawUpgradeId.TerranInfantryArmorsLevel2
    INFANTRY_ARMOR_3 = RawUpgradeId.TerranInfantryArmorsLevel3
    INFANTRY_WEAPONS_1 = RawUpgradeId.TerranInfantryWeaponsLevel1
    INFANTRY_WEAPONS_2 = RawUpgradeId.TerranInfantryWeaponsLevel2
    INFANTRY_WEAPONS_3 = RawUpgradeId.TerranInfantryWeaponsLevel3
    LIBERATOR_RANGE = RawUpgradeId.LiberatorAGRangeUpgrade  # "Advanced Ballistics" in game
    MEDIVAC_SPEED_BOOST = RawUpgradeId.MedivacIncreaseSpeedBoost  # "Rapid Reignition System" in game
    PERSONAL_CLOAKING = RawUpgradeId.PersonalCloaking
    RAVEN_RECALIBRATED_EXPLOSIVES = RawUpgradeId.RavenRecalibratedExplosives
    SHIP_ARMOR_1 = RawUpgradeId.TerranShipArmorsLevel1  # "Ship Plating" in game
    SHIP_ARMOR_2 = RawUpgradeId.TerranShipArmorsLevel2
    SHIP_ARMOR_3 = RawUpgradeId.TerranShipArmorsLevel3
    SHIP_WEAPONS_1 = RawUpgradeId.TerranShipWeaponsLevel1
    SHIP_WEAPONS_2 = RawUpgradeId.TerranShipWeaponsLevel2
    SHIP_WEAPONS_3 = RawUpgradeId.TerranShipWeaponsLevel3
    SMART_SERVOS = RawUpgradeId.SmartServos
    STIMPACK = RawUpgradeId.Stimpack
    VEHICLE_AND_SHIP_ARMOR_1 = RawUpgradeId.TerranVehicleAndShipArmorsLevel1  # "Vehicle and Ship Plating" in game
    VEHICLE_AND_SHIP_ARMOR_2 = RawUpgradeId.TerranVehicleAndShipArmorsLevel2
    VEHICLE_AND_SHIP_ARMOR_3 = RawUpgradeId.TerranVehicleAndShipArmorsLevel3
    VEHICLE_ARMOR_1 = RawUpgradeId.TerranVehicleArmorsLevel1  # "Vehicle Plating" in game
    VEHICLE_ARMOR_2 = RawUpgradeId.TerranVehicleArmorsLevel2
    VEHICLE_ARMOR_3 = RawUpgradeId.TerranVehicleArmorsLevel3
    VEHICLE_WEAPONS_1 = RawUpgradeId.TerranVehicleWeaponsLevel1
    VEHICLE_WEAPONS_2 = RawUpgradeId.TerranVehicleWeaponsLevel2
    VEHICLE_WEAPONS_3 = RawUpgradeId.TerranVehicleWeaponsLevel3
    WEAPON_REFIT = RawUpgradeId.BattlecruiserEnableSpecializations  # unlocks the yamato cannon
