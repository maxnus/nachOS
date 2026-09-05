"""Upgrade identifiers.

Hand-maintained: filtered to what multiplayer needs, named for readability. Each member is defined by a raw
catalog member, never a literal id. Unknown ids raise.
"""

from sc2nachos._enum import ReadableIntEnum
from sc2nachos.ids.raw import RawUpgradeId


class UpgradeId(ReadableIntEnum):
    """Upgrade ids used in multiplayer games."""

    BANSHEECLOAK = RawUpgradeId.BansheeCloak
    BANSHEESPEED = RawUpgradeId.BansheeSpeed
    BATTLECRUISERENABLESPECIALIZATIONS = RawUpgradeId.BattlecruiserEnableSpecializations
    DRILLCLAWS = RawUpgradeId.DrillClaws
    ENHANCEDSHOCKWAVES = RawUpgradeId.EnhancedShockwaves
    HISECAUTOTRACKING = RawUpgradeId.HiSecAutoTracking
    LIBERATORAGRANGEUPGRADE = RawUpgradeId.LiberatorAGRangeUpgrade
    MEDIVACINCREASESPEEDBOOST = RawUpgradeId.MedivacIncreaseSpeedBoost
    PERSONALCLOAKING = RawUpgradeId.PersonalCloaking
    PUNISHERGRENADES = RawUpgradeId.PunisherGrenades
    RAVENRECALIBRATEDEXPLOSIVES = RawUpgradeId.RavenRecalibratedExplosives
    SHIELDWALL = RawUpgradeId.ShieldWall
    SMARTSERVOS = RawUpgradeId.SmartServos
    STIMPACK = RawUpgradeId.Stimpack
    TERRANBUILDINGARMOR = RawUpgradeId.TerranBuildingArmor
    TERRANINFANTRYARMORSLEVEL1 = RawUpgradeId.TerranInfantryArmorsLevel1
    TERRANINFANTRYARMORSLEVEL2 = RawUpgradeId.TerranInfantryArmorsLevel2
    TERRANINFANTRYARMORSLEVEL3 = RawUpgradeId.TerranInfantryArmorsLevel3
    TERRANINFANTRYWEAPONSLEVEL1 = RawUpgradeId.TerranInfantryWeaponsLevel1
    TERRANINFANTRYWEAPONSLEVEL2 = RawUpgradeId.TerranInfantryWeaponsLevel2
    TERRANINFANTRYWEAPONSLEVEL3 = RawUpgradeId.TerranInfantryWeaponsLevel3
    TERRANSHIPARMORSLEVEL1 = RawUpgradeId.TerranShipArmorsLevel1
    TERRANSHIPARMORSLEVEL2 = RawUpgradeId.TerranShipArmorsLevel2
    TERRANSHIPARMORSLEVEL3 = RawUpgradeId.TerranShipArmorsLevel3
    TERRANSHIPWEAPONSLEVEL1 = RawUpgradeId.TerranShipWeaponsLevel1
    TERRANSHIPWEAPONSLEVEL2 = RawUpgradeId.TerranShipWeaponsLevel2
    TERRANSHIPWEAPONSLEVEL3 = RawUpgradeId.TerranShipWeaponsLevel3
    TERRANVEHICLEANDSHIPARMORSLEVEL1 = RawUpgradeId.TerranVehicleAndShipArmorsLevel1
    TERRANVEHICLEANDSHIPARMORSLEVEL2 = RawUpgradeId.TerranVehicleAndShipArmorsLevel2
    TERRANVEHICLEANDSHIPARMORSLEVEL3 = RawUpgradeId.TerranVehicleAndShipArmorsLevel3
    TERRANVEHICLEARMORSLEVEL1 = RawUpgradeId.TerranVehicleArmorsLevel1
    TERRANVEHICLEARMORSLEVEL2 = RawUpgradeId.TerranVehicleArmorsLevel2
    TERRANVEHICLEARMORSLEVEL3 = RawUpgradeId.TerranVehicleArmorsLevel3
    TERRANVEHICLEWEAPONSLEVEL1 = RawUpgradeId.TerranVehicleWeaponsLevel1
    TERRANVEHICLEWEAPONSLEVEL2 = RawUpgradeId.TerranVehicleWeaponsLevel2
    TERRANVEHICLEWEAPONSLEVEL3 = RawUpgradeId.TerranVehicleWeaponsLevel3
