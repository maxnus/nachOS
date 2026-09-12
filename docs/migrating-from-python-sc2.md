# Migrating from python-sc2

For bots moving over from [python-sc2](https://github.com/BurnySc2/python-sc2), the `burnysc2` package imported as
`sc2`. NachOS is not a drop-in replacement. This page lists the places where the obvious translation of python-sc2
code goes wrong. It covers what NachOS has so far, and grows with it.

## Running a game

- **Nothing is subclassed, and nothing is `async`.** Construct an `Api`, at import time if you like, and hand it
  to a runner along with the race it plays: `run_local("PylonAIE_v4", ApiBot(api, Race.TERRAN), Computer(Race.ZERG))`.
- **A turn is one step unless you say otherwise.** Use `Api(steps_per_turn=4)` to match python-sc2, whose
  `client.game_step` defaults to 4. The value is fixed for the life of the api and cannot be changed mid-game.
- **`Computer()` defaults to very hard, with a random race and build.** python-sc2's `Computer` requires a race
  and defaults to easy.
- **A game holds one bot and at most one computer.** Every current map has two slots, and the game drops extra
  players without saying so. Two bots cannot share a process.
- **`run_local`'s `time_limit` calls the game a tie at the first turn at or past the limit.** python-sc2's
  `game_time_limit` waits for the first turn strictly past it. `run_ladder` takes no limit, because a bot ends a
  game early only by leaving it, and leaving concedes it.
- **A map name can resolve to a different file.** NachOS searches every folder under `Maps`. When several copies
  match, it takes the shallowest, and the first alphabetically among copies at the same depth. python-sc2 searches
  two levels deep and takes whichever match the filesystem lists first.
- **`run_ladder` takes the address and ports as arguments.** Reading `--LadderServer`, `--GamePort` and
  `--StartPort` from the ladder's command line is up to you.
- **One api plays any number of games.** Each game starts from nothing. Before the first game, everything that
  belongs to a game, such as `api.step` or `api.map`, raises `NotPlayingError`.
- **New: recordings.** Both runners accept `record_to=path`, which writes the whole conversation with the game to
  `path`. A `Client` over `ReplayTransport(Recording(path))` then plays it back with no game running. A run that
  is killed before it finishes leaves only part of the file.

## Errors

- **Everything NachOS raises for a failure of its own is a `NachOSError`.** python-sc2's `ProtocolError` whose
  `is_game_over_error` is true is `GameEndedError` here, and its `ConnectionAlreadyClosedError` is
  `ConnectionClosedError`. Where a built-in fits, the error is one too: `ConnectionClosedError` is a
  `ConnectionError`, and `ConnectionTimeoutError` a `TimeoutError`.

## Time

- **One game loop is one step.** `api.step` is python-sc2's `state.game_loop`, and `api.time` is its `time`.
- **`api.time` differs from python-sc2's `time` in the last bit on about a quarter of steps.** Neither 22.4 nor
  1 / 22.4 is exact in binary. python-sc2 divides by 22.4 and NachOS multiplies by 1 / 22.4, and the two results
  round differently. NachOS lands exactly on every whole second. python-sc2 overshoots the whole seconds in the
  top quarter of each power of two, so 15 seconds comes out as `15.000000000000002` and 60 as
  `60.00000000000001`. A test that compares the two needs a tolerance.

## Ids

- **The numbers are the same, but the names often are not.** The curated enums use the names players use:
  `PUNISHERGRENADES` is `CONCUSSIVE_SHELLS`, `TERRANBUILD_BARRACKS` is `BUILD_BARRACKS`, and `ADEPTPHASESHIFT` is
  `ADEPT_SHADE`. `UnitTypeId(old.value)` translates one to the other.
- **The curated enums hold only what a melee game needs.** Converting an id they leave out raises `ValueError`.
  `sc2nachos.ids.raw` holds every id, under Blizzard's own names.
- **Ids are ints.** They are `IntEnum`s, so `UnitTypeId.MARINE == 48` is true. python-sc2's ids are plain
  `Enum`s, for which it is false.
- **The match enums are upper case**: `Race.TERRAN`, `Difficulty.VERY_HARD`, `Result.VICTORY`, and
  `AIBuild.RANDOM` for python-sc2's `AIBuild.RandomBuild`. They are `IntEnum`s too.

## Points, areas and grids

| python-sc2 | NachOS |
|---|---|
| `Point2`, `Point3` | `Point`, `Point3D` |
| `Rect` | `Rectangle`, which is neither a point nor a tuple |
| `PixelMap` | `Grid` |
| `p.to2`, `p.to3` | `p.ground`, `p.with_height(z)` |
| `p.offset(q)` | `p + q` |
| `p.rotate(angle)` | `p.rotated(angle)`, optionally `around=` another point |
| `p.rounded`, which floors | `Tile.containing(p)`, the tile the point is on |
| `p.snap()` | `Tile.containing(p).center` |

- **Equality is exact.** python-sc2 treats points as equal if every coordinate is within 1e-8, and counts a
  missing coordinate as zero, so `Point3((1, 2, 0)) == Point2((1, 2))`. NachOS points compare as the tuples they
  are.
- **The origin is truthy.** python-sc2 makes `Point2((0, 0))` falsy, so there `if point:` means "not the origin".
- **`direction_vector` returns a unit vector.** python-sc2's returns the sign of each axis, such as `(1, -1)`.
- **2D and 3D points do not mix.** python-sc2 silently pads with zeros or drops the height: `Point2 + Point3`
  loses the height, and `Point3.towards(Point2)` pulls the height toward zero. NachOS raises instead. Convert with
  `.ground` or `.with_height(z)`.
- **Methods that take a point take only a point.** python-sc2's also accept anything with a `.position`. In
  NachOS, pass the position itself.
- **Grids are indexed `[x, y]`.** python-sc2's `PixelMap.data_numpy` is indexed `[y, x]`. `grid[point]` reads the
  tile that any point falls in, where a `PixelMap` needs whole-number coordinates. Reading past the edge raises
  `IndexError`, or returns the grid's `outside` value if it has one, instead of failing an assert.

## The map

| python-sc2 | NachOS |
|---|---|
| `game_info.map_name` | `api.map.name` |
| `game_info.pathing_grid`, `in_pathing_grid(p)` | `api.map.pathing`, `api.map.pathing[p]` |
| `game_info.placement_grid`, `in_placement_grid(p)` | `api.map.placement`, `api.map.placement[p]` |
| `game_info.terrain_height`, `get_terrain_z_height(p)` | `api.map.height`, `api.map.height_at(p)` |
| `game_info.map_center` | `api.map.playable_area.center` |
| `enemy_start_locations` | `api.map.opponent_start_locations` |
| `game_info.map_ramps` | `api.map.ramps` |
| `game_info.vision_blockers` | nothing; see below |
| `ramp.points`, `ramp.upper`, `ramp.lower` | `ramp.tiles`, `ramp.top`, `ramp.bottom` |
| `ramp.top_center`, `ramp.bottom_center`, `ramp.center` | `ramp.top.center`, `ramp.bottom.center`, `ramp.tiles.center` |

- **The grids cover the playable area and no more.** A grid's `values[0, 0]` is the playable area's lower left
  corner, not the map's. Past the playable area, pathing and placement read `False` and height raises.
- **The grids refuse writes.** python-sc2 rebuilds the pathing grid every step, so writing into it lasted one
  step. A grid the map hands out is `readonly`, so a write raises `TypeError`; `copy()` gives one you can change.
- **Height is the ground's height, not a byte, and python-sc2 decodes the byte a little low.** Its
  `terrain_height` holds the byte the game sends. Its `get_terrain_z_height` computes `-16 + 32 * byte / 255`,
  which reads up to 0.03 below where units stand. A byte is an eighth of a unit of height, with 127 at zero.
- **A tile's height is its center's.** The game sends the height at each tile's lower left corner, and python-sc2
  reads that as the tile's. On a ramp, that is up to 0.41 off the ground elsewhere in the tile, and beside a cliff
  it can be the level on the other side. `api.map.height` averages the tile's corners on its own side of any
  cliff, and `api.map.height_at(p)` interpolates between them.
- **A ramp's ends are its highest and lowest tiles, and come out the same size whichever way it faces.**
  python-sc2's `upper` and `lower` are the tiles sharing the highest and lowest terrain byte, which it reads at
  each tile's lower left corner, so a ramp and its mirror image give ends of different sizes -- 13 and 6 tiles for
  two halves of the same map. NachOS reads the height at the tile's center, which is symmetric.
- **A patch of ground is a ramp whole, and no patch is dropped for being small.** python-sc2 asks of each tile
  alone whether the nine terrain bytes around it are equal, calls a tile a ramp point if they are not, and then
  throws away any group of fewer than 8 of them. NachOS groups the ground a unit can walk over but cannot build
  on and reads the whole patch: one whose heights span half a level or more climbs from one level to the next,
  and is a ramp. On the 2026 ladder pool the two find the same ramps, tile for tile.
- **There is no `vision_blockers`, because the map's grids cannot say.** A bridge, a stand of trees and the
  ground under an indestructible doodad are all level, walkable and unbuildable, and nothing in
  `ResponseGameInfo` separates them. python-sc2's `vision_blockers` is that whole mixture: on PylonAIE_v4 it
  calls 33 tiles of each of the map's two bridges a vision blocker. A bot that needs the real ones can find them
  in a game, from what its units can and cannot see.
- **No wall-in placements.** python-sc2's `Ramp` also answers where to put supply depots and a barracks to wall
  off a ramp, and raises on any ramp whose shape it does not expect. NachOS has no equivalent yet.
