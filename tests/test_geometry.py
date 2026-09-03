"""Geometry primitives."""

import math

import numpy
import pytest

from sc2nachos.geometry import Point, Point3D, Rectangle, Tile, TileSet


class TestPoint2:
    def test_behaves_as_a_tuple(self) -> None:
        """A point unpacks, compares and hashes like the coordinate tuple it is."""
        point = Point((3, 4))
        x, y = point
        assert (x, y) == (3, 4)
        assert point == (3, 4)

        # A point and the plain tuple the protocol hands over must be the same dict key.
        board: dict[tuple[float, ...], str] = {point: "value"}
        assert board[(3, 4)] == "value"

    def test_coordinates(self) -> None:
        point = Point((3, 4))
        assert (point.x, point.y) == (3, 4)
        assert point.position is point

    def test_distance(self) -> None:
        assert Point((0, 0)).distance_to((3, 4)) == 5
        assert Point((0, 0)).distance_to_squared((3, 4)) == 25
        assert Point((0, 0)).is_closer_than(6, (3, 4))
        assert not Point((0, 0)).is_closer_than(5, (3, 4))

    def test_arithmetic(self) -> None:
        assert Point((1, 2)) + (3, 4) == (4, 6)
        assert Point((1, 2)) - (3, 4) == (-2, -2)
        assert Point((1, 2)) * 3 == (3, 6)
        assert Point((3, 6)) / 3 == (1, 2)
        assert -Point((1, 2)) == (-1, -2)

    def test_operand_order_is_preserved(self) -> None:
        """Subtraction and division are not commutative; a zip that swapped operands would pass `+` and `*`."""
        assert Point((10, 20)) - (1, 2) == (9, 18)
        assert Point((10, 20)) / 2 == (5, 10)
        assert Point3D((10, 20, 30)) - Point3D((1, 2, 3)) == (9, 18, 27)

    def test_fast_path_and_general_path_agree(self) -> None:
        """Point specializes 2-tuple operands for speed; both paths must give the same answer."""
        point = Point((10, 20))
        assert point + Point((1, 2)) == point + Point3D((1, 2, 0)).ground
        assert point - (1, 2) == point + (-1, -2)

        class Unit:
            position = Point((1, 2))

        assert point + Unit() == (11, 22), "a positioned object takes the general path"
        assert point + 5 == (15, 25), "a scalar takes the general path"

    def test_reflected_operators_beat_tuple_semantics(self) -> None:
        """Without these, tuple concatenation and sequence repetition are inherited and silently win."""
        point = Point((3.0, 4.0))
        assert (1, 2) + point == (4, 6)
        assert isinstance((1, 2) + point, Point)
        assert 2 * point == (6, 8)
        assert isinstance(2 * point, Point)
        assert 2.0 * point == (6, 8)

    def test_reflected_operators_still_check_dimensionality(self) -> None:
        with pytest.raises(ValueError, match="cannot combine"):
            _ = (1, 2, 3) + Point((3.0, 4.0))

    def test_arithmetic_returns_points_not_tuples(self) -> None:
        """Operators must not fall back to tuple concatenation."""
        result = Point((1, 2)) + (3, 4)
        assert isinstance(result, Point)
        assert len(result) == 2, "tuple.__add__ would have concatenated into a 4-tuple"

    def test_length_and_normalized(self) -> None:
        assert Point((3, 4)).length == 5
        assert Point((3, 4)).normalized == pytest.approx((0.6, 0.8))
        with pytest.raises(ZeroDivisionError):
            _ = Point((0, 0)).normalized

    def test_towards(self) -> None:
        assert Point((0, 0)).towards((10, 0), 3) == (3, 0)
        assert Point((0, 0)).towards((10, 0), -3) == (-3, 0)
        assert Point((0, 0)).towards((0, 0), 3) == (0, 0), "a point cannot move toward itself"

    def test_towards_with_limit_does_not_overshoot(self) -> None:
        assert Point((0, 0)).towards((3, 4), 100, limit=True) == (3, 4)
        assert Point((0, 0)).towards((3, 4), 100) != (3, 4)

    def test_angle_and_rotate(self) -> None:
        assert Point((0, 0)).angle_to((1, 1)) == pytest.approx(math.pi / 4)
        assert Point((1, 0)).rotated(math.pi / 2) == pytest.approx((0, 1))
        assert Point((2, 1)).rotated(math.pi, around=(1, 1)) == pytest.approx((0, 1))

    def test_direction_vector(self) -> None:
        assert Point((1, 1)).direction_vector((1, 5)) == pytest.approx((0, 1))

    def test_closest_and_furthest(self) -> None:
        origin = Point((0, 0))
        points = [(10, 0), (1, 1), (5, 5)]
        assert origin.closest(points) == (1, 1)
        assert origin.furthest(points) == (10, 0)
        with pytest.raises(ValueError):
            origin.closest([])


class TestPoint3:
    def test_is_not_a_point2(self) -> None:
        """The two hold different numbers of coordinates, so neither is substitutable for the other.

        Claiming otherwise breaks `x, y = point` and hides a 3D point from a set of 2D ones.
        """
        point = Point3D((1, 2, 3))
        assert not isinstance(point, Point)
        assert not isinstance(Point((1, 2)), Point3D)
        assert Point3D((1, 2, 0)) != Point((1, 2)), "different dimensionality is not equality"

    def test_with_height_takes_a_height(self) -> None:
        assert Point((1, 2)).with_height(5) == (1, 2, 5)
        assert Point((1, 2)).with_height(z=5) == (1, 2, 5)
        assert Point((1, 2)).with_height() == (1, 2, 0), "defaults to ground level"

    def test_converts_explicitly(self) -> None:
        point = Point3D((1, 2, 3))
        assert (point.x, point.y, point.z) == (1, 2, 3)
        assert point.ground == (1, 2)
        assert isinstance(point.ground, Point)
        assert Point((1, 2)).with_height() == (1, 2, 0)
        assert isinstance(Point((1, 2)).with_height(), Point3D)

    def test_operations_keep_the_type(self) -> None:
        """Every operation returns a Point3D, so height survives a chain of calls."""
        point = Point3D((1, 2, 3))
        assert isinstance(point.towards((10, 2, 3), 1), Point3D)
        assert isinstance(point.rotated(1.0), Point3D)
        assert isinstance(point.normalized, Point3D)

    def test_towards_keeps_height(self) -> None:
        """Moving toward another point must not flatten a 3D point to 2D."""
        moved = Point3D((0, 0, 7)).towards(Point3D((10, 0, 7)), 3)
        assert moved == (3, 0, 7)

    def test_rotate_keeps_height(self) -> None:
        rotated = Point3D((1, 0, 9)).rotated(math.pi / 2)
        assert rotated == pytest.approx((0, 1, 9))

    def test_distance_uses_the_ground_plane(self) -> None:
        """Range checks in StarCraft are horizontal, so height must not enter the distance."""
        assert Point3D((0, 0, 100)).distance_to(Point3D((3, 4, -50))) == 5

    def test_arithmetic_keeps_the_height(self) -> None:
        """Adding two Point3s must not silently degrade to a Point and drop z."""
        total = Point3D((1, 2, 3)) + Point3D((10, 20, 30))
        assert isinstance(total, Point3D)
        assert (total.x, total.y, total.z) == (11, 22, 33)

    def test_towards_rejects_mixed_dimensionality(self) -> None:
        """The same rule as arithmetic, so there is one rule to remember rather than a rule with exceptions."""
        with pytest.raises(ValueError, match="cannot combine"):
            _ = Point3D((1, 2, 3)).towards(Point((10, 10)), 1)

    def test_towards_rejects_even_when_the_ground_positions_match(self) -> None:
        """The zero-separation early return would otherwise skip the check entirely."""
        with pytest.raises(ValueError, match="cannot combine"):
            _ = Point3D((1, 2, 3)).towards(Point((1, 2)), 1)

    def test_ground_plane_operations_stay_permissive(self) -> None:
        """Operations that read only x and y cannot lose a coordinate, so they accept either dimensionality."""
        assert Point3D((0, 0, 99)).distance_to(Point((3, 4))) == 5
        assert Point3D((1, 0, 9)).rotated(math.pi / 2, around=Point((0, 0))) == pytest.approx((0, 1, 9))

    def test_mixed_dimensionality_is_rejected(self) -> None:
        """Silently reconciling would discard a coordinate in one direction and invent one in the other."""
        with pytest.raises(ValueError, match="cannot combine"):
            _ = Point3D((1, 2, 3)) + Point((10, 10))
        with pytest.raises(ValueError, match="cannot combine"):
            _ = Point((1, 2)) + Point3D((10, 10, 10))
        with pytest.raises(ValueError, match="cannot combine"):
            _ = Point3D((1, 2, 3)) - (10, 10)

    def test_dimension_error_names_both_operands(self) -> None:
        """zip(strict=True) alone would only say "argument 2 is shorter than argument 1"."""
        with pytest.raises(ValueError, match=r"3 coordinates with 2.*Point3D\(1, 2, 3\).*\(10, 10\)"):
            _ = Point3D((1, 2, 3)) + Point((10, 10))

    def test_mixed_dimensionality_has_an_explicit_spelling(self) -> None:
        """The conversion the error suggests is the supported way to do it."""
        assert Point3D((1, 2, 3)) + Point((10, 10)).with_height() == (11, 12, 3)
        assert Point3D((1, 2, 3)).ground + Point((10, 10)) == (11, 12)

    def test_scalars_are_not_mixed_dimensionality(self) -> None:
        assert Point3D((1, 2, 3)) + 10 == (11, 12, 13)

    def test_scaling_and_negation_keep_the_height(self) -> None:
        assert Point3D((1, 2, 3)) * 2 == (2, 4, 6)
        assert -Point3D((1, 2, 3)) == (-1, -2, -3)


class TestNumpyScalars:
    """The bot's grids are numpy arrays, so values read out of them land in point arithmetic."""

    @pytest.mark.parametrize("dtype", ["float64", "float32", "float16", "int64", "int32", "int8", "uint8"])
    def test_numpy_scalars_are_accepted(self, dtype: str) -> None:
        """Only float64 subclasses Python float; the rest need `numbers.Real` to be recognized."""
        scalar = getattr(numpy, dtype)(2)
        assert Point((3.0, 4.0)) * scalar == (6, 8)
        assert Point((3.0, 4.0)) / getattr(numpy, dtype)(1) == (3, 4)
        assert Point3D((3.0, 4.0, 5.0)) * scalar == (6, 8, 10)

    def test_value_read_from_an_array(self) -> None:
        grid = numpy.full((4, 4), 2.0, dtype=numpy.float32)
        assert Point((3.0, 4.0)) * grid[1, 1] == (6, 8)

    def test_a_numpy_array_is_not_a_scalar(self) -> None:
        with pytest.raises(TypeError, match="expected a point"):
            _ = Point((3.0, 4.0)) * numpy.array([1.0, 2.0])


class TestUnsupportedOperands:
    def test_error_names_the_type(self) -> None:
        """Previously an operand with no `.position` produced a confusing AttributeError."""
        with pytest.raises(TypeError, match="expected a point or something with a .position, got str"):
            # Statically rejected too; this covers callers that are not type-checked.
            _ = Point((1, 2)) + "banana"  # pyright: ignore[reportOperatorIssue]


class TestPositionedObjects:
    """Geometry accepts anything with a `.position`, so a unit works wherever a point does."""

    class Unit:
        def __init__(self, x: float, y: float) -> None:
            self.position = Point((x, y))

    def test_distance_to_a_positioned_object(self) -> None:
        assert Point((0, 0)).distance_to(self.Unit(3, 4)) == 5
        assert Point((0, 0)).distance_to_squared(self.Unit(3, 4)) == 25
        assert Point((0, 0)).is_closer_than(6, self.Unit(3, 4))

    def test_towards_a_positioned_object(self) -> None:
        assert Point((0, 0)).towards(self.Unit(10, 0), 3) == (3, 0)

    def test_closest_returns_the_object_that_was_passed_in(self) -> None:
        """Not a converted point â€” so a unit comes back as a unit and a Point3D keeps its height."""
        far, near = self.Unit(10, 0), self.Unit(1, 1)
        assert Point((0, 0)).closest([far, near]) is near
        assert Point((0, 0)).furthest([far, near]) is far

        points = [Point3D((10, 0, 5)), Point3D((1, 1, 5))]
        assert Point((0, 0)).closest(points) == (1, 1, 5)

    def test_rectangle_contains_a_positioned_object(self) -> None:
        assert self.Unit(5, 5) in Rectangle(0, 0, 10, 10)


class TestRectangle:
    def test_edges_and_size(self) -> None:
        rect = Rectangle(10, 20, 30, 40)
        assert (rect.x, rect.y, rect.width, rect.height) == (10, 20, 30, 40)
        assert (rect.left, rect.bottom, rect.right, rect.top) == (10, 20, 40, 60)
        assert rect.center == (25, 40)
        assert rect.size == (30, 40)
        assert rect.area == 1200
        assert rect.perimeter == 140

    def test_compares_and_hashes_by_value(self) -> None:
        assert Rectangle(1, 2, 3, 4) == Rectangle(1, 2, 3, 4)
        assert len({Rectangle(1, 2, 3, 4), Rectangle(1, 2, 3, 4)}) == 1

    def test_is_not_a_sequence(self) -> None:
        """A rectangle is four named edges, not four numbers in a row."""
        assert not isinstance(Rectangle(1, 2, 3, 4), tuple)

    def test_is_not_a_point(self) -> None:
        """A rectangle is deliberately not a Point — it should not be usable where a point is expected."""
        rect = Rectangle(10, 20, 30, 40)
        assert not isinstance(rect, Point)
        assert not hasattr(rect, "distance_to")

    def test_from_center(self) -> None:
        assert Rectangle.from_center((5, 5), 4, 2) == Rectangle(3, 4, 4, 2)

    def test_contains_is_half_open(self) -> None:
        """Adjacent rectangles must partition the ground, so a point belongs to exactly one of them."""
        rect = Rectangle(0, 0, 10, 10)
        assert (5, 5) in rect
        assert (0, 0) in rect, "the lower edges are inside"
        assert (10, 10) not in rect, "the upper edges belong to the next rectangle"
        assert (11, 5) not in rect

    def test_encloses(self) -> None:
        assert Rectangle(0, 0, 10, 10).encloses(Rectangle(2, 2, 4, 4))
        assert not Rectangle(0, 0, 10, 10).encloses(Rectangle(2, 2, 40, 4))

    def test_contains_rejects_non_points(self) -> None:
        """`in` cannot signal an unsupported operand, so an unusable one must raise rather than answer False."""
        rect = Rectangle(0, 0, 10, 10)
        for item in ("banana", None, 5):
            with pytest.raises(TypeError):
                _ = item in rect  # pyright: ignore[reportOperatorIssue]

    def test_corners_wind_counter_clockwise(self) -> None:
        assert Rectangle(0, 0, 2, 2).corners == ((0, 0), (2, 0), (2, 2), (0, 2))

    def test_translated_preserves_size(self) -> None:
        moved = Rectangle(0, 0, 10, 10).translated((5, 5))
        assert moved == Rectangle(5, 5, 10, 10)
        assert isinstance(moved, Rectangle)

    def test_translated_accepts_a_negative_offset(self) -> None:
        assert Rectangle(5, 5, 2, 2).translated((-5, -5)) == Rectangle(0, 0, 2, 2)

    def test_intersects(self) -> None:
        rect = Rectangle(0, 0, 10, 10)
        assert rect.intersects(Rectangle(5, 5, 10, 10))
        assert not rect.intersects(Rectangle(10, 0, 10, 10)), "touching edges do not overlap"

    def test_intersection(self) -> None:
        overlap = Rectangle(0, 0, 10, 10).intersection(Rectangle(5, 5, 10, 10))
        assert overlap == Rectangle(5, 5, 5, 5)
        assert Rectangle(0, 0, 10, 10).intersection(Rectangle(20, 20, 5, 5)) is None

    def test_rounding_out_contains_rounding_in(self) -> None:
        rect = Rectangle(0.4, 0.6, 5.3, 5.1)
        inner = rect.rounded_in()
        assert inner is not None
        assert rect.rounded_out() == Rectangle(0, 0, 6, 6)
        assert inner == Rectangle(1, 1, 4, 4)
        assert rect.rounded_out().encloses(inner)

    def test_rounding_in_a_rectangle_smaller_than_a_tile(self) -> None:
        """Returning a rectangle here gave one of negative extent, whose area still read as positive."""
        assert Rectangle(0.4, 0.4, 0.2, 0.2).rounded_in() is None
        assert Rectangle(0.0, 0.0, 1.0, 0.5).rounded_in() is None, "one axis is enough"

    def test_closest_point_to(self) -> None:
        rect = Rectangle(0, 0, 10, 10)
        assert rect.closest_point_to((5, 5)) == ((5, 5), 0.0)
        assert rect.closest_point_to((13, 5)) == ((10, 5), 3.0)

    def test_random_point_is_inside(self) -> None:
        rect = Rectangle(3, 7, 2, 4)
        assert all(rect.random_point() in rect for _ in range(100))

    def test_bounding_rectangle_is_itself(self) -> None:
        rect = Rectangle(1, 2, 3, 4)
        assert rect.bounding_rectangle() is rect

    def test_tile_centers_are_laid_out_like_the_tiles(self) -> None:
        points = Rectangle(0, 0, 3, 2).tile_centers()
        assert points.shape == (3, 2, 2)
        assert points[0, 0].tolist() == [0.5, 0.5]
        assert points[2, 1].tolist() == [2.5, 1.5]

    def test_tile_centers_agree_with_tiles(self) -> None:
        """Both must cover the same tiles, or a mask over one cannot index the other."""
        rect = Rectangle(0.4, 0.6, 5.3, 5.1)
        centers = rect.tile_centers().reshape(-1, 2)
        assert {Tile.containing(tuple(point)) for point in centers} == set(rect.tiles())

    def test_tile_centers_offset_shifts_without_changing_coverage(self) -> None:
        """An even-sized footprint sits on a tile corner, so the caller shifts by half a tile."""
        plain = Rectangle(0, 0, 3, 2).tile_centers()
        shifted = Rectangle(0, 0, 3, 2).tile_centers(offset=(-0.5, -0.5))
        assert shifted.shape == plain.shape
        assert shifted[0, 0].tolist() == [0.0, 0.0]


class TestTile:
    def test_containing_floors(self) -> None:
        """Flooring, not rounding: the reference implementation conflated the two."""
        assert Tile.containing((3.9, 4.1)) == Tile(3, 4)
        assert Tile.containing(Point((1.9, 2.9))) == Tile(1, 2), "rounding would give Tile(2, 3)"
        assert Tile.containing((-0.5, -0.5)) == Tile(-1, -1), "floors rather than truncating"

    def test_containing_takes_anything_with_a_position(self) -> None:
        assert Tile.containing(Point3D((1.4, 2.6, 9.9))) == Tile(1, 2), "height is dropped"
        assert Tile.containing(self.Positioned(3.5, 4.5)) == Tile(3, 4)

    class Positioned:
        """Stands in for a unit."""

        def __init__(self, x: float, y: float) -> None:
            self.position = Point((x, y))

    def test_center_is_where_a_unit_stands(self) -> None:
        assert Tile(3, 4).center == Point((3.5, 4.5))

    def test_indexes_numpy_directly(self) -> None:
        grid = numpy.arange(100).reshape(10, 10)
        assert grid[Tile(3, 4)] == grid[3, 4]

    def test_is_an_area(self) -> None:
        tile = Tile(3, 4)
        assert tile.area == 1.0
        assert tile.bounding_rectangle() == Rectangle(3, 4, 1, 1)
        assert len(tile.tiles()) == 1

    def test_contains_is_area_membership_not_tuple_membership(self) -> None:
        tile = Tile(3, 4)
        assert (3.5, 4.5) in tile
        assert (3.0, 4.0) in tile, "the lower edges are inside"
        assert (4.0, 4.5) not in tile, "the upper edges belong to the next tile"
        with pytest.raises(TypeError):
            _ = 3 in tile

    def test_translated(self) -> None:
        assert Tile(3, 4).translated((2, -1)) == Tile(5, 3)

    def test_read_as_a_point_it_is_the_center(self) -> None:
        """The tuple is the grid address, but as a point a tile is where a unit would stand."""
        tile = Tile(3, 4)
        assert tile in Rectangle(3, 4, 1, 1)
        assert Point((3.5, 4.5)).distance_to(tile) == 0.0
        assert Point((3, 4)).distance_to(tile) == pytest.approx(math.sqrt(0.5))

    def test_the_address_and_the_position_stay_separate(self) -> None:
        """Indexing reads the tuple; point math reads `.position`. Both are right for their purpose."""
        grid = numpy.arange(100).reshape(10, 10)
        tile = Tile(3, 4)
        assert grid[tile] == grid[3, 4]
        assert tile.position == (3.5, 4.5)
        assert Point((0, 0)).towards(tile, 1.0) == pytest.approx(tile.center.normalized)

    def test_neighbors(self) -> None:
        assert set(Tile(0, 0).neighbors4) == {Tile(0, 1), Tile(0, -1), Tile(1, 0), Tile(-1, 0)}
        assert len(set(Tile(0, 0).neighbors8)) == 8
        assert set(Tile(0, 0).neighbors4) < set(Tile(0, 0).neighbors8)

    def test_neighbors_have_fixed_arity(self) -> None:
        """The counts are in the names, so the return types state them too."""
        assert len(Tile(0, 0).neighbors4) == 4
        assert len(Tile(0, 0).neighbors8) == 8

    def test_random_point_is_inside(self) -> None:
        tile = Tile(7, 2)
        assert all(tile.random_point() in tile for _ in range(100))

    def test_closest_point_to(self) -> None:
        assert Tile(0, 0).closest_point_to((5, 0.5)) == ((1, 0.5), 4.0)


class TestAreaLayout:
    def test_the_value_shapes_carry_no_instance_dict(self) -> None:
        """`Area` must declare __slots__ itself, or its subclasses get a __dict__ whatever they declare."""
        for obj in (Tile(1, 2), Rectangle(0, 0, 1, 1), Point((1, 2)), Point3D((1, 2, 3))):
            assert not hasattr(obj, "__dict__"), type(obj).__name__

    def test_tile_sets_keep_one_for_their_caches(self) -> None:
        """TileSet deliberately opts back in: cached_property needs somewhere to write."""
        assert hasattr(TileSet([Tile(0, 0)]), "__dict__")


class TestAreaAgreement:
    """The same ground must answer the same way however it is wrapped."""

    areas = (Tile(0, 0), TileSet([Tile(0, 0)]), Rectangle(0, 0, 1, 1))

    @pytest.mark.parametrize("probe", [(5, 0.5), (0.9, 0.9), (-3, -3), (0.5, 0.5), (1.5, 0.5)])
    def test_closest_point_to_agrees(self, probe: tuple[float, float]) -> None:
        results = [area.closest_point_to(probe) for area in self.areas]
        assert len({(tuple(point), round(distance, 9)) for point, distance in results}) == 1, results

    @pytest.mark.parametrize("probe", [(5, 0.5), (0.9, 0.9), (-3, -3), (0.5, 0.5)])
    def test_the_distance_matches_the_point(self, probe: tuple[float, float]) -> None:
        """A returned point 0.57 away once came back with a distance of 0.0."""
        for area in self.areas:
            point, distance = area.closest_point_to(probe)
            assert distance == pytest.approx(point.distance_to(probe)), area

    @pytest.mark.parametrize("probe", [(0.5, 0.5), (0.0, 0.0), (0.99, 0.99), (1.0, 0.5), (-0.1, 0.5)])
    def test_membership_agrees(self, probe: tuple[float, float]) -> None:
        assert len({probe in area for area in self.areas}) == 1


class TestTileSet:
    def test_points_in_one_tile_collapse(self) -> None:
        tiles = TileSet([Tile.containing((0.1, 0.9)), Tile.containing((0.4, 0.2))])
        assert len(tiles) == 1, "both points fall in the same tile"
        assert (0.7, 0.7) in tiles

    def test_rejects_an_empty_tile_set(self) -> None:
        with pytest.raises(ValueError, match="at least one tile"):
            TileSet([])

    def test_area_counts_unit_tiles(self) -> None:
        tiles = Rectangle(0, 0, 3, 2).tiles()
        assert len(tiles) == 6
        assert tiles.area == 6.0

    def test_center(self) -> None:
        assert Rectangle(0, 0, 4, 4).tiles().center == (2, 2)

    def test_bounding_rectangle_covers_whole_tiles(self) -> None:
        """The tiles are unit squares, so the bounds run to their edges rather than their centers."""
        assert TileSet([Tile(0, 0), Tile(2, 3)]).bounding_rectangle() == Rectangle(0, 0, 3, 4)

    def test_round_trips_through_a_rectangle(self) -> None:
        rect = Rectangle(0, 0, 5, 5)
        assert rect.tiles().bounding_rectangle() == rect

    def test_closest_point_to(self) -> None:
        tiles = Rectangle(0, 0, 2, 2).tiles()
        assert tiles.closest_point_to((0.5, 0.5)) == ((0.5, 0.5), 0.0)
        point, distance = tiles.closest_point_to((10, 1.5))
        assert point == (2, 1.5), "the near edge of the covered ground, not a tile center"
        assert distance == pytest.approx(8.0)

    def test_random_point_is_inside(self) -> None:
        tiles = Rectangle(0, 0, 3, 3).tiles()
        assert all(tiles.random_point() in tiles for _ in range(50))

    def test_union_and_difference(self) -> None:
        left = Rectangle(0, 0, 2, 1).tiles()
        right = Rectangle(2, 0, 2, 1).tiles()
        assert len(left + right) == 4
        assert (left + right) - right == left
        assert left - left is None, "a tile set cannot be empty"

    def test_translated_moves_every_tile(self) -> None:
        tiles = Rectangle(0, 0, 2, 2).tiles()
        moved = tiles.translated((3, 0))
        assert len(moved) == len(tiles)
        assert moved.bounding_rectangle() == Rectangle(3, 0, 2, 2)

    def test_translated_by_a_partial_tile_snaps_back_to_the_grid(self) -> None:
        """Tiles are the unit of the set, so a fractional shift lands on whole tiles."""
        moved = TileSet([Tile(0, 0)]).translated((0.5, 0))
        assert moved == TileSet([Tile(1, 0)])

    def test_iteration_order_does_not_depend_on_how_the_set_was_built(self) -> None:
        """A set reached by difference used to iterate differently from the same set built directly."""
        direct = TileSet([Tile(x, y) for x in range(8) for y in range(8)])
        wider = TileSet([Tile(x, y) for x in range(12) for y in range(12)])
        right = wider - TileSet([Tile(x, y) for x in range(8, 12) for y in range(12)])
        assert right is not None
        carved = right - TileSet([Tile(x, y) for x in range(8) for y in range(8, 12)])
        assert carved is not None
        assert carved == direct
        assert list(carved) == list(direct)

    def test_iterates_by_ascending_x_then_y(self) -> None:
        assert list(Rectangle(0, 0, 2, 2).tiles()) == [Tile(0, 0), Tile(0, 1), Tile(1, 0), Tile(1, 1)]

    def test_filter(self) -> None:
        tiles = Rectangle(0, 0, 4, 1).tiles()
        filtered = tiles.filter(lambda point: point.x < 2)
        assert filtered is not None
        assert len(filtered) == 2
        assert tiles.filter(lambda point: point.x > 100) is None

    def test_equality_is_by_covered_tiles(self) -> None:
        assert Rectangle(0, 0, 2, 2).tiles() != Rectangle(0, 0, 3, 3).tiles()
