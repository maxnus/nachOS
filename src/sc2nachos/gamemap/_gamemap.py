"""The map a game is played on."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

import numpy

from sc2nachos.geometry import Grid, Point, Rectangle, Tile
from sc2nachos.protocol import ProtocolError

if TYPE_CHECKING:
    from numpy import ndarray
    from s2clientprotocol import common_pb2, sc2api_pb2


@dataclass(frozen=True, slots=True, eq=False)
class GameMap:
    """The map a game is played on, as the game describes it when the game starts. None of it changes.

    The grids cover the playable area and nothing beyond it, since no unit can leave it, so a grid's `values` are
    indexed from the playable area's lower left corner. Past it, pathing and placement read `False` and height
    raises. Everything that reads the map shares its grids, so they refuse writes: `copy()` one to change it.
    """

    name: str
    """The name the map is shown under, such as `Pylon AIE`."""

    playable_area: Rectangle
    """The part of the map a unit can be in."""

    pathing: Grid[bool]
    """Where a ground unit can walk as the game starts. Rocks block it, and so do this player's own starting
    townhall, mineral fields and geysers, but no other resources."""

    placement: Grid[bool]
    """Where a structure can go as the game starts. Rocks block it, but no resource or townhall does."""

    height: Grid[float]
    """The height of the ground at each tile's lower left corner, in the units of a unit's `z`, in eighths.

    Units on flat ground stand within 0.15 of it. On a ramp, the rest of a tile can be up to 0.41 higher or lower
    than its corner, and beside a cliff the corner can be on the other level."""

    opponent_start_locations: tuple[Point, ...]
    """Where the opponent may have started: every start location on the map but this player's own."""

    @classmethod
    def from_proto(cls, info: sc2api_pb2.ResponseGameInfo) -> Self:
        """Read the map out of the game's answer to `RequestGameInfo`."""
        start = info.start_raw
        playable_area = Rectangle.from_proto(start.playable_area)
        origin = Tile(start.playable_area.p0.x, start.playable_area.p0.y)
        # A byte is an eighth of a unit of height, and 127 is zero.
        height = (_pixels(start.terrain_height, playable_area).astype(float) - 127) / 8
        return cls(
            name=info.map_name,
            playable_area=playable_area,
            pathing=Grid(_read_only(_pixels(start.pathing_grid, playable_area) != 0), origin=origin, outside=False),
            placement=Grid(_read_only(_pixels(start.placement_grid, playable_area) != 0), origin=origin, outside=False),
            height=Grid(_read_only(height), origin=origin),
            opponent_start_locations=tuple(Point.from_proto(location) for location in start.start_locations),
        )


def _pixels(image: common_pb2.ImageData, area: Rectangle) -> ndarray:
    """The pixels of `image` over the tiles of `area`, indexed `[x, y]`."""
    width, height, bits = image.size.x, image.size.y, image.bits_per_pixel
    if bits not in (1, 8) or len(image.data) != math.ceil(width * height * bits / 8):
        raise ProtocolError(f"a {width} by {height} image of {bits} bits a pixel cannot be {len(image.data)} bytes")
    if not Rectangle(0, 0, width, height).encloses(area):
        raise ProtocolError(f"a {width} by {height} image does not cover {area!r}")
    pixels = numpy.frombuffer(image.data, dtype=numpy.uint8)
    if bits == 1:
        pixels = numpy.unpackbits(pixels, count=width * height)
    # Each row is one y, from the bottom of the map up.
    xs, ys = area.tile_range()
    rows = pixels.reshape(height, width)[ys.start : ys.stop, xs.start : xs.stop]
    return numpy.ascontiguousarray(rows.T)


def _read_only(values: ndarray) -> ndarray:
    """`values`, which from now on refuse writes."""
    values.flags.writeable = False
    return values
