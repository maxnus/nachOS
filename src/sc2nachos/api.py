"""Everything a bot talks to."""

from dataclasses import dataclass

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

    client: Client
    info: sc2api_pb2.ResponseGameInfo
    data: sc2api_pb2.ResponseData
    observation: sc2api_pb2.ResponseObservation | None = None
    turn: int = 0
    game_loop: int = 0
    result: Result | None = None

    def finish(self, result: Result) -> Result:
        """Settle how the game ended, and say so."""
        self.result = result
        seconds = steps_to_seconds(self.game_loop)
        logger.info("The game ended in a {} on turn {} at {:.0f} seconds", result, self.turn, seconds)
        return result


class Api:
    """Everything a bot talks to, built before there is a game to talk to.

    Construct one where the rest of your bot can reach it, which may be module scope, and hand it to `run_local`
    or `run_ladder` for every game it plays. Never subclass it: helpers of your own belong in your own modules, as
    ordinary functions.
    """

    def __init__(self, *, step_size: int = 1) -> None:
        """Take a turn every `step_size` game frames. Nothing here connects to anything."""
        self._step_size = step_size
        # Everything that belongs to one game and nothing that outlives it, so each game replaces it whole.
        self._game: _Game | None = None

    @property
    def step_size(self) -> int:
        """How many game frames pass between turns."""
        return self._step_size

    @property
    def client(self) -> Client:
        """The client of the game being played, or of the last one once it is over."""
        if self._game is None:
            raise NotPlayingError("no game has been joined")
        return self._game.client

    @property
    def turn(self) -> int:
        """How many turns the game has had, which is zero before the first one."""
        return self._game.turn if self._game is not None else 0

    @property
    def game_loop(self) -> int:
        """The frame the game had reached when it was last observed."""
        return self._game.game_loop if self._game is not None else 0

    @property
    def time(self) -> float:
        """How long the game has been played, in seconds."""
        return steps_to_seconds(self.game_loop)

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
        # The map and the static tables never change during a game, so they are asked for once.
        game = _Game(client, client.game_info(), client.game_data())
        self._game = game
        logger.info("Playing {} at {} frames a turn", game.info.map_name, self._step_size)

        while True:
            # A realtime game runs whether or not anyone is watching, so a turn asks for the frame it wants.
            target = game.game_loop + self._step_size if realtime and game.turn else None
            game.observation = client.observation(game_loop=target)
            game.game_loop = game.observation.observation.game_loop

            if (result := client.result) is not None:
                return game.finish(result)
            if not client.in_game:
                # Over, and the game would not say how even when the client asked it again.
                return game.finish(Result.UNDECIDED)
            if time_limit is not None and self.time >= time_limit:
                logger.info("Calling the game a tie at its {:.0f} second limit", time_limit)
                return game.finish(Result.TIE)

            game.turn += 1
            # A turn's work belongs here, once there is any: the event dispatch and the flush of orders.

            if not realtime:
                client.step(self._step_size)
