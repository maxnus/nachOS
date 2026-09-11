"""What can go wrong between the library and the game."""

from sc2nachos._errors import NachOSError


class ProtocolError(NachOSError):
    """The game refused a request, or answered one with something other than what it asked for."""


class GameEndedError(ProtocolError):
    """The request needs a game in progress, and this one is over."""


class GameNotStartedError(ProtocolError):
    """The request needs a game in progress, and none has been started."""


class ConnectionClosedError(ProtocolError, ConnectionError):
    """The connection to the game is gone, so the request cannot be answered."""


class ConnectionTimeoutError(ProtocolError, TimeoutError):
    """The game did not answer within the transport's timeout."""
