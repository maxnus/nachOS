"""The map as a game describes it, read from maps drawn here and from the recorded games."""

from pathlib import Path

import numpy
import pytest
from s2clientprotocol import raw_pb2, sc2api_pb2

from sc2nachos.gamemap import GameMap
from sc2nachos.geometry import Point, Rectangle, Tile
from sc2nachos.ids import UnitTypeId
from sc2nachos.protocol import ProtocolError, Recording
from support import make_bytes, make_game_info

CORPUS = sorted((Path(__file__).parent / "corpus").glob("*.sc2rec"))
_TOWNHALLS = {UnitTypeId.COMMAND_CENTER, UnitTypeId.HATCHERY, UnitTypeId.NEXUS}


class TestReadingAMap:
    def test_the_grids_read_the_map_the_way_up_it_is_drawn(self) -> None:
        # Sixteen across, so each row spans two bytes and a wrong bit order moves the open tile.
        game_map = GameMap(
            make_game_info(
                "................",
                "..........#.....",
                "................",
            )
        )
        assert game_map.pathing[Tile(10, 1)]
        assert game_map.placement[Tile(10, 1)]
        assert game_map.pathing.sum() == game_map.placement.sum() == 1

    def test_the_grids_cover_the_playable_area_and_read_closed_past_it(self) -> None:
        game_map = GameMap(make_game_info(*["#" * 8] * 6, playable=(1, 2, 7, 5)))
        assert game_map.playable_area == Rectangle(1, 2, 6, 3)
        for grid in (game_map.pathing, game_map.placement, game_map.height):
            assert grid.bounds == game_map.playable_area
        assert game_map.pathing[Tile(1, 2)]
        # Open on the drawing, but off the playable area.
        assert not game_map.pathing[Tile(0, 0)]
        assert not game_map.placement[Point((7.5, 4.5))]
        with pytest.raises(IndexError, match="lies outside"):
            _ = game_map.height[Tile(0, 0)]

    # 191, 207, 223 and 239 are the levels units stand on, at 8, 10, 12 and 14.
    @pytest.mark.parametrize(
        ("byte", "height"), [(0, -15.875), (127, 0.0), (191, 8.0), (207, 10.0), (223, 12.0), (239, 14.0), (255, 16.0)]
    )
    def test_a_byte_of_height_is_an_eighth_with_127_at_zero(self, byte: int, height: float) -> None:
        game_map = GameMap(make_game_info("##", "##", heights=make_bytes([byte] * 2, [byte] * 2)))
        assert game_map.height[Tile(0, 0)] == game_map.height_at(Point((0.3, 0.8))) == height

    def test_a_tile_on_a_ramp_is_as_high_as_its_corners_on_average(self) -> None:
        # The heights are the tiles' corners, so four tiles across have five corners, rising a quarter each.
        heights = make_bytes(*[[191, 193, 195, 197, 199]] * 3)
        game_map = GameMap(make_game_info(*["#####"] * 3, playable=(0, 0, 4, 2), heights=heights))
        assert [game_map.height[Tile(x, 0)] for x in range(4)] == [8.125, 8.375, 8.625, 8.875]
        assert game_map.height_at(Point((1.25, 0.5))) == 8.3125
        assert game_map.height_at(Point((1.0, 0.0))) == 8.25

    @pytest.mark.parametrize(
        ("rows", "height"),
        [
            # A ramp's top beside the cliff it runs along: the corner on the cliff line holds the level below.
            ([[207, 207, 207], [207, 207, 207], [191, 207, 207]], 10.0),
            # The foot of a cliff, whose corner on the cliff line holds the level above.
            ([[239, 239, 239], [239, 239, 239], [255, 239, 239]], 14.0),
            # Two corners on each level: the tile is on the upper one.
            ([[207, 207, 207], [207, 207, 207], [191, 191, 207]], 10.0),
        ],
    )
    def test_beside_a_cliff_a_tile_stands_on_the_side_most_of_its_corners_are_on(
        self, rows: list[list[int]], height: float
    ) -> None:
        game_map = GameMap(make_game_info(*["###"] * 3, playable=(0, 0, 2, 2), heights=make_bytes(*rows)))
        assert game_map.height[Tile(0, 0)] == height
        assert game_map.height_at(Point((0.1, 0.1))) == height

    def test_a_height_at_takes_a_point_and_not_a_tile(self) -> None:
        with pytest.raises(TypeError, match="pass its .center"):
            GameMap(make_game_info()).height_at(Tile(1, 1))

    def test_a_height_at_past_the_playable_area_raises(self) -> None:
        with pytest.raises(IndexError, match="lies outside"):
            GameMap(make_game_info(*["#" * 8] * 6, playable=(1, 2, 7, 5))).height_at(Point((0.5, 0.5)))

    def test_the_grids_refuse_writes_but_a_copy_does_not(self) -> None:
        game_map = GameMap(make_game_info())
        with pytest.raises(ValueError, match="read-only"):
            game_map.pathing[Tile(0, 0)] = False
        copy = game_map.pathing.copy()
        copy[Tile(0, 0)] = False
        assert game_map.pathing[Tile(0, 0)]

    def test_the_opponent_start_locations_are_the_ones_the_game_names(self) -> None:
        game_map = GameMap(make_game_info(start_locations=((5.5, 2.5),)))
        assert game_map.opponent_start_locations == (Point((5.5, 2.5)),)

    def test_an_image_too_short_for_its_size_is_refused(self) -> None:
        info = make_game_info()
        info.start_raw.pathing_grid.data = info.start_raw.pathing_grid.data[:-1]
        with pytest.raises(ProtocolError, match="cannot be 7 bytes"):
            GameMap(info)

    def test_a_playable_area_past_the_image_is_refused(self) -> None:
        with pytest.raises(ProtocolError, match="does not cover"):
            GameMap(make_game_info(playable=(0, 0, 9, 8)))


def _start(path: Path) -> tuple[sc2api_pb2.ResponseGameInfo, sc2api_pb2.Observation]:
    """The map a recorded game was played on, and the first observation of it."""
    info = None
    for exchange in Recording(path):
        response = exchange.response
        if response.HasField("game_info"):
            info = response.game_info
        elif response.HasField("observation"):
            assert info is not None, f"{path.name} has an observation before the map"
            return info, response.observation.observation
    raise AssertionError(f"{path.name} holds no observation")


def _own_townhall(observation: sc2api_pb2.Observation) -> Point:
    """Where this player's townhall stood as the game started."""
    return next(
        Point((unit.pos.x, unit.pos.y))
        for unit in observation.raw_data.units
        if unit.alliance == raw_pb2.Alliance.Self and unit.unit_type in _TOWNHALLS
    )


@pytest.mark.parametrize("path", CORPUS, ids=lambda path: path.stem)
class TestARecordedMap:
    def test_every_unit_on_flat_ground_stands_at_its_height(self, path: Path) -> None:
        info, observation = _start(path)
        game_map = GameMap(info)
        for unit in observation.raw_data.units:
            tile = Tile(int(unit.pos.x), int(unit.pos.y))
            around = {game_map.height[Tile(tile.x + dx, tile.y + dy)] for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
            if not unit.is_flying and len(around) == 1:
                # Units stand up to a few hundredths below it, and the ground can sit a little above: Pylon's main
                # base by 0.15.
                position = Point((unit.pos.x, unit.pos.y))
                assert -0.03 < unit.pos.z - game_map.height_at(position) < 0.16
                assert game_map.height_at(position) == game_map.height[tile]

    def test_nothing_open_is_left_off_the_playable_area(self, path: Path) -> None:
        info, _ = _start(path)
        game_map = GameMap(info)
        for grid, image in (
            (game_map.pathing, info.start_raw.pathing_grid),
            (game_map.placement, info.start_raw.placement_grid),
        ):
            assert grid.sum() == int(numpy.unpackbits(numpy.frombuffer(image.data, dtype=numpy.uint8)).sum())

    def test_this_players_own_townhall_blocks_pathing_but_not_placement(self, path: Path) -> None:
        info, observation = _start(path)
        game_map = GameMap(info)
        townhall = _own_townhall(observation)
        assert not game_map.pathing[townhall]
        assert game_map.placement[townhall]

    def test_the_opponent_start_locations_leave_out_this_players_own(self, path: Path) -> None:
        info, observation = _start(path)
        game_map = GameMap(info)
        assert game_map.opponent_start_locations
        assert _own_townhall(observation) not in game_map.opponent_start_locations
