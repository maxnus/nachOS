"""Stand-ins for the game, shared by the tests that drive the library without one."""

from collections import deque
from typing import Any

from s2clientprotocol import sc2api_pb2
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
