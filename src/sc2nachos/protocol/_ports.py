"""The ports a client needs to join a multiplayer game."""

from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class GamePorts:
    """A `(game, base)` port pair for the server, and one for each player in the match."""

    server: tuple[int, int]
    players: tuple[tuple[int, int], ...]

    @classmethod
    def from_start_port(cls, start_port: int) -> Self:
        """The ladder's layout: five consecutive ports from `start_port`, of which the first goes unused."""
        return cls(server=(start_port + 2, start_port + 3), players=((start_port + 4, start_port + 5),))
