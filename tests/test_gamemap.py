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
        game_map = GameMap.from_proto(
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
        game_map = GameMap.from_proto(make_game_info(*["#" * 8] * 6, playable=(1, 2, 7, 5)))
        assert game_map.playable_area == Rectangle(1, 2, 6, 3)
        for grid in (game_map.pathing, game_map.placement, game_map.height):
            assert grid.bounds == game_map.playable_area
        assert game_map.pathing[Tile(1, 2)]
        # Open on the drawing, but off the playable area.
        assert not game_map.pathing[Tile(0, 0)]
        assert not game_map.placement[Point((7.5, 4.5))]
        with pytest.raises(IndexError, match="lies outside"):
            _ = game_map.height[Tile(0, 0)]

    def test_the_height_is_in_the_units_of_a_unit_z(self) -> None:
        game_map = GameMap.from_proto(make_game_info("###", heights=make_bytes([0, 51, 255])))
        assert game_map.height[Tile(0, 0)] == -16.0
        assert game_map.height[Tile(1, 0)] == pytest.approx(-9.6)
        assert game_map.height[Tile(2, 0)] == 16.0

    def test_the_grids_refuse_writes_but_a_copy_does_not(self) -> None:
        game_map = GameMap.from_proto(make_game_info())
        with pytest.raises(ValueError, match="read-only"):
            game_map.pathing[Tile(0, 0)] = False
        copy = game_map.pathing.copy()
        copy[Tile(0, 0)] = False
        assert game_map.pathing[Tile(0, 0)]

    def test_the_opponent_start_locations_are_the_ones_the_game_names(self) -> None:
        game_map = GameMap.from_proto(make_game_info(start_locations=((5.5, 2.5),)))
        assert game_map.opponent_start_locations == (Point((5.5, 2.5)),)

    def test_an_image_too_short_for_its_size_is_refused(self) -> None:
        info = make_game_info()
        info.start_raw.pathing_grid.data = info.start_raw.pathing_grid.data[:-1]
        with pytest.raises(ProtocolError, match="cannot be 7 bytes"):
            GameMap.from_proto(info)

    def test_a_playable_area_past_the_image_is_refused(self) -> None:
        with pytest.raises(ProtocolError, match="does not cover"):
            GameMap.from_proto(make_game_info(playable=(0, 0, 9, 8)))


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
    def test_every_unit_on_the_ground_stands_at_the_height_of_the_ground(self, path: Path) -> None:
        info, observation = _start(path)
        game_map = GameMap.from_proto(info)
        for unit in observation.raw_data.units:
            if not unit.is_flying:
                # Within a step of the byte it is stored in, and a little more on a slope.
                assert game_map.height[Point((unit.pos.x, unit.pos.y))] == pytest.approx(unit.pos.z, abs=0.2)

    def test_nothing_open_is_left_off_the_playable_area(self, path: Path) -> None:
        info, _ = _start(path)
        game_map = GameMap.from_proto(info)
        for grid, image in (
            (game_map.pathing, info.start_raw.pathing_grid),
            (game_map.placement, info.start_raw.placement_grid),
        ):
            assert grid.sum() == int(numpy.unpackbits(numpy.frombuffer(image.data, dtype=numpy.uint8)).sum())

    def test_this_players_own_townhall_blocks_pathing_but_not_placement(self, path: Path) -> None:
        info, observation = _start(path)
        game_map = GameMap.from_proto(info)
        townhall = _own_townhall(observation)
        assert not game_map.pathing[townhall]
        assert game_map.placement[townhall]

    def test_the_opponent_start_locations_leave_out_this_players_own(self, path: Path) -> None:
        info, observation = _start(path)
        game_map = GameMap.from_proto(info)
        assert game_map.opponent_start_locations
        assert _own_townhall(observation) not in game_map.opponent_start_locations
