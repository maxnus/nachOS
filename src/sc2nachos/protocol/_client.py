"""The conversation the library holds with one game client."""

from collections.abc import Mapping, Sequence
from contextlib import suppress

from loguru import logger
from s2clientprotocol import sc2api_pb2

from sc2nachos.match import Race, Result
from sc2nachos.protocol._errors import ConnectionClosedError, GameEndedError, ProtocolError
from sc2nachos.protocol._ports import GamePorts
from sc2nachos.protocol._status import Status
from sc2nachos.protocol._transport import Transport

# What the game says when it is asked for something only a running game can give.
_GAME_OVER_ERRORS = frozenset({"Game has already ended", "Not supported if game has already ended"})


def _wrong_answer(field: str) -> ProtocolError:
    """The error for a response that does not carry what its request asked for.

    Each caller spells the field name out so that the protobuf stubs check it.
    """
    return ProtocolError(f"the game answered a {field} request without a {field} field")


class Client:
    """A game client, addressed over a transport.

    Every method is one request, and blocks until the game answers it. The protocol carries one request at
    a time with no way to match an answer to anything but the last question, so there is nothing to overlap.

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
    def results(self) -> Mapping[int, Result]:
        """How the game ended, by player id. Empty until it does."""
        return self._results

    def ping(self) -> sc2api_pb2.ResponsePing:
        """Ask the game which version it is, which also proves the connection works."""
        response = self._send(sc2api_pb2.Request(ping=sc2api_pb2.RequestPing()))
        if not response.HasField("ping"):
            raise _wrong_answer("ping")
        return response.ping

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
            request.server_ports.game_port, request.server_ports.base_port = ports.server
            for game_port, base_port in ports.players:
                request.client_ports.add(game_port=game_port, base_port=base_port)

        response = self._send(sc2api_pb2.Request(join_game=request))
        if not response.HasField("join_game"):
            raise _wrong_answer("join_game")
        joined = response.join_game
        # An unset error field reads as the first refusal the proto declares, so ask before reading it.
        if joined.HasField("error"):
            reason = sc2api_pb2.ResponseJoinGame.Error.Name(joined.error)
            detail = joined.error_details or "no detail given"
            raise ProtocolError(f"the game refused the join as {reason}: {detail}")
        self._player_id = joined.player_id
        self._results = {}
        logger.info("Joined the game as player {} playing {}", joined.player_id, race)
        return joined.player_id

    def game_info(self) -> sc2api_pb2.ResponseGameInfo:
        """The map: its size, its terrain, its start locations and the players in it."""
        response = self._send(sc2api_pb2.Request(game_info=sc2api_pb2.RequestGameInfo()))
        if not response.HasField("game_info"):
            raise _wrong_answer("game_info")
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
        """The static tables behind the ids: costs, ranges, requirements and names."""
        request = sc2api_pb2.RequestData(
            ability_id=abilities,
            unit_type_id=unit_types,
            upgrade_id=upgrades,
            buff_id=buffs,
            effect_id=effects,
        )
        response = self._send(sc2api_pb2.Request(data=request))
        if not response.HasField("data"):
            raise _wrong_answer("data")
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
        """Let the game run `count` frames. Only a stepped game needs this; a realtime one runs on its own."""
        response = self._send(sc2api_pb2.Request(step=sc2api_pb2.RequestStep(count=count)))
        if not response.HasField("step"):
            raise _wrong_answer("step")
        return response.step

    def act(self, actions: Sequence[sc2api_pb2.Action]) -> sc2api_pb2.ResponseAction:
        """Send `actions`, and get back the game's verdict on each one in the order they were given."""
        response = self._send(sc2api_pb2.Request(action=sc2api_pb2.RequestAction(actions=actions)))
        if not response.HasField("action"):
            raise _wrong_answer("action")
        return response.action

    def save_replay(self) -> bytes:
        """The replay of the game so far, as the bytes of a `.SC2Replay` file."""
        response = self._send(sc2api_pb2.Request(save_replay=sc2api_pb2.RequestSaveReplay()))
        if not response.HasField("save_replay"):
            raise _wrong_answer("save_replay")
        return response.save_replay.data

    def leave_game(self) -> None:
        """Leave the game, which concedes it if it has not already ended."""
        self._send(sc2api_pb2.Request(leave_game=sc2api_pb2.RequestLeaveGame()))

    def quit(self) -> None:
        """Ask the game client to exit. A connection that has already gone is not an error here."""
        with suppress(ConnectionClosedError):
            self._send(sc2api_pb2.Request(quit=sc2api_pb2.RequestQuit()))

    def close(self) -> None:
        """Release the transport."""
        self._transport.close()

    def _observe(self, game_loop: int | None) -> sc2api_pb2.ResponseObservation:
        request = sc2api_pb2.RequestObservation()
        if game_loop is not None:
            request.game_loop = game_loop
        response = self._send(sc2api_pb2.Request(observation=request))
        if not response.HasField("observation"):
            raise _wrong_answer("observation")
        return response.observation

    def _send(self, request: sc2api_pb2.Request) -> sc2api_pb2.Response:
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
            raise ProtocolError(f"the game refused the request: {'; '.join(errors)}")
        return response
