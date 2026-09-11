"""The conversation the library holds with one game client."""

from collections.abc import Mapping, Sequence
from contextlib import suppress
from pathlib import Path
from typing import Literal

from loguru import logger
from s2clientprotocol import sc2api_pb2

from sc2nachos.match import Computer, Participant, Player, Race, Result
from sc2nachos.protocol._errors import ConnectionClosedError, GameEndedError, GameNotStartedError, ProtocolError
from sc2nachos.protocol._ports import GamePorts
from sc2nachos.protocol._status import Status
from sc2nachos.protocol._transport import Transport

# What the game says when it is asked for something only a running game can give, once the game is over.
_GAME_OVER_ERRORS = frozenset({"Game has already ended", "Not supported if game has already ended"})
# And what it says before one has started, which includes after the client has left the last one.
_NOT_STARTED_ERRORS = frozenset({"A game has not been started yet"})


# The answers this client knows how to read. Spelled out rather than taken as a `str` so that pyright checks
# each name against the response the stubs declare, which a widened parameter would silently give up.
type _Answer = Literal[
    "action", "create_game", "data", "game_info", "join_game", "observation", "ping", "save_replay", "step"
]


def _player_setup(player: Player) -> sc2api_pb2.PlayerSetup:
    """One slot in a game being created. A participant carries nothing: it says who it is when it joins."""
    match player:
        case Participant():
            return sc2api_pb2.PlayerSetup(type=sc2api_pb2.Participant)
        case Computer(race=race, difficulty=difficulty, build=build, name=name):
            setup = sc2api_pb2.PlayerSetup(
                type=sc2api_pb2.Computer, race=race.value, difficulty=difficulty.value, ai_build=build.value
            )
            if name is not None:
                setup.player_name = name
            return setup


class Client:
    """A game client, addressed over a transport.

    Every method is one request, and blocks until the game answers it. The protocol carries one request at
    a time with no way to match an answer to anything but the last question, so there is nothing to overlap.

    One connection can play game after game. What the client keeps of a game, which is its own player and how
    the game ended, lasts from the join until the game is left or the next one is set up.

    Nothing is interpreted here beyond what the protocol itself demands: the responses are the game's own
    messages, and turning them into a data model belongs above.
    """

    def __init__(self, transport: Transport) -> None:
        """Talk to the game over `transport`. Nothing is sent until a request is made."""
        self._transport = transport
        self._status: Status | None = None
        self._player_id: int | None = None
        self._results: dict[int, Result] = {}

    @property
    def status(self) -> Status | None:
        """What the game said it was doing when it last answered, or `None` before it has answered at all."""
        return self._status

    @property
    def in_game(self) -> bool:
        """Whether the game is running, as opposed to loading, ended or not yet started."""
        return self._status in (Status.IN_GAME, Status.IN_REPLAY)

    @property
    def player_id(self) -> int | None:
        """This client's player id, once it has joined a game."""
        return self._player_id

    @property
    def result(self) -> Result | None:
        """How the game ended for this client's own player, or `None` while it has not ended."""
        if self._player_id is None:
            return None
        return self._results.get(self._player_id)

    @property
    def results(self) -> Mapping[int, Result]:
        """How the game ended, by player id. Empty until it does."""
        return self._results

    def ping(self) -> sc2api_pb2.ResponsePing:
        """Ask the game which version it is, which also proves the connection works."""
        response = self._send(sc2api_pb2.Request(ping=sc2api_pb2.RequestPing()), "ping")
        return response.ping

    def create_game(
        self,
        map_path: Path | str,
        players: Sequence[Player],
        *,
        realtime: bool = False,
        disable_fog: bool = False,
        random_seed: int | None = None,
    ) -> None:
        """Set up a match on `map_path` for `players`, which each participant then joins.

        Only the client that creates the game sends this; on a ladder the game already exists. At least one player
        must be a participant, and the game seats only as many as the map has slots, dropping the rest unrefused.
        """
        self._forget_game()
        request = sc2api_pb2.RequestCreateGame(
            local_map=sc2api_pb2.LocalMap(map_path=str(map_path)),
            player_setup=[_player_setup(player) for player in players],
            realtime=realtime,
            disable_fog=disable_fog,
        )
        if random_seed is not None:
            request.random_seed = random_seed

        response = self._send(sc2api_pb2.Request(create_game=request), "create_game")
        created = response.create_game
        # An unset error field reads as the first refusal the proto declares, so ask before reading it.
        if created.HasField("error"):
            reason = sc2api_pb2.ResponseCreateGame.Error.Name(created.error)
            detail = created.error_details or "no detail given"
            raise ProtocolError(f"the game refused to create the match as {reason}: {detail}")
        logger.info("Created a game on {} for {} players", map_path, len(players))

    def join_game(
        self,
        race: Race,
        *,
        name: str | None = None,
        ports: GamePorts | None = None,
        raw_affects_selection: bool = False,
    ) -> int:
        """Join the waiting game as `race`, and return the player id the game assigns.

        NachOS plays on the raw interface, so the rendered ones are never requested.
        """
        self._forget_game()
        request = sc2api_pb2.RequestJoinGame(
            race=race.value,
            options=sc2api_pb2.InterfaceOptions(
                raw=True,
                score=True,
                show_cloaked=True,
                show_burrowed_shadows=True,
                show_placeholders=True,
                raw_affects_selection=raw_affects_selection,
                raw_crop_to_playable_area=False,
            ),
        )
        if name is not None:
            request.player_name = name
        if ports is not None:
            request.server_ports.game_port = ports.server.game
            request.server_ports.base_port = ports.server.base
            for pair in ports.players:
                request.client_ports.add(game_port=pair.game, base_port=pair.base)

        response = self._send(sc2api_pb2.Request(join_game=request), "join_game")
        joined = response.join_game
        # An unset error field reads as the first refusal the proto declares, so ask before reading it.
        if joined.HasField("error"):
            reason = sc2api_pb2.ResponseJoinGame.Error.Name(joined.error)
            detail = joined.error_details or "no detail given"
            raise ProtocolError(f"the game refused the join as {reason}: {detail}")
        self._player_id = joined.player_id
        logger.info("Joined the game as player {} playing {}", joined.player_id, race)
        return joined.player_id

    def game_info(self) -> sc2api_pb2.ResponseGameInfo:
        """The map: its size, its terrain, its start locations and the players in it."""
        response = self._send(sc2api_pb2.Request(game_info=sc2api_pb2.RequestGameInfo()), "game_info")
        return response.game_info

    def game_data(
        self,
        *,
        abilities: bool = True,
        unit_types: bool = True,
        upgrades: bool = True,
        buffs: bool = True,
        effects: bool = True,
    ) -> sc2api_pb2.ResponseData:
        """The tables behind the ids: costs, ranges, requirements and names.

        Unit weapons, armor and movement speed include the upgrades this player holds when it asks.
        """
        request = sc2api_pb2.RequestData(
            ability_id=abilities,
            unit_type_id=unit_types,
            upgrade_id=upgrades,
            buff_id=buffs,
            effect_id=effects,
        )
        response = self._send(sc2api_pb2.Request(data=request), "data")
        return response.data

    def observation(self, *, game_loop: int | None = None) -> sc2api_pb2.ResponseObservation:
        """What this player can see now, or once the game reaches `game_loop`.

        When the game is over, each player's result lands in `results`.
        """
        observation = self._observe(game_loop)
        if self.in_game and not observation.player_result:
            return observation
        if not observation.player_result:
            # The game reports itself ended a step before it will say who won, so ask once more.
            observation = self._observe(None)
        self._results = {entry.player_id: Result(entry.result) for entry in observation.player_result}
        if self._results:
            logger.info("The game ended: {}", self._results)
        return observation

    def step(self, count: int) -> sc2api_pb2.ResponseStep:
        """Let the game run `count` game loops. Only a stepped game needs this; a realtime one runs on its own."""
        response = self._send(sc2api_pb2.Request(step=sc2api_pb2.RequestStep(count=count)), "step")
        return response.step

    def act(self, actions: Sequence[sc2api_pb2.Action]) -> sc2api_pb2.ResponseAction:
        """Send `actions`, and get back the game's verdict on each one in the order they were given."""
        response = self._send(sc2api_pb2.Request(action=sc2api_pb2.RequestAction(actions=actions)), "action")
        return response.action

    def save_replay(self) -> bytes:
        """The replay of the game so far, as the bytes of a `.SC2Replay` file."""
        response = self._send(sc2api_pb2.Request(save_replay=sc2api_pb2.RequestSaveReplay()), "save_replay")
        return response.save_replay.data

    def leave_game(self) -> None:
        """Leave the game, which concedes it if it has not already ended, and return the client to `launched`.

        Leaving when there is no game to leave, or no connection left, is not an error.
        """
        with suppress(GameNotStartedError, GameEndedError, ConnectionClosedError):
            self._send(sc2api_pb2.Request(leave_game=sc2api_pb2.RequestLeaveGame()))
        self._forget_game()

    def quit(self) -> None:
        """Ask the game client to exit. A connection that has already gone is not an error here."""
        with suppress(ConnectionClosedError):
            self._send(sc2api_pb2.Request(quit=sc2api_pb2.RequestQuit()))

    def close(self) -> None:
        """Release the transport."""
        self._transport.close()

    def _forget_game(self) -> None:
        """Drop what the client kept of the last game, so none of it answers for the next."""
        self._player_id = None
        self._results = {}

    def _observe(self, game_loop: int | None) -> sc2api_pb2.ResponseObservation:
        request = sc2api_pb2.RequestObservation()
        if game_loop is not None:
            request.game_loop = game_loop
        response = self._send(sc2api_pb2.Request(observation=request), "observation")
        return response.observation

    def _send(self, request: sc2api_pb2.Request, answer: _Answer | None = None) -> sc2api_pb2.Response:
        """Send `request`, and return the response once it proves to be an `answer` the game did not refuse."""
        response = self._transport.request(request)
        # An unset status field reads as `launched`, the first value the proto declares, so ask before reading it.
        if response.HasField("status"):
            status = Status(response.status)
            if status is not self._status:
                logger.info("The game client is now {}", status)
                self._status = status
        if response.error:
            errors = list(response.error)
            if _GAME_OVER_ERRORS.intersection(errors):
                raise GameEndedError(f"the game is over: {'; '.join(errors)}")
            if _NOT_STARTED_ERRORS.intersection(errors):
                raise GameNotStartedError(f"no game has started: {'; '.join(errors)}")
            raise ProtocolError(f"the game refused the request: {'; '.join(errors)}")
        if answer is not None and not response.HasField(answer):
            asked = response.WhichOneof("response") or "nothing"
            raise ProtocolError(f"the game was asked for {answer} and answered {asked}")
        return response
