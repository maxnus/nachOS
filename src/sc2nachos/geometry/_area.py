"""The shared interface of the shapes a bot reasons about."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from sc2nachos.geometry._point import Point, PointLike
    from sc2nachos.geometry._shapes import Rectangle, TileSet


class Area(ABC):
    """A patch of ground: somewhere to attack, to scout, or to filter positions by."""

    # Without this every subclass carries a __dict__, whatever slots it declares itself.
    __slots__ = ()

    @property
    @abstractmethod
    def center(self) -> Point:
        """The middle of the area."""

    @property
    @abstractmethod
    def area(self) -> float:
        """The ground covered, in square game units."""

    @abstractmethod
    def random_point(self) -> Point:
        """A point drawn uniformly from the area.

        A method rather than a property: each call consumes randomness and answers differently.
        """

    @abstractmethod
    def __contains__(self, point: PointLike) -> bool:
        """Whether a point lies inside, written `point in area`.

        Raises `TypeError` on anything but a point: `in` has no way to signal an unsupported operand, so an
        unusable one would silently answer False.
        """

    @abstractmethod
    def translated(self, offset: PointLike) -> Self:
        """The area shifted by `offset`, keeping its shape."""

    @abstractmethod
    def closest_point_to(self, point: PointLike) -> tuple[Point, float]:
        """The point of the area nearest to `point`, and the distance to it."""

    @abstractmethod
    def bounding_rectangle(self) -> Rectangle:
        """The smallest rectangle containing the area."""

    @abstractmethod
    def tiles(self) -> TileSet:
        """The area as the set of grid tiles it covers."""
