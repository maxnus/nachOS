"""What can go wrong between the library and the game."""


class ProtocolError(Exception):
    """The game refused a request, or answered one with something other than what it asked for."""


class GameEndedError(ProtocolError):
    """The request needs a game in progress, and this one is over."""


class ConnectionClosedError(ProtocolError):
    """The connection to the game is gone, so the request cannot be answered."""


class ConnectionTimeoutError(ProtocolError):
    """The game did not answer within the transport's timeout."""
