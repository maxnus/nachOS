# AGENTS.md

## Project Overview

**NachOS** (package `sc2nachos`) — an event-driven StarCraft II bot API for Python, built directly on
`s2clientprotocol`. It replaces `python-sc2` as the client interface for the bot
[AvocaDOS](https://github.com/maxnus/AvocaDOS), and is intended to be published for other bot authors.

The migration plan lives in the AvocaDOS repo at `docs/plans/nachOS-plan.md`, with its rationale in
`docs/plans/nachOS-initial-prompt.md`.

## Python

Use the AvocaDOS virtual environment: `../AvocaDOS/.venv/Scripts/python.exe`. Never system Python.

**`Path.read_text` and `Path.write_text` default to the locale encoding here, which is cp1252.** Pass
`encoding="utf-8"` to both, or an em dash written back to a source file silently becomes invalid UTF-8
and ruff refuses to read it.

## Core design rules

These are the non-negotiables. They exist because this library is published for others, not just used by AvocaDOS.

- **No module-level mutable state, anywhere.** NachOS never creates or exposes a singleton. It exposes an
  instance-based `Api`; the consuming bot decides whether to make one global. Two `Api` instances must be
  able to coexist in one process.
- **The API is instantiated, never subclassed.** Do not document, encourage or design for bot authors inheriting
  from `Api`, and never add a mixin or extension hook for them to hang helpers on. Their helpers belong in
  their own modules as ordinary functions. A felt need to subclass is a signal that NachOS is missing an API —
  treat it as a bug report against this library, not as a pattern to support. (AvocaDOS subclasses during the
  migration only because of its legacy `ApiExtensions` mixin. That is a wart being dissolved, not the intended
  shape.)
- **`Api.__init__` must be cheap and must not require a live connection.** Consumers construct it at import
  time so that `@api.event.on(...)` decorators can run as their modules load. Connecting happens in
  `run_local` / `run_ladder`, which take an already-built instance.
- **No AvocaDOS-shaped quirks.** Nothing may exist in NachOS solely to make something work in AvocaDOS. If in
  doubt, the awkwardness stays in AvocaDOS. Better still, fix it so neither side needs it.
- **NachOS owes python-sc2 nothing.** This is a new package, not a fork and not a compatible replacement — no API
  compatibility, no naming, no behavior. python-sc2 is a reference for *what the game requires*, never for *how to
  express it*. When porting, the question is never "what does python-sc2 do here" but "what should this do", and
  where it is wrong or awkward NachOS must be right, even if that means the consuming bot has to change. The
  failure mode is silent: matching the reference feels like diligence, which is how its bugs and its internal
  development names get copied in. Already caught: `Point2.rounded` there is `math.floor`; `Rect` subclasses
  `Point2` and so has a `distance_to`; `PUNISHERGRENADES` is what a player calls concussive shells.
- **Scope:** anything useful to any bot maker, if it is (or can be made) acceptable quality — protocol, state, data
  model, units, orders, events, geometry, pathfinding, map analysis, generic utilities. Not: strategy, build
  orders, combat micro, roles, economy management.
- **The protocol transport is injectable.** Everything above it must be testable with no game client running,
  against recorded observation fixtures.
- **Performance matters.** This code sits in the bot's hot loop. Do not add abstraction layers that cost step time.

## Conventions

Carried over from AvocaDOS, so the two codebases read alike:

- **Imports**: separate stdlib, third-party and internal imports with blank lines.
- **Keyword-only args**: use `*` in signatures liberally.
- **One class per file** (except small data classes). File named after the class, lowercase.
- **Type hints** on all parameters and return types.
- **Docstrings** on all public functions and classes, but without parameter/return sections.
- **`__all__`** only where it earns its place — package `__init__.py` files that curate a public surface.
- **`TYPE_CHECKING` guard** for imports that would otherwise be circular.
- **loguru**, not stdlib `logging`.
- **US spelling** everywhere in code, comments, docstrings and docs — `behavior`, `initialize`, `summarize`,
  `color`, `center`. The exception is generated identifiers: `ids/raw/` mirrors Blizzard's own names verbatim
  (`BuildinProgressNonCancellable`), and those are data, never to be "corrected".
- Line length 120. `ruff check` and `ruff format --check` must pass.
- **One game loop is a step.** Above the protocol layer time is counted in steps -- `Api.step`,
  `steps_per_turn`, `steps_to_seconds` -- and the bot's own cycle is a turn, which nothing counts. The protocol
  layer keeps Blizzard's `game_loop`, because the messages it hands back carry that field, and `Api.play` is
  the one place the two meet. Never write "frame" for either.

## Review checklist

Each of these came from a real bug found in review, mostly in code that looked correct and passed its tests.

- **Annotate as tightly as the value allows.** `Self` for type-preserving operations, exact tuple arity
  (`tuple[float, float]`, not `tuple[float, ...]`), fixed-length returns where the count is in the name, real
  protobuf types under `TYPE_CHECKING`. `pyright` runs in CI and has caught what `ruff` and the tests did not.
- **No false IS-A.** Types of different shape must not inherit from each other — `Point3` is not a `Point2`, a
  `Rect` is not a point. Share behavior through a non-public base instead. A subtype claim that is not
  substitutable makes every downstream bug typecheck cleanly.
- **Never silently discard data.** An operation that cannot preserve a coordinate, a field, or a dimension must
  raise, with a message naming both operands and the explicit conversion. Padding and truncation hide bugs.
- **Numeric checks must accept numpy scalars.** Only `numpy.float64` subclasses `float`; `float32` and the
  integer types subclass neither. Use `numbers.Real`, ordered *after* the concrete types — the ABC check is
  roughly 3x slower, so the common path must not reach it.
- **A `tuple` subclass must define `__radd__` and `__rmul__`.** Otherwise `(1, 2) + point` inherits concatenation
  and `2 * point` inherits repetition, both returning a wrong answer with no error.
- **`__contains__` has no reflected form.** Return a bool, never `NotImplemented` — it is truthy, so
  `"banana" in rect` answers `True`.
- **Every exported name is a promise.** No public API without a caller or a test that shows why it exists, and no
  second spelling of an operation that already exists.
- **Measure before claiming.** Benchmark competing shapes rather than reasoning about them; grep for real call
  sites before calling something hot. Several "obvious" optimizations in review turned out to target the wrong
  cost entirely.
- **A name must not claim behavior the code lacks.** The most common defect found in review, and the one tests
  never catch. `rescale` was a plain `lerp`; `exp_decay` was a linear blend that mixed seconds with game steps;
  `Region` was a set of discrete tiles; `Area.size` meant area for two shapes and a point count for the third;
  `Point.floored` returned a tile corner wearing a position's type. Read the body, then ask what the name
  promised.
- **Test invariants across implementations, not one at a time.** `closest_point_to` returned a tile center from
  `TileSet` and a boundary point from `Tile` and `Rectangle`, so one square of ground answered three ways — and
  `TileSet`'s distance did not match the point it returned. Every per-class test passed. Parametrize one probe
  over every implementation of the interface.
- **A base class without `__slots__` gives every subclass a `__dict__`.** `Area` omitted it, so `Tile`'s
  `__slots__ = ()` and `Rectangle`'s `slots=True` were both inert: wasted bytes on thousands of instances, and
  arbitrary attributes assignable on a frozen value. `functools.cached_property` needs that dict, so a class
  wanting one opts back in by declaring no slots — it cannot have both, and it cannot override an abstract
  `property`.
- **Set iteration order depends on how the set was built.** Two `frozenset`s holding equal elements iterate
  differently when one was reached by `difference`. That reached `random_point`, making a seeded game
  unreproducible. Anything that picks or orders elements must sort first.
- **An unset proto2 enum field reads as its first declared value, not zero.** `Response.status` unset is
  `launched`; `ResponseJoinGame.error` and `ResponseCreateGame.error` unset are `MissingParticipation` and
  `MissingMap`, both truthy, so reading either blind refuses every successful request. Gate optional enum reads
  with `HasField`, spelled out at the call site -- the stubs type it with a `Literal` of field names, so a helper
  taking `field: str` defeats the check.
- **`isinstance` against an ABC subclass costs ~6x a plain class when it misses** — ~125 ns against ~20. A
  dispatch chain over `Area` implementations pays that per branch it rejects. Prefer a virtual method; a type
  switch is both slower and closed to new shapes.

## Checking what the game contains

Curation decides which ids are real, so "does this still exist?" comes up constantly. Answer it from these:

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

**`data/stableid.json` is map-dependent.** SC2 rewrites it on every launch from the loaded map's mod
dependencies, so the map decides the file: BerlingradAIE (2022) yields 4652 abilities against MagannathaAIE's
4134, with 518 ids present only in the old map and a couple of dozen shared names shifted by +312 or +316.
Refresh it from a current ladder map, never from whatever happened to be loaded last.

## Talking to the game

- **The authoritative protocol documentation is the comments in `sc2api.proto`**, and the `s2clientprotocol`
  package on PyPI ships only generated code, which carries none of them. Read the source:
  `https://raw.githubusercontent.com/Blizzard/s2client-proto/master/s2clientprotocol/sc2api.proto`
- **A participant's race and name come from the join, not from the create.** `PlayerSetup.race` is used only for
  a computer player, as its proto comment says: a game created with a bare `Participant` and joined as Terran
  reports `race_actual` Terran, and `race_actual` is populated only for your own player.
- **`ResponseGameInfo` never changes during a game.** Byte-identical at game loops 0, 256, 1024 and 3008 on
  the same match. python-sc2 re-asks for it on every single step, which is 77 KB a step for a message that holds
  the map, its terrain and who is playing. Ask once, at the start.
- **A recorded game is enormous raw and tiny compressed.** A full bare game is 771 exchanges and 63 MB, of
  which the observations are all but 0.4 MB -- about 80 KB each, changing very little between steps. xz at its
  default preset takes that to 0.2 MB, some 200x; gzip manages 30x, because a 32 KB window cannot span even one
  observation. xz is also the fastest to read back here, since most of the output is long match copies.
- **A game against the computer says it is over on the observation that carries the results.** The step before
  it still answers `in_game`. Once over, `step` and `action` are refused with `Game has already ended`, while
  `observation` goes on answering with the results. Nothing in the protocol stops a step being the first to say
  `ended`, so a runner has to follow any end with an observation before it can say who won.
- **Leaving is refused whenever there is no game to leave**: before one is created, after a `create_game` the
  game refused, between create and join, and after having already left. Each answers
  `A game has not been started yet`, which a cleanup path has to forgive or it will hide the error that got it
  there. Leaving from `in_game` is accepted and returns the client to `launched`.
- **A game that is killed makes websocket-client raise a bare `ConnectionResetError`** (WinError 10054), not
  one of its own `WebSocketException`s, so a transport has to translate the OS error too.
- **Map packs install alongside the maps they replace**, so one map name really does match several files --
  `MagannathaAIE_v2.SC2Map` sits in both `Maps/` and `Maps/AIE/`. A lookup by name must resolve that rather than
  refuse it.

## Testing

`pytest`. Tests must not require StarCraft II to be installed or running, with the single exception of tests
marked `@pytest.mark.integration`, which a plain `pytest` run deselects. Everything else runs against recorded
protobuf fixtures via the fixture transport.

| Task | Command |
|---|---|
| Run tests | `pytest` |
| Run the tests that start a game | `pytest -m integration` |
| Lint | `ruff check .` and `ruff format --check .` |
| Type check | `pyright` (locally: `--pythonpath ../AvocaDOS/.venv/Scripts/python.exe`) |
| Regenerate raw ids | `python tools/generate_ids.py` after refreshing `data/stableid.json` |
