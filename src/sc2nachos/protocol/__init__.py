"""Talking to a running game client."""

from sc2nachos.protocol._client import Client
from sc2nachos.protocol._errors import (
    ConnectionClosedError,
    ConnectionTimeoutError,
    GameEndedError,
    ProtocolError,
)
from sc2nachos.protocol._ports import GamePorts
from sc2nachos.protocol._status import Status
from sc2nachos.protocol._transport import Transport
from sc2nachos.protocol._websocket import WebSocketTransport

__all__ = [
    "Client",
    "ConnectionClosedError",
    "ConnectionTimeoutError",
    "GameEndedError",
    "GamePorts",
    "ProtocolError",
    "Status",
    "Transport",
    "WebSocketTransport",
]
