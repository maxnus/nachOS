"""A grid of per-tile values laid over a rectangular patch of the map."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self, cast, final, overload

import numpy
import scipy.ndimage

from sc2nachos.geometry._area import Area
from sc2nachos.geometry._point import coordinates
from sc2nachos.geometry._shapes import Rectangle, Tile

if TYPE_CHECKING:
    from collections.abc import Callable

    from numpy import ndarray

    from sc2nachos.geometry._point import PointLike

_ORIGIN = Tile(0, 0)


# Scalars a grid combines with. numpy scalars subclass neither `int` nor `bool`, and only `float64`
# subclasses `float`; without them the operand round-trips through numpy and back, at twice the cost.
# Held as a constant because an inline `a | b` union is rebuilt on every call, at seven times the cost.
SCALAR_TYPES = (int, float, numpy.number, numpy.bool_)


class Grid[T: float]:
    """A grid of values covering whole tiles, read by map position rather than by array index.

    `origin` is the tile at the grid's lower left corner, so a grid can cover the playable area alone. An
    area reaching past the edge is clipped to the tiles the grid holds; a point outside it raises `IndexError`.

    A `Grid` is only read, which is how the library hands out what it shares, such as the map's. `MutableGrid` is
    the one that can be written to, and every grid derived from either -- a copy, a crop, the result of
    arithmetic -- is one.
    """

    __slots__ = ("_data", "_origin", "_outside")

    _data: ndarray
    _origin: Tile
    _outside: T | None

    # --- Construction

    def __init__(self, data: ndarray, *, origin: Tile = _ORIGIN, outside: T | None = None) -> None:
        """A grid holding `data`, whose `[0, 0]` entry is the tile at `origin`.

        `outside` is what reading a point beyond the grid answers; without it such a read raises. Writing
        beyond the grid always raises.
        """
        if data.ndim != 2:
            raise ValueError(f"a grid is two-dimensional, got {data.ndim} dimensions")
        self._data = data
        self._origin = origin
        self._outside = outside

    @classmethod
    def zeros(
        cls, width: int, height: int, *, origin: Tile = _ORIGIN, dtype: type[T] = float, outside: T | None = None
    ) -> MutableGrid[T]:
        """A grid of `width` by `height` tiles, filled with zeros."""
        return MutableGrid(numpy.zeros((width, height), dtype=dtype), origin=origin, outside=outside)

    @classmethod
    def like[U: float](cls, other: Grid[U], *, dtype: type[T] = float, outside: T | None = None) -> MutableGrid[T]:
        """A grid of zeros covering the same tiles as `other`."""
        return MutableGrid(numpy.zeros(other._data.shape, dtype=dtype), origin=other._origin, outside=outside)

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

    def index_of(self, point: PointLike) -> tuple[int, int]:
        """The index into `values` of the tile holding `point`, for handing the array to other code.

        Raises `IndexError` for a point the grid does not cover, `outside` notwithstanding.
        """
        tile = Tile.containing(point)
        x = tile[0] - self._origin[0]
        y = tile[1] - self._origin[1]
        if not (0 <= x < self._data.shape[0] and 0 <= y < self._data.shape[1]):
            raise IndexError(f"{tile!r} lies outside {self.bounds!r}")
        return x, y

    def tile_at(self, index: tuple[int, int]) -> Tile:
        """The tile an index into `values` addresses. The inverse of `index_of`."""
        x, y = index
        if not (0 <= x < self._data.shape[0] and 0 <= y < self._data.shape[1]):
            raise IndexError(f"{index} lies outside a {self.width} by {self.height} grid")
        return Tile(self._origin[0] + x, self._origin[1] + y)

    @property
    def outside(self) -> T | None:
        """What a read beyond the grid answers, or None if one raises."""
        return self._outside

    def with_outside(self, value: T | None) -> Self:
        """The same grid, reading `value` beyond its edge. Shares the data rather than copying it."""
        return type(self)(self._data, origin=self._origin, outside=value)

    def _value_at(self, point: PointLike) -> T:
        """The value at `point`, or `outside` for a point the grid does not cover."""
        tile = Tile.containing(point)
        x = tile[0] - self._origin[0]
        y = tile[1] - self._origin[1]
        if 0 <= x < self._data.shape[0] and 0 <= y < self._data.shape[1]:
            return self._data.item(x, y)
        if self._outside is None:
            raise IndexError(f"{tile!r} lies outside {self.bounds!r}")
        return self._outside

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
            return self._value_at(key)
        if isinstance(key, Rectangle):
            return self._data[self._slices(key)]
        if isinstance(key, Area):
            return self._data[self._scatter(key)]
        if isinstance(key, Grid):
            return self._data[self._mask(key)]
        return self._value_at(key)

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

    def copy(self) -> MutableGrid[T]:
        """An independent grid holding the same values."""
        return MutableGrid(self._data.copy(), origin=self._origin, outside=self._outside)

    def where(self, condition: Grid[bool], other: T | Grid[T]) -> MutableGrid[T]:
        """This grid where `condition` holds, and `other` everywhere else."""
        values = self._aligned(other) if isinstance(other, Grid) else other
        # Chosen first: `_aligned` is what rejects a condition that is not a grid, and the off-grid
        # value reads `condition._outside`, which only means anything once that check has passed.
        chosen = numpy.where(self._aligned(condition), self._data, values)
        return MutableGrid(chosen, origin=self._origin, outside=self._where_outside(condition, other))

    def _where_outside(self, condition: Grid[bool], other: T | Grid[T]) -> T | None:
        """The off-grid value of the operand the condition picks there, or None if it has none."""
        if condition._outside is None:
            return None
        if condition._outside:
            return self._outside
        return other._outside if isinstance(other, Grid) else other

    def minimum(self, other: Grid[T]) -> MutableGrid[T]:
        """The smaller of the two values on each tile."""
        return self._combine(other, numpy.minimum)

    def maximum(self, other: Grid[T]) -> MutableGrid[T]:
        """The larger of the two values on each tile."""
        return self._combine(other, numpy.maximum)

    def cropped(self, rectangle: Rectangle) -> MutableGrid[T]:
        """An independent grid over the tiles `rectangle` covers, clipped to the ones this grid holds."""
        x, y = self._slices(rectangle)
        origin = Tile(self._origin[0] + x.start, self._origin[1] + y.start)
        return MutableGrid(self._data[x, y].copy(), origin=origin, outside=self._outside)

    def distance_from(self, point: PointLike, *, outside: float | None = None) -> MutableGrid[float]:
        """The distance from each tile's center to `point`."""
        position = coordinates(point)
        xs = numpy.arange(self.width) + self._origin[0] + 0.5 - position[0]
        ys = numpy.arange(self.height) + self._origin[1] + 0.5 - position[1]
        return MutableGrid(numpy.hypot(xs[:, None], ys[None, :]), origin=self._origin, outside=outside)

    def distance_transform(self: Grid[bool], *, outside: float | None = None) -> MutableGrid[float]:
        """For each true tile, the distance to the nearest false one; zero on a false tile."""
        distances = scipy.ndimage.distance_transform_edt(self._data, return_indices=False)
        return MutableGrid(numpy.asarray(distances), origin=self._origin, outside=outside)

    def smoothed(
        self, sigma: float, *, within: Grid[bool] | None = None, outside: float | None = None
    ) -> MutableGrid[float]:
        """A Gaussian blur of the values, `sigma` measured in tiles.

        Given `within`, only those tiles contribute and the result is renormalized, so values near the edge
        of the region are not dragged down by the tiles outside it. A tile no contributor reaches keeps its
        own value.
        """
        values = self._data.astype(float)
        if within is None:
            return MutableGrid(scipy.ndimage.gaussian_filter(values, sigma=sigma), origin=self._origin, outside=outside)
        weights = self._mask(within).astype(float)
        numerator = scipy.ndimage.gaussian_filter(values * weights, sigma=sigma)
        denominator = scipy.ndimage.gaussian_filter(weights, sigma=sigma)
        blurred = values.copy()
        numpy.divide(numerator, denominator, out=blurred, where=denominator > 0)
        return MutableGrid(blurred, origin=self._origin, outside=outside)

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
        return self.tile_at((int(x), int(y)))

    # --- Operators

    def _combine(self, other: object, op: Callable[..., ndarray], *, flip: bool = False) -> MutableGrid:
        """`op` applied against a scalar, or tilewise against a grid covering the same tiles."""
        if isinstance(other, Grid):
            values = self._aligned(other)
        elif isinstance(other, SCALAR_TYPES):
            values = other
        else:
            return NotImplemented
        left, right = (values, self._data) if flip else (self._data, values)
        return MutableGrid(op(left, right), origin=self._origin, outside=self._combine_outside(other, op, flip=flip))

    def _combine_outside(self, other: object, op: Callable[..., ndarray], *, flip: bool) -> T | None:
        """`op` applied to the operands' own off-grid values, or None if either has none."""
        if self._outside is None:
            return None
        if isinstance(other, Grid):
            if other._outside is None:
                return None
            value = other._outside
        else:
            value = other
        left, right = (value, self._outside) if flip else (self._outside, value)
        return op(left, right).item()

    def __add__(self, other: Grid[T] | T) -> MutableGrid[T]:
        return self._combine(other, numpy.add)

    def __radd__(self, other: T) -> MutableGrid[T]:
        return self._combine(other, numpy.add, flip=True)

    def __sub__(self, other: Grid[T] | T) -> MutableGrid[T]:
        return self._combine(other, numpy.subtract)

    def __rsub__(self, other: T) -> MutableGrid[T]:
        return self._combine(other, numpy.subtract, flip=True)

    def __mul__(self, other: Grid[T] | T) -> MutableGrid[T]:
        return self._combine(other, numpy.multiply)

    def __rmul__(self, other: T) -> MutableGrid[T]:
        return self._combine(other, numpy.multiply, flip=True)

    def __truediv__(self, other: Grid[T] | T) -> MutableGrid[float]:
        return self._combine(other, numpy.divide)

    def __neg__(self) -> MutableGrid[T]:
        # Negating a `T` bound to float widens to float; at runtime the type is unchanged.
        outside = None if self._outside is None else cast("T", -self._outside)
        return MutableGrid(-self._data, origin=self._origin, outside=outside)

    def __abs__(self) -> MutableGrid[T]:
        outside = None if self._outside is None else cast("T", abs(self._outside))
        return MutableGrid(abs(self._data), origin=self._origin, outside=outside)

    def __invert__(self: Grid[bool]) -> MutableGrid[bool]:
        return MutableGrid(
            numpy.logical_not(self._data),
            origin=self._origin,
            outside=None if self._outside is None else not self._outside,
        )

    def __and__(self: Grid[bool], other: Grid[bool] | bool) -> MutableGrid[bool]:
        return self._combine(other, numpy.logical_and)

    def __rand__(self: Grid[bool], other: bool) -> MutableGrid[bool]:
        return self._combine(other, numpy.logical_and, flip=True)

    def __or__(self: Grid[bool], other: Grid[bool] | bool) -> MutableGrid[bool]:
        return self._combine(other, numpy.logical_or)

    def __ror__(self: Grid[bool], other: bool) -> MutableGrid[bool]:
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

    def __eq__(self, other: Grid[T] | T) -> MutableGrid[bool]:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Whether each tile equals `other`; `equals` compares grids as wholes."""
        return self._combine(other, numpy.equal)

    def __ne__(self, other: Grid[T] | T) -> MutableGrid[bool]:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self._combine(other, numpy.not_equal)

    def __lt__(self, other: Grid[T] | T) -> MutableGrid[bool]:
        return self._combine(other, numpy.less)

    def __le__(self, other: Grid[T] | T) -> MutableGrid[bool]:
        return self._combine(other, numpy.less_equal)

    def __gt__(self, other: Grid[T] | T) -> MutableGrid[bool]:
        return self._combine(other, numpy.greater)

    def __ge__(self, other: Grid[T] | T) -> MutableGrid[bool]:
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
        return f"{type(self).__name__}({self.width}x{self.height} of {self._data.dtype} at {self._origin!r})"


@final
class MutableGrid[T: float](Grid[T]):
    """A grid that can be written to, which is what a bot builds for itself.

    Every grid the library hands out is a plain `Grid`, since what it holds is shared with everything else that
    reads it. `copy()` gives a grid of your own.
    """

    __slots__ = ()

    def __init__(self, data: ndarray, *, origin: Tile = _ORIGIN, outside: T | None = None) -> None:
        """A grid holding `data`, which must accept writes. Otherwise as `Grid`."""
        super().__init__(data, origin=origin, outside=outside)
        if not data.flags.writeable:
            raise ValueError("values that refuse writes make a Grid, not a MutableGrid")

    def __setitem__(self, key: PointLike | Area | Grid[bool], value: T | ndarray) -> None:
        """Writes a value at a point, over an area, or over the tiles a mask selects."""
        if isinstance(key, tuple):
            self._data[self.index_of(key)] = value
        elif isinstance(key, Rectangle):
            self._data[self._slices(key)] = value
        elif isinstance(key, Area):
            self._data[self._scatter(key)] = value
        elif isinstance(key, Grid):
            self._data[self._mask(key)] = value
        else:
            self._data[self.index_of(key)] = value

    def fill(self, value: T) -> None:
        """Sets every tile to `value`."""
        self._data[:] = value
