# Curating ids

The curated enums in `sc2nachos/ids/` name only what is really in the game, so "does this still exist?" comes up
constantly. Answer it from these.

## Where to look

- **Liquipedia** is the source of record for units, abilities and upgrades, and it dates removals -- a page's
  `Removed Upgrades` section names the patch that took one out. The page URL returns HTTP 403 to automated
  fetches, so read the wikitext through the API instead:
  `https://liquipedia.net/starcraft2/api.php?action=parse&page=Raven_(Legacy_of_the_Void)&prop=wikitext&format=json`
- **What a live structure offers** is the only direct evidence that an upgrade is researchable:
  `query_available_abilities` on a debug-created structure. An armory offers vehicle weapons, ship weapons and
  vehicle and ship plating, and nothing else -- vehicle plating and ship plating are dead halves of a 2012 merge.
- **A price is not evidence.** Dead upgrades keep theirs: vehicle plating still answers ability 852 at 100/100
  after fourteen years. Only an entry with no ability, no cost and no research time at all (Enhanced Shockwaves)
  is caught from `RequestData` alone.
- **`friendlyname` in `stableid.json`** carries what an ability is called -- `Research BattlecruiserWeaponRefit`
  named the upgrade that became `YAMATO_CANNON`.

## Refreshing `data/stableid.json`

**The file depends on the map.** SC2 rewrites it on every launch from the loaded map's mod dependencies:
BerlingradAIE (2022) yields 518 ability ids that MagannathaAIE does not, and shifts a couple of dozen shared names
by +312 or +316. So after a patch, launch a current ladder map, copy the file the game wrote
(`~/Documents/StarCraft II/stableid.json` on Windows) over `data/stableid.json`, and run
`uv run python tools/generate_ids.py`.
