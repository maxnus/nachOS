# AGENTS.md

## Project Overview

**NachOS** (package `sc2nachos`) — an event-driven StarCraft II bot API for Python, built directly on
`s2clientprotocol`. It replaces `python-sc2` as the client interface for the bot
[AvocaDOS](https://github.com/maxnus/AvocaDOS), and is intended to be published for other bot authors.

The migration plan lives in the AvocaDOS repo at `docs/plans/nachOS-plan.md`, with its rationale in
`docs/plans/nachOS-initial-prompt.md`.

## Python

Use the AvocaDOS virtual environment: `../AvocaDOS/.venv/Scripts/python.exe`. Never system Python.

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
- Line length 120. `ruff check` and `ruff format --check` must pass.

## Testing

`pytest`. Tests must not require StarCraft II to be installed or running, with the single exception of tests
explicitly marked as integration tests. Everything else runs against recorded protobuf fixtures via the fixture
transport.

| Task | Command |
|---|---|
| Run tests | `pytest` |
| Lint | `ruff check .` |
