"""Stand-ins for the game, shared by the tests that drive the library without one."""

from collections import deque
from typing import Any

import numpy
from s2clientprotocol import common_pb2, raw_pb2, sc2api_pb2
from websocket import WebSocketConnectionClosedException

from sc2nachos.match import Result
from sc2nachos.protocol import Client, Status


class FakeTransport:
    """A `Transport` that answers from a prepared queue and remembers what it was asked."""

    def __init__(self, *responses: sc2api_pb2.Response) -> None:
        self.requests: list[sc2api_pb2.Request] = []
        self.closed = False
        self._responses = deque(responses)

    def request(self, request: sc2api_pb2.Request) -> sc2api_pb2.Response:
        self.requests.append(request)
        if not self._responses:
            raise AssertionError("the client asked more of the transport than the test prepared")
        return self._responses.popleft()

    def close(self) -> None:
        self.closed = True


class FakeWebSocket:
    """The three methods `WebSocketTransport` uses, over a prepared queue of payloads or a `failure` to raise."""

    def __init__(self, *payloads: str | bytes, failure: Exception | None = None) -> None:
        self.sent: list[bytes] = []
        self.closed = False
        self._payloads: deque[str | bytes] = deque(payloads)
        self._failure = failure

    def send_binary(self, payload: bytes) -> int:
        if self.closed:
            raise WebSocketConnectionClosedException("socket is already closed.")
        self.sent.append(payload)
        return len(payload)

    def recv(self) -> str | bytes:
        if self._failure is not None:
            raise self._failure
        if not self._payloads:
            raise WebSocketConnectionClosedException("Connection to remote host was lost.")
        return self._payloads.popleft()

    def close(self) -> None:
        self.closed = True


def make_response(status: Status | None = Status.IN_GAME, **fields: Any) -> sc2api_pb2.Response:
    """A response carrying `fields`, and `status` unless it is given as `None`."""
    response = sc2api_pb2.Response(**fields)
    if status is not None:
        response.status = status.value
    return response


def make_bits(*rows: str, drawn: str = "#") -> common_pb2.ImageData:
    """A one-bit image drawn as rows of characters, the top row first, set wherever one of `drawn` stands."""
    bits = [char in drawn for row in reversed(rows) for char in row]
    size = common_pb2.Size2DI(x=len(rows[0]), y=len(rows))
    return common_pb2.ImageData(bits_per_pixel=1, size=size, data=numpy.packbits(bits).tobytes())


def make_bytes(*rows: list[int]) -> common_pb2.ImageData:
    """A one-byte image of `rows` of values, the top row first, the way the map would look."""
    data = bytes(value for row in reversed(rows) for value in row)
    return common_pb2.ImageData(bits_per_pixel=8, size=common_pb2.Size2DI(x=len(rows[0]), y=len(rows)), data=data)


def make_game_info(
    *rows: str,
    playable: tuple[int, int, int, int] | None = None,
    heights: common_pb2.ImageData | None = None,
    start_locations: tuple[tuple[float, float], ...] = (),
) -> sc2api_pb2.ResponseGameInfo:
    """A map drawn in rows, the top row first, or eight by eight of open ground.

    `#` is open ground, `~` ground a unit can walk over but not build on, and `.` ground it can do neither on.
    The map is playable from corner to corner unless `playable` gives the corners `(x0, y0, x1, y1)` of a smaller
    area, and level unless `heights` says otherwise.
    """
    rows = rows or ("#" * 8,) * 8
    width, height = len(rows[0]), len(rows)
    x0, y0, x1, y1 = playable or (0, 0, width, height)
    return sc2api_pb2.ResponseGameInfo(
        map_name="Somewhere",
        start_raw=raw_pb2.StartRaw(
            map_size=common_pb2.Size2DI(x=width, y=height),
            pathing_grid=make_bits(*rows, drawn="#~"),
            placement_grid=make_bits(*rows),
            terrain_height=heights or make_bytes(*([128] * width for _ in range(height))),
            playable_area=common_pb2.RectangleI(p0=common_pb2.PointI(x=x0, y=y0), p1=common_pb2.PointI(x=x1, y=y1)),
            start_locations=[common_pb2.Point2D(x=x, y=y) for x, y in start_locations],
        ),
    )


def make_observation(game_loop: int = 0, *results: tuple[int, Result]) -> sc2api_pb2.ResponseObservation:
    """What the game saw at `game_loop`, and how it ended if it has."""
    return sc2api_pb2.ResponseObservation(
        observation=sc2api_pb2.Observation(game_loop=game_loop),
        player_result=[sc2api_pb2.PlayerResult(player_id=player, result=result.value) for player, result in results],
    )


def make_client(*responses: sc2api_pb2.Response) -> tuple[Client, FakeTransport]:
    """A client over a transport that will answer `responses`, and that transport."""
    transport = FakeTransport(*responses)
    return Client(transport), transport
