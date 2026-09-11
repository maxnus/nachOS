"""Everything a bot talks to."""

from dataclasses import dataclass
from typing import Final, Self

from loguru import logger
from s2clientprotocol import sc2api_pb2

from sc2nachos.constants import steps_to_seconds
from sc2nachos.match import Result
from sc2nachos.protocol import Client


class NotPlayingError(Exception):
    """There is no game to answer from, because none has been joined."""


@dataclass(slots=True)
class _Game:
    """One game as it is played: the client it is played on, and everything seen of it so far."""

    client: Final[Client]
    info: Final[sc2api_pb2.ResponseGameInfo]
    # The tables as they stood before any upgrade, which both sides share. Asked again later they fold in this
    # player's upgrades, and with one entry per unit type they would hand those to the enemy's units too.
    data: Final[sc2api_pb2.ResponseData]
    observation: sc2api_pb2.ResponseObservation | None = None
    step: int = 0
    result: Result | None = None

    @classmethod
    def start(cls, client: Client) -> Self:
        """Start on the game `client` has joined, asking once for its map and for the tables before any upgrade."""
        return cls(client, client.game_info(), client.game_data())

    def observe(self, step: int | None = None) -> Result | None:
        """Observe the game now, or once it reaches `step`, and return how it ended if it has."""
        self.observation = self.client.observation(game_loop=step)
        # The protocol's game loop is what NachOS calls a step, and this is the one place the two meet.
        self.step = self.observation.observation.game_loop
        if (result := self.client.result) is not None:
            return self.finish(result)
        if not self.client.in_game:
            # Over, and the game would not say how even when the client asked it again.
            return self.finish(Result.UNDECIDED)
        return None

    def finish(self, result: Result) -> Result:
        """Settle how the game ended, and say so."""
        self.result = result
        seconds = steps_to_seconds(self.step)
        logger.info("The game ended in a {} at step {}, {:.0f} seconds in", result, self.step, seconds)
        return result


class Api:
    """Everything a bot talks to, built before there is a game to talk to.

    Construct one where the rest of your bot can reach it, which may be module scope, and hand it to `run_local`
    or `run_ladder` for every game it plays. Never subclass it: helpers of your own belong in your own modules, as
    ordinary functions.

    Time is counted in steps. One step is one game loop, 22.4 of them make a second, and the bot takes a turn
    every `steps_per_turn` of them.
    """

    def __init__(self, *, steps_per_turn: int = 1) -> None:
        """Take a turn every `steps_per_turn` steps. Nothing here connects to anything."""
        self._steps_per_turn = steps_per_turn
        # Everything that belongs to one game and nothing that outlives it, so each game replaces it whole.
        self._game: _Game | None = None

    @property
    def steps_per_turn(self) -> int:
        """How many steps pass between one turn and the next."""
        return self._steps_per_turn

    @property
    def client(self) -> Client:
        """The client of the game being played, or of the last one once it is over."""
        if self._game is None:
            raise NotPlayingError("no game has been joined")
        return self._game.client

    @property
    def step(self) -> int:
        """The step the game had reached when it was last observed, which is zero before it has been."""
        return self._game.step if self._game is not None else 0

    @property
    def time(self) -> float:
        """How long the game has been played, in seconds."""
        return steps_to_seconds(self.step)

    @property
    def result(self) -> Result | None:
        """How the game ended for this player, or `None` while it is still being played."""
        return self._game.result if self._game is not None else None

    def play(self, client: Client, *, realtime: bool = False, time_limit: float | None = None) -> Result:
        """Play the game `client` has already joined to its end, and return how it ended for this player.

        `run_local` and `run_ladder` call this. Call it directly to play a game connected some other way,
        such as a recording. `time_limit` gives up on a game that is taking too long, in game seconds.

        Each call starts its game from nothing, so one api plays any number of games, one after another.
        """
        game = _Game.start(client)
        self._game = game
        logger.info("Playing {} at {} steps a turn", game.info.map_name, self._steps_per_turn)

        while True:
            # A realtime game runs whether or not anyone is watching, so each turn after the first asks for the
            # step it wants.
            target = game.step + self._steps_per_turn if realtime and game.observation is not None else None
            if (result := game.observe(target)) is not None:
                return result
            if time_limit is not None and self.time >= time_limit:
                logger.info("Calling the game a tie at its {:.0f} second limit", time_limit)
                return game.finish(Result.TIE)

            # A turn's work belongs here, once there is any: the event dispatch and the flush of orders.

            if not realtime:
                client.step(self._steps_per_turn)
