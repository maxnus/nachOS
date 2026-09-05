"""A grid of per-tile values laid over a rectangular patch of the map."""

from __future__ import annotations

from typing import TYPE_CHECKING, final, overload

import numpy

from sc2nachos.geometry._area import Area
from sc2nachos.geometry._point import coordinates
from sc2nachos.geometry._shapes import Rectangle, Tile

if TYPE_CHECKING:
    from collections.abc import Callable

    from numpy import ndarray

    from sc2nachos.geometry._point import PointLike

_ORIGIN = Tile(0, 0)


@final
class Grid[T: float]:
    """A grid of values covering whole tiles, addressed by map position rather than by array index.

    `origin` is the tile at the grid's lower left corner, so a grid can cover the playable area alone. An
    area reaching past the edge is clipped to the tiles the grid holds; a point outside it raises `IndexError`.
    """

    __slots__ = ("_data", "_origin")

    _data: ndarray
    _origin: Tile

    # --- Construction

    def __init__(self, data: ndarray, *, origin: Tile = _ORIGIN) -> None:
        """A grid holding `data`, whose `[0, 0]` entry is the tile at `origin`."""
        if data.ndim != 2:
            raise ValueError(f"a grid is two-dimensional, got {data.ndim} dimensions")
        self._data = data
        self._origin = origin

    @classmethod
    def zeros(cls, width: int, height: int, *, origin: Tile = _ORIGIN, dtype: type[T] = float) -> Grid[T]:
        """A grid of `width` by `height` tiles, filled with zeros."""
        return Grid(numpy.zeros((width, height), dtype=dtype), origin=origin)

    @classmethod
    def like[U: float](cls, other: Grid[U], *, dtype: type[T] = float) -> Grid[T]:
        """A grid of zeros covering the same tiles as `other`."""
        return Grid(numpy.zeros(other._data.shape, dtype=dtype), origin=other._origin)

    # --- The ground it covers

    @property
    def origin(self) -> Tile:
        """The tile at the grid's lower left corner."""
        return self._origin

    @property
    def width(self) -> int:
        """The number of tiles across."""
        return self._data.shape[0]

    @property
    def height(self) -> int:
        """The number of tiles up."""
        return self._data.shape[1]

    @property
    def bounds(self) -> Rectangle:
        """The ground the grid covers."""
        return Rectangle(self._origin[0], self._origin[1], self.width, self.height)

    @property
    def values(self) -> ndarray:
        """A read-only view of the grid, indexed `[x, y]` from `origin`."""
        view = self._data.view()
        view.flags.writeable = False
        return view

    def _aligned(self, other: Grid) -> ndarray:
        """The values of `other`, which must cover the same tiles as this grid."""
        if not isinstance(other, Grid):
            raise TypeError(f"expected a grid, got {type(other).__name__}")
        if other._data.shape != self._data.shape or other._origin != self._origin:
            raise ValueError(f"{other!r} does not cover the same tiles as {self!r}")
        return other._data

    # --- Reading and writing

    # `Tile` is an `Area`, and the only one that addresses a single tile, so it has to be matched first.
    # The overlap is real and cannot be narrowed away: a key typed `Area` that holds a `Tile` is annotated
    # `ndarray` and answers with a scalar.
    @overload
    def __getitem__(self, key: Tile) -> T: ...  # pyright: ignore[reportOverlappingOverload]

    @overload
    def __getitem__(self, key: Rectangle | Area | Grid[bool]) -> ndarray: ...
    @overload
    def __getitem__(self, key: PointLike) -> T: ...

    def __getitem__(self, key: PointLike | Area | Grid[bool]) -> T | ndarray:
        """The value at a point, the values over an area, or the values a mask selects."""
        # Points first, and by tuple: `Tile` is the only `Area` that is one, and it addresses a single
        # tile like any other point. A miss here is cheap, where a miss against an `Area` subclass is not.
        if isinstance(key, tuple):
            return self._data.item(self._address(key))
        if isinstance(key, Rectangle):
            return self._data[self._slices(key)]
        if isinstance(key, Area):
            return self._data[self._scatter(key)]
        if isinstance(key, Grid):
            return self._data[self._mask(key)]
        return self._data.item(self._address(key))

    def __setitem__(self, key: PointLike | Area | Grid[bool], value: T | ndarray) -> None:
        """Writes a value at a point, over an area, or over the tiles a mask selects."""
        if isinstance(key, tuple):
            self._data[self._address(key)] = value
        elif isinstance(key, Rectangle):
            self._data[self._slices(key)] = value
        elif isinstance(key, Area):
            self._data[self._scatter(key)] = value
        elif isinstance(key, Grid):
            self._data[self._mask(key)] = value
        else:
            self._data[self._address(key)] = value

    def fill(self, value: T) -> None:
        """Sets every tile to `value`."""
        self._data[:] = value

    def _address(self, point: PointLike) -> tuple[int, int]:
        """The array index of the tile holding `point`."""
        tile = Tile.containing(point)
        x = tile[0] - self._origin[0]
        y = tile[1] - self._origin[1]
        if not (0 <= x < self._data.shape[0] and 0 <= y < self._data.shape[1]):
            raise IndexError(f"{tile!r} lies outside {self.bounds!r}")
        return x, y

    def _slices(self, rectangle: Rectangle) -> tuple[slice, slice]:
        """The array slices covering the tiles of `rectangle`, clipped to the grid."""
        x_range, y_range = rectangle.tile_range()
        width, height = self._data.shape
        x = min(max(x_range.start - self._origin[0], 0), width)
        y = min(max(y_range.start - self._origin[1], 0), height)
        stop_x = min(max(x_range.stop - self._origin[0], x), width)
        stop_y = min(max(y_range.stop - self._origin[1], y), height)
        return slice(x, stop_x), slice(y, stop_y)

    def _scatter(self, area: Area) -> tuple[ndarray, ndarray]:
        """The array indices of the area's tiles that the grid covers, as a pair of index arrays."""
        tiles = area.tiles()
        if not tiles:
            return numpy.empty(0, dtype=int), numpy.empty(0, dtype=int)
        addresses = numpy.array([(tile[0], tile[1]) for tile in tiles]) - numpy.array(self._origin)
        covered = ((addresses >= 0) & (addresses < self._data.shape)).all(axis=1)
        addresses = addresses[covered]
        return addresses[:, 0], addresses[:, 1]

    def _mask(self, mask: Grid[bool]) -> ndarray:
        """The values of a mask covering the same tiles, which numpy would read as row indices if not boolean."""
        values = self._aligned(mask)
        if values.dtype != bool:
            raise TypeError(f"a grid used as a mask must hold booleans, got {values.dtype}")
        return values

    # --- Derived grids

    def copy(self) -> Grid[T]:
        """An independent grid holding the same values."""
        return Grid(self._data.copy(), origin=self._origin)

    def where(self, condition: Grid[bool], other: T | Grid[T]) -> Grid[T]:
        """This grid where `condition` holds, and `other` everywhere else."""
        values = self._aligned(other) if isinstance(other, Grid) else other
        return Grid(numpy.where(self._aligned(condition), self._data, values), origin=self._origin)

    def minimum(self, other: Grid[T]) -> Grid[T]:
        """The smaller of the two values on each tile."""
        return self._combine(other, numpy.minimum)

    def maximum(self, other: Grid[T]) -> Grid[T]:
        """The larger of the two values on each tile."""
        return self._combine(other, numpy.maximum)

    def distance_from(self, point: PointLike) -> Grid[float]:
        """The distance from each tile's center to `point`."""
        position = coordinates(point)
        xs = numpy.arange(self.width) + self._origin[0] + 0.5 - position[0]
        ys = numpy.arange(self.height) + self._origin[1] + 0.5 - position[1]
        return Grid(numpy.hypot(xs[:, None], ys[None, :]), origin=self._origin)

    # --- Summaries

    def min(self) -> T:
        """The smallest value."""
        return self._data.min().item()

    def max(self) -> T:
        """The largest value."""
        return self._data.max().item()

    @overload
    def sum(self: Grid[bool]) -> int: ...
    @overload
    def sum(self) -> T: ...

    def sum(self) -> T | int:
        """The total over every tile, which for a boolean grid is the number of true ones."""
        return self._data.sum().item()

    def argmin(self) -> Tile:
        """The tile holding the smallest value, the lowest address of them if several tie."""
        return self._tile_at(int(numpy.argmin(self._data)))

    def argmax(self) -> Tile:
        """The tile holding the largest value, the lowest address of them if several tie."""
        return self._tile_at(int(numpy.argmax(self._data)))

    def _tile_at(self, flat_index: int) -> Tile:
        """The tile addressed by a flat index into the grid."""
        x, y = numpy.unravel_index(flat_index, self._data.shape)
        return Tile(self._origin[0] + int(x), self._origin[1] + int(y))

    # --- Operators

    def _combine(self, other: object, op: Callable[..., ndarray], *, flip: bool = False) -> Grid:
        """`op` applied against a scalar, or tilewise against a grid covering the same tiles."""
        if isinstance(other, Grid):
            values = self._aligned(other)
        elif isinstance(other, bool | int | float | numpy.number | numpy.bool_):
            # numpy scalars subclass neither `int` nor `bool`, and only `float64` subclasses `float`.
            # Without them here the operand round-trips through numpy and back, at twice the cost.
            values = other
        else:
            return NotImplemented
        left, right = (values, self._data) if flip else (self._data, values)
        return Grid(op(left, right), origin=self._origin)

    def __add__(self, other: Grid[T] | T) -> Grid[T]:
        return self._combine(other, numpy.add)

    def __radd__(self, other: T) -> Grid[T]:
        return self._combine(other, numpy.add, flip=True)

    def __sub__(self, other: Grid[T] | T) -> Grid[T]:
        return self._combine(other, numpy.subtract)

    def __rsub__(self, other: T) -> Grid[T]:
        return self._combine(other, numpy.subtract, flip=True)

    def __mul__(self, other: Grid[T] | T) -> Grid[T]:
        return self._combine(other, numpy.multiply)

    def __rmul__(self, other: T) -> Grid[T]:
        return self._combine(other, numpy.multiply, flip=True)

    def __truediv__(self, other: Grid[T] | T) -> Grid[float]:
        return self._combine(other, numpy.divide)

    def __neg__(self) -> Grid[T]:
        return Grid(-self._data, origin=self._origin)

    def __abs__(self) -> Grid[T]:
        return Grid(abs(self._data), origin=self._origin)

    def __invert__(self: Grid[bool]) -> Grid[bool]:
        return Grid(numpy.logical_not(self._data), origin=self._origin)

    def __and__(self: Grid[bool], other: Grid[bool] | bool) -> Grid[bool]:
        return self._combine(other, numpy.logical_and)

    def __rand__(self: Grid[bool], other: bool) -> Grid[bool]:
        return self._combine(other, numpy.logical_and, flip=True)

    def __or__(self: Grid[bool], other: Grid[bool] | bool) -> Grid[bool]:
        return self._combine(other, numpy.logical_or)

    def __ror__(self: Grid[bool], other: bool) -> Grid[bool]:
        return self._combine(other, numpy.logical_or, flip=True)

    # --- Comparisons

    def equals(self, other: object) -> bool:
        """Whether `other` is a grid covering the same tiles and holding the same values."""
        return (
            isinstance(other, Grid)
            and self._origin == other._origin
            and self._data.shape == other._data.shape
            and numpy.array_equal(self._data, other._data)
        )

    def __eq__(self, other: Grid[T] | T) -> Grid[bool]:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Whether each tile equals `other`; `equals` compares grids as wholes."""
        return self._combine(other, numpy.equal)

    def __ne__(self, other: Grid[T] | T) -> Grid[bool]:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self._combine(other, numpy.not_equal)

    def __lt__(self, other: Grid[T] | T) -> Grid[bool]:
        return self._combine(other, numpy.less)

    def __le__(self, other: Grid[T] | T) -> Grid[bool]:
        return self._combine(other, numpy.less_equal)

    def __gt__(self, other: Grid[T] | T) -> Grid[bool]:
        return self._combine(other, numpy.greater)

    def __ge__(self, other: Grid[T] | T) -> Grid[bool]:
        return self._combine(other, numpy.greater_equal)

    def __bool__(self) -> bool:
        """Refused: `grid == other` answers per tile, so `if grid == other` would always be true."""
        raise TypeError("a grid has no truth value; use .any() or .all()")

    def any(self) -> bool:
        """Whether any tile is true."""
        return bool(self._data.any())

    def all(self) -> bool:
        """Whether every tile is true."""
        return bool(self._data.all())

    def __repr__(self) -> str:
        return f"Grid({self.width}x{self.height} of {self._data.dtype} at {self._origin!r})"
