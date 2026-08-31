"""Points in the game's coordinate space."""

from __future__ import annotations

import math
import numbers
import operator
from collections.abc import Iterable
from typing import TYPE_CHECKING, Protocol, Self, Union

if TYPE_CHECKING:
    from collections.abc import Callable

    from s2clientprotocol import common_pb2


class HasPosition(Protocol):
    """Anything that knows where it is — a unit, a structure, an expansion."""

    @property
    def position(self) -> Point2: ...


# A point, a plain coordinate tuple, or anything with a `.position`.
PointLike = Union["Point2", "Point3", tuple[float, ...], HasPosition]


# Scalars accepted by point arithmetic. `numbers.Real` catches numpy scalars, which subclass neither `int` nor
# `float` — except `float64`. It goes last because the ABC check is far slower than the concrete ones.
SCALAR_TYPES = (int, float, numbers.Real)


def coordinates(value: PointLike) -> tuple[float, ...]:
    """The coordinate tuple of a point, or of anything that has a `.position`."""
    if isinstance(value, tuple):
        return value
    position = getattr(value, "position", None)
    if position is None:
        raise TypeError(f"expected a point or something with a .position, got {type(value).__name__}")
    return position


class _CoordinateTuple(tuple[float, ...]):
    """Coordinate math shared by `Point2` and `Point3`.

    Operations preserve the operand's type, and reject operands of a different dimensionality. The arithmetic
    operators are vector operations, not tuple ones: `point * 3` scales rather than repeating the sequence.
    """

    __slots__ = ()

    @property
    def x(self) -> float:
        """The horizontal coordinate."""
        return self[0]

    @property
    def y(self) -> float:
        """The vertical coordinate."""
        return self[1]

    @property
    def position(self) -> Self:
        """The point itself, so points and units can be used interchangeably."""
        return self

    @property
    def rounded(self) -> Self:
        """The nearest integer coordinates."""
        return type(self)(round(value) for value in self)

    @property
    def floored(self) -> Self:
        """The integer coordinates of the grid cell containing this point."""
        return type(self)(math.floor(value) for value in self)

    @property
    def cell_center(self) -> Self:
        """The center of the grid cell containing this point, where units sit."""
        return type(self)(math.floor(value) + 0.5 for value in self)

    @property
    def length(self) -> float:
        """Distance from the origin, on the ground plane."""
        return math.hypot(self[0], self[1])

    @property
    def normalized(self) -> Self:
        """The point scaled to unit length on the ground plane."""
        length = self.length
        if not length:
            raise ZeroDivisionError("cannot normalize a zero-length point")
        return self / length

    def distance_to(self, other: PointLike) -> float:
        """Distance to another point, on the ground plane.

        StarCraft ranges ignore height, so a unit on a cliff is in range of one below it.
        """
        position = coordinates(other)
        return math.hypot(self[0] - position[0], self[1] - position[1])

    def distance_to_squared(self, other: PointLike) -> float:
        """Squared ground-plane distance, for when only the ordering matters."""
        position = coordinates(other)
        return (self[0] - position[0]) ** 2 + (self[1] - position[1]) ** 2

    def is_closer_than(self, distance: float, other: PointLike) -> bool:
        """Whether another point lies strictly within `distance`."""
        return self.distance_to_squared(other) < distance**2

    def towards(self, other: PointLike, distance: float = 1, *, limit: bool = False) -> Self:
        """The point moved `distance` toward another of the same dimensionality.

        `distance` is measured on the ground plane. With `limit`, never overshoots. A negative distance moves
        away.
        """
        position = coordinates(other)
        # Checked up front rather than left to the zip below, which the zero-separation early return would skip.
        if len(position) != len(self):
            raise self._dimension_error(position)
        separation = self.distance_to(position)
        if not separation:
            return self
        if limit:
            distance = min(distance, separation)
        fraction = distance / separation
        return type(self)(value + fraction * (target - value) for value, target in zip(self, position, strict=True))

    def direction_vector(self, other: PointLike) -> Point2:
        """The unit vector on the ground plane pointing from this point to another."""
        position = coordinates(other)
        return Point2((position[0] - self[0], position[1] - self[1])).normalized

    def angle_to(self, other: PointLike) -> float:
        """The angle in radians to another point, from the positive x-axis."""
        position = coordinates(other)
        return math.atan2(position[1] - self[1], position[0] - self[0])

    def rotate(self, angle: float, *, around: PointLike | None = None) -> Self:
        """The point rotated by `angle` radians about the vertical axis through `around`, or the origin.

        Only the pivot's x and y are read, so it may be of any dimensionality. Height is carried through.
        """
        pivot = (0.0, 0.0) if around is None else coordinates(around)
        sin, cos = math.sin(angle), math.cos(angle)
        dx, dy = self[0] - pivot[0], self[1] - pivot[1]
        rotated = (pivot[0] + cos * dx - sin * dy, pivot[1] + sin * dx + cos * dy)
        return type(self)(rotated + tuple(self[2:]))

    def closest[T: PointLike](self, points: Iterable[T]) -> T:
        """The nearest of the given points, returned as it was passed in."""
        candidates = list(points)
        if not candidates:
            raise ValueError("no points to choose from")
        return min(candidates, key=self.distance_to_squared)

    def furthest[T: PointLike](self, points: Iterable[T]) -> T:
        """The most distant of the given points, returned as it was passed in."""
        candidates = list(points)
        if not candidates:
            raise ValueError("no points to choose from")
        return max(candidates, key=self.distance_to_squared)

    @property
    def neighbors4(self) -> tuple[Self, Self, Self, Self]:
        """The four orthogonally adjacent points."""
        return (self + (0, 1), self + (0, -1), self + (1, 0), self + (-1, 0))

    @property
    def neighbors8(self) -> tuple[Self, Self, Self, Self, Self, Self, Self, Self]:
        """The eight adjacent points, diagonals included."""
        return (*self.neighbors4, self + (1, 1), self + (1, -1), self + (-1, 1), self + (-1, -1))

    def _dimension_error(self, position: tuple[float, ...]) -> ValueError:
        """The error for combining points of unequal dimensionality."""
        return ValueError(
            f"cannot combine {len(self)} coordinates with {len(position)}: "
            f"{type(self).__name__}{tuple(self)} and {tuple(position)}. "
            f"Convert explicitly with .to2 or .to3."
        )

    def _combine(self, other: PointLike | float, operation: Callable[[float, float], float]) -> Self:
        """Apply `operation` coordinate-wise against a point of equal dimensionality, or a scalar."""
        # Ordered so the common point-and-point case never reaches the expensive ABC check.
        if isinstance(other, tuple):
            position: tuple[float, ...] = other
        elif isinstance(other, SCALAR_TYPES):
            return type(self)([operation(value, other) for value in self])
        else:
            position = coordinates(other)
        try:
            return type(self)([operation(a, b) for a, b in zip(self, position, strict=True)])
        except ValueError:
            raise self._dimension_error(position) from None

    def __add__(self, other: PointLike | float) -> Self:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self._combine(other, operator.add)

    def __sub__(self, other: PointLike | float) -> Self:
        return self._combine(other, operator.sub)

    def __mul__(self, other: PointLike | float) -> Self:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self._combine(other, operator.mul)

    def __truediv__(self, other: PointLike | float) -> Self:
        return self._combine(other, operator.truediv)

    # Required, not conveniences: without them `(1, 2) + point` inherits tuple concatenation and `2 * point`
    # inherits sequence repetition, both silently returning a 4-tuple. Delegating to the forward operator keeps
    # `Point2`'s fast path. Addition and multiplication are commutative, so no operand order is lost.

    def __radd__(self, other: PointLike | float) -> Self:
        return self.__add__(other)

    def __rmul__(self, other: PointLike | float) -> Self:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self.__mul__(other)

    def __neg__(self) -> Self:
        return type(self)(-value for value in self)

    def __abs__(self) -> float:
        return self.length

    def __str__(self) -> str:
        return f"({', '.join(f'{value:.2f}' for value in self)})"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({tuple(self)})"


class Point2(_CoordinateTuple, tuple[float, float]):
    """An immutable 2D point, constructed from an iterable: `Point2((3, 4))`.

    A tuple subclass, so it unpacks, hashes and compares like `(x, y)` and works as a dict key.
    """

    __slots__ = ()

    @classmethod
    def from_proto(cls, data: common_pb2.Point2D | common_pb2.PointI) -> Self:
        """Build from a protobuf 2D point message."""
        return cls((data.x, data.y))

    def to3(self, z: float = 0.0) -> Point3:
        """The point at height `z`."""
        return Point3((self[0], self[1], z))

    # Two-coordinate fast paths, ~2.5x quicker than the general implementation and used in per-unit loops.

    def __add__(self, other: PointLike | float) -> Point2:  # pyright: ignore[reportIncompatibleMethodOverride]
        if isinstance(other, tuple) and len(other) == 2:
            return Point2((self[0] + other[0], self[1] + other[1]))
        return super().__add__(other)

    def __sub__(self, other: PointLike | float) -> Point2:
        if isinstance(other, tuple) and len(other) == 2:
            return Point2((self[0] - other[0], self[1] - other[1]))
        return super().__sub__(other)


class Point3(_CoordinateTuple, tuple[float, float, float]):
    """An immutable 3D point, used for terrain height and debug drawing."""

    __slots__ = ()

    @classmethod
    def from_proto(cls, data: common_pb2.Point) -> Self:
        """Build from a protobuf 3D point message."""
        return cls((data.x, data.y, data.z))

    @property
    def z(self) -> float:
        """The height coordinate."""
        return self[2]

    def to2(self) -> Point2:
        """The point with its height dropped."""
        return Point2((self[0], self[1]))


class Rect(tuple[float, float, float, float]):
    """An axis-aligned rectangle, as `(x, y, width, height)`."""

    __slots__ = ()

    @classmethod
    def from_proto(cls, data: common_pb2.RectangleI) -> Self:
        """Build from a protobuf `RectangleI`, which stores opposite corners rather than a size."""
        return cls((data.p0.x, data.p0.y, data.p1.x - data.p0.x, data.p1.y - data.p0.y))

    @property
    def x(self) -> float:
        """The left edge."""
        return self[0]

    @property
    def y(self) -> float:
        """The bottom edge."""
        return self[1]

    @property
    def width(self) -> float:
        """Extent along x."""
        return self[2]

    @property
    def height(self) -> float:
        """Extent along y."""
        return self[3]

    @property
    def right(self) -> float:
        """The right edge."""
        return self[0] + self[2]

    @property
    def top(self) -> float:
        """The top edge."""
        return self[1] + self[3]

    @property
    def center(self) -> Point2:
        """The midpoint."""
        return Point2((self[0] + self[2] / 2, self[1] + self[3] / 2))

    @property
    def corners(self) -> tuple[Point2, Point2, Point2, Point2]:
        """The four corners, counter-clockwise from the bottom left."""
        return (
            Point2((self.x, self.y)),
            Point2((self.right, self.y)),
            Point2((self.right, self.top)),
            Point2((self.x, self.top)),
        )

    def offset(self, point: PointLike) -> Rect:
        """The rectangle shifted by a point, keeping its size.

        A named method rather than `+`, which could as easily mean growing the rectangle as moving it.
        """
        position = coordinates(point)
        return Rect((self[0] + position[0], self[1] + position[1], self[2], self[3]))

    def contains(self, point: PointLike) -> bool:
        """Whether a point lies inside, edges included."""
        position = coordinates(point)
        return self.x <= position[0] <= self.right and self.y <= position[1] <= self.top

    def __contains__(self, point: object) -> bool:
        if isinstance(point, tuple) and len(point) >= 2:
            return self.contains(point)
        return hasattr(point, "position") and self.contains(point)  # pyright: ignore[reportArgumentType]

    def __repr__(self) -> str:
        return f"Rect(x={self.x}, y={self.y}, width={self.width}, height={self.height})"
