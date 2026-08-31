"""Geometry primitives."""

import math

import numpy
import pytest

from sc2nachos.geometry import Point2, Point3, Rect


class TestPoint2:
    def test_behaves_as_a_tuple(self) -> None:
        """A point unpacks, compares and hashes like the coordinate tuple it is."""
        point = Point2((3, 4))
        x, y = point
        assert (x, y) == (3, 4)
        assert point == (3, 4)

        # A point and the plain tuple the protocol hands over must be the same dict key.
        board: dict[tuple[float, ...], str] = {point: "value"}
        assert board[(3, 4)] == "value"

    def test_coordinates(self) -> None:
        point = Point2((3, 4))
        assert (point.x, point.y) == (3, 4)
        assert point.position is point

    def test_distance(self) -> None:
        assert Point2((0, 0)).distance_to((3, 4)) == 5
        assert Point2((0, 0)).distance_to_squared((3, 4)) == 25
        assert Point2((0, 0)).is_closer_than(6, (3, 4))
        assert not Point2((0, 0)).is_closer_than(5, (3, 4))

    def test_arithmetic(self) -> None:
        assert Point2((1, 2)) + (3, 4) == (4, 6)
        assert Point2((1, 2)) - (3, 4) == (-2, -2)
        assert Point2((1, 2)) * 3 == (3, 6)
        assert Point2((3, 6)) / 3 == (1, 2)
        assert -Point2((1, 2)) == (-1, -2)

    def test_operand_order_is_preserved(self) -> None:
        """Subtraction and division are not commutative; a zip that swapped operands would pass `+` and `*`."""
        assert Point2((10, 20)) - (1, 2) == (9, 18)
        assert Point2((10, 20)) / 2 == (5, 10)
        assert Point3((10, 20, 30)) - Point3((1, 2, 3)) == (9, 18, 27)

    def test_fast_path_and_general_path_agree(self) -> None:
        """Point2 specializes 2-tuple operands for speed; both paths must give the same answer."""
        point = Point2((10, 20))
        assert point + Point2((1, 2)) == point + Point3((1, 2, 0)).to2()
        assert point - (1, 2) == point + (-1, -2)

        class Unit:
            position = Point2((1, 2))

        assert point + Unit() == (11, 22), "a positioned object takes the general path"
        assert point + 5 == (15, 25), "a scalar takes the general path"

    def test_reflected_operators_beat_tuple_semantics(self) -> None:
        """Without these, tuple concatenation and sequence repetition are inherited and silently win."""
        point = Point2((3.0, 4.0))
        assert (1, 2) + point == (4, 6)
        assert isinstance((1, 2) + point, Point2)
        assert 2 * point == (6, 8)
        assert isinstance(2 * point, Point2)
        assert 2.0 * point == (6, 8)

    def test_reflected_operators_still_check_dimensionality(self) -> None:
        with pytest.raises(ValueError, match="cannot combine"):
            _ = (1, 2, 3) + Point2((3.0, 4.0))

    def test_arithmetic_returns_points_not_tuples(self) -> None:
        """Operators must not fall back to tuple concatenation."""
        result = Point2((1, 2)) + (3, 4)
        assert isinstance(result, Point2)
        assert len(result) == 2, "tuple.__add__ would have concatenated into a 4-tuple"

    def test_length_and_normalized(self) -> None:
        assert Point2((3, 4)).length == 5
        assert Point2((3, 4)).normalized == pytest.approx((0.6, 0.8))
        with pytest.raises(ZeroDivisionError):
            _ = Point2((0, 0)).normalized

    def test_towards(self) -> None:
        assert Point2((0, 0)).towards((10, 0), 3) == (3, 0)
        assert Point2((0, 0)).towards((10, 0), -3) == (-3, 0)
        assert Point2((0, 0)).towards((0, 0), 3) == (0, 0), "a point cannot move toward itself"

    def test_towards_with_limit_does_not_overshoot(self) -> None:
        assert Point2((0, 0)).towards((3, 4), 100, limit=True) == (3, 4)
        assert Point2((0, 0)).towards((3, 4), 100) != (3, 4)

    def test_rounded_really_rounds(self) -> None:
        """Distinct from `floored`. The reference implementation conflated the two under this name."""
        assert Point2((1.4, 2.6)).rounded == (1, 3)
        assert Point2((1.6, 2.6)).rounded == (2, 3)

    def test_floored_gives_the_containing_cell(self) -> None:
        assert Point2((1.4, 2.6)).floored == (1, 2)
        assert Point2((1.9, 2.9)).floored == (1, 2)

    def test_cell_center(self) -> None:
        """Units sit at cell centers, so any point in a cell maps to the same target."""
        assert Point2((1.1, 2.9)).cell_center == (1.5, 2.5)
        assert Point2((1.9, 2.1)).cell_center == (1.5, 2.5)

    def test_grid_operations_differ(self) -> None:
        """Guards the distinction: a naive `round` would agree with `floor` here and hide the bug."""
        point = Point2((1.7, 1.7))
        assert point.rounded == (2, 2)
        assert point.floored == (1, 1)
        assert point.cell_center == (1.5, 1.5)

    def test_angle_and_rotate(self) -> None:
        assert Point2((0, 0)).angle_to((1, 1)) == pytest.approx(math.pi / 4)
        assert Point2((1, 0)).rotate(math.pi / 2) == pytest.approx((0, 1))
        assert Point2((2, 1)).rotate(math.pi, around=(1, 1)) == pytest.approx((0, 1))

    def test_direction_vector(self) -> None:
        assert Point2((1, 1)).direction_vector((1, 5)) == pytest.approx((0, 1))

    def test_closest_and_furthest(self) -> None:
        origin = Point2((0, 0))
        points = [(10, 0), (1, 1), (5, 5)]
        assert origin.closest(points) == (1, 1)
        assert origin.furthest(points) == (10, 0)
        with pytest.raises(ValueError):
            origin.closest([])

    def test_neighbors(self) -> None:
        point = Point2((0, 0))
        assert set(point.neighbors4) == {(0, 1), (0, -1), (1, 0), (-1, 0)}
        assert len(set(point.neighbors8)) == 8
        assert set(point.neighbors4) < set(point.neighbors8)

    def test_neighbors_have_fixed_arity(self) -> None:
        """The counts are in the names, so the return types state them too."""
        point = Point2((0, 0))
        assert len(point.neighbors4) == 4
        assert len(point.neighbors8) == 8


class TestPoint3:
    def test_is_not_a_point2(self) -> None:
        """The two hold different numbers of coordinates, so neither is substitutable for the other.

        Claiming otherwise breaks `x, y = point` and hides a 3D point from a set of 2D ones.
        """
        point = Point3((1, 2, 3))
        assert not isinstance(point, Point2)
        assert not isinstance(Point2((1, 2)), Point3)
        assert Point3((1, 2, 0)) != Point2((1, 2)), "different dimensionality is not equality"

    def test_to3_takes_a_height(self) -> None:
        assert Point2((1, 2)).to3(5) == (1, 2, 5)
        assert Point2((1, 2)).to3(z=5) == (1, 2, 5)
        assert Point2((1, 2)).to3() == (1, 2, 0)

    def test_converts_explicitly(self) -> None:
        point = Point3((1, 2, 3))
        assert (point.x, point.y, point.z) == (1, 2, 3)
        assert point.to2() == (1, 2)
        assert isinstance(point.to2(), Point2)
        assert Point2((1, 2)).to3() == (1, 2, 0)
        assert isinstance(Point2((1, 2)).to3(), Point3)

    def test_operations_keep_the_type(self) -> None:
        """Every operation returns a Point3, so height survives a chain of calls."""
        point = Point3((1, 2, 3))
        assert isinstance(point.towards((10, 2, 3), 1), Point3)
        assert isinstance(point.rotate(1.0), Point3)
        assert isinstance(point.rounded, Point3)

    def test_towards_keeps_height(self) -> None:
        """Moving toward another point must not flatten a 3D point to 2D."""
        moved = Point3((0, 0, 7)).towards(Point3((10, 0, 7)), 3)
        assert moved == (3, 0, 7)

    def test_rotate_keeps_height(self) -> None:
        rotated = Point3((1, 0, 9)).rotate(math.pi / 2)
        assert rotated == pytest.approx((0, 1, 9))

    def test_distance_uses_the_ground_plane(self) -> None:
        """Range checks in StarCraft are horizontal, so height must not enter the distance."""
        assert Point3((0, 0, 100)).distance_to(Point3((3, 4, -50))) == 5

    def test_arithmetic_keeps_the_height(self) -> None:
        """Adding two Point3s must not silently degrade to a Point2 and drop z."""
        total = Point3((1, 2, 3)) + Point3((10, 20, 30))
        assert isinstance(total, Point3)
        assert (total.x, total.y, total.z) == (11, 22, 33)

    def test_towards_rejects_mixed_dimensionality(self) -> None:
        """The same rule as arithmetic, so there is one rule to remember rather than a rule with exceptions."""
        with pytest.raises(ValueError, match="cannot combine"):
            _ = Point3((1, 2, 3)).towards(Point2((10, 10)), 1)

    def test_towards_rejects_even_when_the_ground_positions_match(self) -> None:
        """The zero-separation early return would otherwise skip the check entirely."""
        with pytest.raises(ValueError, match="cannot combine"):
            _ = Point3((1, 2, 3)).towards(Point2((1, 2)), 1)

    def test_ground_plane_operations_stay_permissive(self) -> None:
        """Operations that read only x and y cannot lose a coordinate, so they accept either dimensionality."""
        assert Point3((0, 0, 99)).distance_to(Point2((3, 4))) == 5
        assert Point3((1, 0, 9)).rotate(math.pi / 2, around=Point2((0, 0))) == pytest.approx((0, 1, 9))

    def test_mixed_dimensionality_is_rejected(self) -> None:
        """Silently reconciling would discard a coordinate in one direction and invent one in the other."""
        with pytest.raises(ValueError, match="cannot combine"):
            _ = Point3((1, 2, 3)) + Point2((10, 10))
        with pytest.raises(ValueError, match="cannot combine"):
            _ = Point2((1, 2)) + Point3((10, 10, 10))
        with pytest.raises(ValueError, match="cannot combine"):
            _ = Point3((1, 2, 3)) - (10, 10)

    def test_dimension_error_names_both_operands(self) -> None:
        """zip(strict=True) alone would only say "argument 2 is shorter than argument 1"."""
        with pytest.raises(ValueError, match=r"3 coordinates with 2.*Point3\(1, 2, 3\).*\(10, 10\)"):
            _ = Point3((1, 2, 3)) + Point2((10, 10))

    def test_mixed_dimensionality_has_an_explicit_spelling(self) -> None:
        """The conversion the error suggests is the supported way to do it."""
        assert Point3((1, 2, 3)) + Point2((10, 10)).to3() == (11, 12, 3)
        assert Point3((1, 2, 3)).to2() + Point2((10, 10)) == (11, 12)

    def test_scalars_are_not_mixed_dimensionality(self) -> None:
        assert Point3((1, 2, 3)) + 10 == (11, 12, 13)

    def test_scaling_and_negation_keep_the_height(self) -> None:
        assert Point3((1, 2, 3)) * 2 == (2, 4, 6)
        assert -Point3((1, 2, 3)) == (-1, -2, -3)
        assert Point3((1.4, 2.6, 3.5)).rounded == (1, 3, 4)


class TestNumpyScalars:
    """The bot's grids are numpy arrays, so values read out of them land in point arithmetic."""

    @pytest.mark.parametrize("dtype", ["float64", "float32", "float16", "int64", "int32", "int8", "uint8"])
    def test_numpy_scalars_are_accepted(self, dtype: str) -> None:
        """Only float64 subclasses Python float; the rest need `numbers.Real` to be recognized."""
        scalar = getattr(numpy, dtype)(2)
        assert Point2((3.0, 4.0)) * scalar == (6, 8)
        assert Point2((3.0, 4.0)) / getattr(numpy, dtype)(1) == (3, 4)
        assert Point3((3.0, 4.0, 5.0)) * scalar == (6, 8, 10)

    def test_value_read_from_an_array(self) -> None:
        grid = numpy.full((4, 4), 2.0, dtype=numpy.float32)
        assert Point2((3.0, 4.0)) * grid[1, 1] == (6, 8)

    def test_a_numpy_array_is_not_a_scalar(self) -> None:
        with pytest.raises(TypeError, match="expected a point"):
            _ = Point2((3.0, 4.0)) * numpy.array([1.0, 2.0])


class TestUnsupportedOperands:
    def test_error_names_the_type(self) -> None:
        """Previously an operand with no `.position` produced a confusing AttributeError."""
        with pytest.raises(TypeError, match="expected a point or something with a .position, got str"):
            # Statically rejected too; this covers callers that are not type-checked.
            _ = Point2((1, 2)) + "banana"  # pyright: ignore[reportOperatorIssue]


class TestPositionedObjects:
    """Geometry accepts anything with a `.position`, so a unit works wherever a point does."""

    class Unit:
        def __init__(self, x: float, y: float) -> None:
            self.position = Point2((x, y))

    def test_distance_to_a_positioned_object(self) -> None:
        assert Point2((0, 0)).distance_to(self.Unit(3, 4)) == 5
        assert Point2((0, 0)).distance_to_squared(self.Unit(3, 4)) == 25
        assert Point2((0, 0)).is_closer_than(6, self.Unit(3, 4))

    def test_towards_a_positioned_object(self) -> None:
        assert Point2((0, 0)).towards(self.Unit(10, 0), 3) == (3, 0)

    def test_closest_returns_the_object_that_was_passed_in(self) -> None:
        """Not a converted point — so a unit comes back as a unit and a Point3 keeps its height."""
        far, near = self.Unit(10, 0), self.Unit(1, 1)
        assert Point2((0, 0)).closest([far, near]) is near
        assert Point2((0, 0)).furthest([far, near]) is far

        points = [Point3((10, 0, 5)), Point3((1, 1, 5))]
        assert Point2((0, 0)).closest(points) == (1, 1, 5)

    def test_rect_contains_a_positioned_object(self) -> None:
        assert Rect((0, 0, 10, 10)).contains(self.Unit(5, 5))


class TestRect:
    def test_edges_and_size(self) -> None:
        rect = Rect((10, 20, 30, 40))
        assert (rect.x, rect.y, rect.width, rect.height) == (10, 20, 30, 40)
        assert rect.right == 40
        assert rect.top == 60
        assert rect.center == (25, 40)

    def test_is_not_a_point(self) -> None:
        """A rectangle is deliberately not a Point2 — it should not be usable where a point is expected."""
        rect = Rect((10, 20, 30, 40))
        assert not isinstance(rect, Point2)
        assert not hasattr(rect, "distance_to")

    def test_contains(self) -> None:
        rect = Rect((0, 0, 10, 10))
        assert rect.contains((5, 5))
        assert (5, 5) in rect
        assert rect.contains((0, 0)), "edges count as inside"
        assert rect.contains((10, 10))
        assert not rect.contains((11, 5))

    def test_contains_rejects_non_points(self) -> None:
        """`__contains__` has no reflected form, so returning NotImplemented would answer True."""
        rect = Rect((0, 0, 10, 10))
        assert "banana" not in rect
        assert None not in rect
        assert 5 not in rect

    def test_corners_wind_counter_clockwise(self) -> None:
        assert Rect((0, 0, 2, 2)).corners == ((0, 0), (2, 0), (2, 2), (0, 2))

    def test_offset_preserves_size(self) -> None:
        moved = Rect((0, 0, 10, 10)).offset((5, 5))
        assert moved == (5, 5, 10, 10)
        assert isinstance(moved, Rect)
