"""A transport over the websocket a running game client listens on."""

from typing import Self

from loguru import logger
from s2clientprotocol import sc2api_pb2
from websocket import (
    WebSocket,
    WebSocketConnectionClosedException,
    WebSocketException,
    WebSocketTimeoutException,
    create_connection,
)

from sc2nachos.protocol._errors import ConnectionClosedError, ConnectionTimeoutError, ProtocolError


class WebSocketTransport:
    """A `Transport` over the websocket of a game client that is already running."""

    def __init__(self, websocket: WebSocket) -> None:
        """Wrap an open websocket, which is closed along with the transport."""
        self._websocket = websocket

    @classmethod
    def connect(cls, url: str, *, timeout: float | None = None) -> Self:
        """Open a websocket to the game client listening at `url`.

        `timeout` bounds every wait on the socket. It defaults to none, because loading a map takes as long as
        it takes and a bot has nothing to do in the meantime.
        """
        websocket = create_connection(url, timeout=timeout)
        logger.info("Connected to the game at {}", url)
        return cls(websocket)

    def request(self, request: sc2api_pb2.Request) -> sc2api_pb2.Response:
        """Send `request`, wait for the game to answer it, and return the answer."""
        try:
            self._websocket.send_binary(request.SerializeToString())
            payload = self._websocket.recv()
        except WebSocketConnectionClosedException as error:
            raise ConnectionClosedError("the connection to the game closed mid-request") from error
        except WebSocketTimeoutException as error:
            raise ConnectionTimeoutError("the game did not answer in time") from error
        except WebSocketException as error:
            raise ProtocolError(f"the websocket failed: {error}") from error
        if not isinstance(payload, bytes):
            raise ProtocolError(f"the game sent text where the protocol is binary: {payload!r}")
        response = sc2api_pb2.Response()
        response.ParseFromString(payload)
        return response

    def close(self) -> None:
        """Close the websocket."""
        self._websocket.close()
