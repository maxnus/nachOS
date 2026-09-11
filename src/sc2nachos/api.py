"""Everything a bot talks to."""

from typing import TYPE_CHECKING

from loguru import logger

from sc2nachos.constants import steps_to_seconds
from sc2nachos.match import Result
from sc2nachos.protocol import Client

if TYPE_CHECKING:
    from s2clientprotocol import sc2api_pb2


class NotPlayingError(Exception):
    """There is no game to answer from, because none has been joined."""


class Api:
    """Everything a bot talks to, built before there is a game to talk to.

    Construct one for each game, where the rest of your bot can reach it, then hand it to `run_local` or
    `run_ladder`. Never subclass it: helpers of your own belong in your own modules, as ordinary functions.
    """

    def __init__(self, *, step_size: int = 1) -> None:
        """Take a turn every `step_size` game frames. Nothing here connects to anything."""
        self._step_size = step_size
        self._client: Client | None = None
        self._game_info: sc2api_pb2.ResponseGameInfo | None = None
        self._game_data: sc2api_pb2.ResponseData | None = None
        self._observation: sc2api_pb2.ResponseObservation | None = None
        self._turn = 0
        self._game_loop = 0
        self._result: Result | None = None

    @property
    def step_size(self) -> int:
        """How many game frames pass between turns."""
        return self._step_size

    @property
    def client(self) -> Client:
        """The game client, from the moment a game has been joined."""
        if self._client is None:
            raise NotPlayingError("no game has been joined")
        return self._client

    @property
    def turn(self) -> int:
        """How many turns have been played, which is zero before the first one."""
        return self._turn

    @property
    def game_loop(self) -> int:
        """The frame the game had reached when it was last observed."""
        return self._game_loop

    @property
    def time(self) -> float:
        """How long the game has been played, in seconds."""
        return steps_to_seconds(self._game_loop)

    @property
    def result(self) -> Result | None:
        """How the game ended for this player, or `None` while it is still being played."""
        return self._result

    def play(self, client: Client, *, realtime: bool = False, time_limit: float | None = None) -> Result:
        """Play the game `client` has already joined to its end, and return how it ended for this player.

        `run_local` and `run_ladder` call this. Call it directly to play a game connected some other way,
        such as a recording. `time_limit` gives up on a game that is taking too long, in game seconds.

        An api plays one game, so calling this a second time raises `RuntimeError`.
        """
        if self._client is not None:
            raise RuntimeError("an api plays one game, so make a new one for the next")
        self._client = client
        # The map and the static tables never change during a game, so they are asked for once.
        self._game_info = client.game_info()
        self._game_data = client.game_data()
        logger.info("Playing {} at {} frames a turn", self._game_info.map_name, self._step_size)

        while True:
            # A realtime game runs whether or not anyone is watching, so a turn asks for the frame it wants.
            target = self._game_loop + self._step_size if realtime and self._turn else None
            self._observation = client.observation(game_loop=target)
            self._game_loop = self._observation.observation.game_loop

            if (result := client.result) is not None:
                return self._finish(result)
            if not client.in_game:
                # Over, and the game would not say how even when the client asked it again.
                return self._finish(Result.UNDECIDED)
            if time_limit is not None and self.time >= time_limit:
                logger.info("Calling the game a tie at its {:.0f} second limit", time_limit)
                return self._finish(Result.TIE)

            self._turn += 1
            # A turn's work belongs here, once there is any: the event dispatch and the flush of orders.

            if not realtime:
                client.step(self._step_size)

    def _finish(self, result: Result) -> Result:
        """Settle how the game ended, and say so."""
        self._result = result
        logger.info("The game ended in a {} on turn {} at {:.0f} seconds", result, self._turn, self.time)
        return result
