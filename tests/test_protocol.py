"""The protocol layer, driven entirely through the transport seam."""

import lzma
from collections import deque
from pathlib import Path
from typing import Any, cast

import pytest
from s2clientprotocol import error_pb2, raw_pb2, sc2api_pb2
from websocket import WebSocket, WebSocketConnectionClosedException, WebSocketTimeoutException

from sc2nachos.match import AIBuild, Computer, Difficulty, Participant, Race, Result
from sc2nachos.protocol import (
    Client,
    ConnectionClosedError,
    ConnectionTimeoutError,
    GameEndedError,
    GamePorts,
    PortPair,
    ProtocolError,
    Recording,
    RecordingTransport,
    ReplayTransport,
    Status,
    WebSocketTransport,
)


class FakeTransport:
    """A `Transport` that answers from a prepared queue and remembers what it was asked."""

    def __init__(self, *responses: sc2api_pb2.Response) -> None:
        self.requests: list[sc2api_pb2.Request] = []
        self.closed = False
        self._responses = deque(responses)

    def request(self, request: sc2api_pb2.Request) -> sc2api_pb2.Response:
        self.requests.append(request)
        if not self._responses:
            raise AssertionError("the client asked more of the transport than the test prepared")
        return self._responses.popleft()

    def close(self) -> None:
        self.closed = True


class FakeWebSocket:
    """The three methods `WebSocketTransport` uses, over a prepared queue of payloads."""

    def __init__(self, *payloads: str | bytes, timeout: bool = False) -> None:
        self.sent: list[bytes] = []
        self.closed = False
        self._payloads: deque[str | bytes] = deque(payloads)
        self._timeout = timeout

    def send_binary(self, payload: bytes) -> int:
        if self.closed:
            raise WebSocketConnectionClosedException("socket is already closed.")
        self.sent.append(payload)
        return len(payload)

    def recv(self) -> str | bytes:
        if self._timeout:
            raise WebSocketTimeoutException("timed out")
        if not self._payloads:
            raise WebSocketConnectionClosedException("Connection to remote host was lost.")
        return self._payloads.popleft()

    def close(self) -> None:
        self.closed = True


def _response(status: Status | None = Status.IN_GAME, **fields: Any) -> sc2api_pb2.Response:
    """A response carrying `fields`, and `status` unless it is given as `None`."""
    response = sc2api_pb2.Response(**fields)
    if status is not None:
        response.status = status.value
    return response


def _observation(*results: tuple[int, Result]) -> sc2api_pb2.ResponseObservation:
    return sc2api_pb2.ResponseObservation(
        player_result=[sc2api_pb2.PlayerResult(player_id=player, result=result.value) for player, result in results]
    )


def _client(*responses: sc2api_pb2.Response) -> tuple[Client, FakeTransport]:
    transport = FakeTransport(*responses)
    return Client(transport), transport


class TestStatus:
    def test_the_client_reports_what_the_game_last_said(self) -> None:
        client, _ = _client(_response(Status.INIT_GAME, ping=sc2api_pb2.ResponsePing()))
        assert client.status is None
        client.ping()
        assert client.status is Status.INIT_GAME

    def test_a_response_without_a_status_leaves_the_last_one_standing(self) -> None:
        """An unset status field reads as `launched`, so reading it blind would walk the status backwards."""
        client, _ = _client(
            _response(Status.IN_GAME, ping=sc2api_pb2.ResponsePing()),
            _response(None, ping=sc2api_pb2.ResponsePing()),
        )
        client.ping()
        client.ping()
        assert client.status is Status.IN_GAME

    def test_in_game_covers_playing_and_watching(self) -> None:
        for status, expected in [
            (Status.IN_GAME, True),
            (Status.IN_REPLAY, True),
            (Status.INIT_GAME, False),
            (Status.ENDED, False),
        ]:
            client, _ = _client(_response(status, ping=sc2api_pb2.ResponsePing()))
            client.ping()
            assert client.in_game is expected, status


class TestErrors:
    def test_a_refused_request_raises(self) -> None:
        client, _ = _client(_response(error=["Doh!"], ping=sc2api_pb2.ResponsePing()))
        with pytest.raises(ProtocolError, match="Doh!"):
            client.ping()

    def test_a_finished_game_raises_its_own_error(self) -> None:
        client, _ = _client(_response(Status.ENDED, error=["Game has already ended"]))
        with pytest.raises(GameEndedError):
            client.ping()

    def test_every_failure_is_a_protocol_error(self) -> None:
        for error in (GameEndedError, ConnectionClosedError, ConnectionTimeoutError):
            assert issubclass(error, ProtocolError)

    def test_an_answer_to_a_different_question_names_both(self) -> None:
        client, _ = _client(_response(ping=sc2api_pb2.ResponsePing()))
        with pytest.raises(ProtocolError, match="asked for game_info and answered ping"):
            client.game_info()

    def test_a_response_carrying_no_answer_at_all_says_so(self) -> None:
        client, _ = _client(_response())
        with pytest.raises(ProtocolError, match="asked for ping and answered nothing"):
            client.ping()


class TestJoining:
    def test_the_join_asks_for_the_raw_interface_only(self) -> None:
        client, transport = _client(_response(join_game=sc2api_pb2.ResponseJoinGame(player_id=2)))
        assert client.join_game(Race.TERRAN) == 2
        assert client.player_id == 2
        options = transport.requests[0].join_game.options
        assert options.raw and options.score
        assert not options.HasField("render") and not options.HasField("feature_layer")

    def test_a_name_and_ports_reach_the_request(self) -> None:
        client, transport = _client(_response(join_game=sc2api_pb2.ResponseJoinGame(player_id=1)))
        client.join_game(Race.ZERG, name="AvocaDOS", ports=GamePorts.from_start_port(1000))
        request = transport.requests[0].join_game
        assert request.race == Race.ZERG.value
        assert request.player_name == "AvocaDOS"
        assert (request.server_ports.game_port, request.server_ports.base_port) == (1002, 1003)
        assert [(port.game_port, port.base_port) for port in request.client_ports] == [(1004, 1005)]

    def test_a_refused_join_raises_even_without_a_top_level_error(self) -> None:
        refusal = sc2api_pb2.ResponseJoinGame(
            error=sc2api_pb2.ResponseJoinGame.MissingParticipation, error_details="no slot"
        )
        client, _ = _client(_response(join_game=refusal))
        with pytest.raises(ProtocolError, match="MissingParticipation.*no slot"):
            client.join_game(Race.PROTOSS)


class TestObservation:
    def test_a_running_game_answers_in_one_request(self) -> None:
        client, transport = _client(
            _response(ping=sc2api_pb2.ResponsePing()),
            _response(observation=sc2api_pb2.ResponseObservation()),
        )
        client.ping()
        client.observation()
        assert len(transport.requests) == 2
        assert client.results == {}

    def test_a_requested_game_loop_reaches_the_request(self) -> None:
        client, transport = _client(_response(observation=sc2api_pb2.ResponseObservation()))
        client.observation(game_loop=448)
        assert transport.requests[0].observation.game_loop == 448

    def test_the_results_land_when_the_game_ends(self) -> None:
        ended = _observation((1, Result.VICTORY), (2, Result.DEFEAT))
        client, _ = _client(_response(Status.ENDED, observation=ended))
        client.observation()
        assert client.results == {1: Result.VICTORY, 2: Result.DEFEAT}

    def test_a_game_that_ends_a_step_early_costs_one_more_request(self) -> None:
        """The game reports itself ended a step before it will say who won."""
        client, transport = _client(
            _response(Status.ENDED, observation=sc2api_pb2.ResponseObservation()),
            _response(Status.ENDED, observation=_observation((1, Result.DEFEAT))),
        )
        client.observation()
        assert len(transport.requests) == 2
        assert client.results == {1: Result.DEFEAT}

    def test_joining_clears_the_results_of_the_last_game(self) -> None:
        client, _ = _client(
            _response(Status.ENDED, observation=_observation((1, Result.VICTORY))),
            _response(Status.IN_GAME, join_game=sc2api_pb2.ResponseJoinGame(player_id=1)),
        )
        client.observation()
        client.join_game(Race.TERRAN)
        assert client.results == {}


class TestRequests:
    def test_step_asks_for_a_count_of_frames(self) -> None:
        client, transport = _client(_response(step=sc2api_pb2.ResponseStep(simulation_loop=112)))
        assert client.step(4).simulation_loop == 112
        assert transport.requests[0].step.count == 4

    def test_act_returns_a_verdict_per_action(self) -> None:
        actions = [sc2api_pb2.Action(), sc2api_pb2.Action()]
        client, transport = _client(_response(action=sc2api_pb2.ResponseAction(result=[error_pb2.Success] * 2)))
        assert len(client.act(actions).result) == 2
        assert len(transport.requests[0].action.actions) == 2

    def test_game_data_asks_for_every_table_by_default(self) -> None:
        client, transport = _client(_response(data=sc2api_pb2.ResponseData()))
        client.game_data()
        request = transport.requests[0].data
        assert (request.ability_id, request.unit_type_id, request.upgrade_id, request.buff_id, request.effect_id) == (
            True,
            True,
            True,
            True,
            True,
        )

    def test_a_replay_comes_back_as_bytes(self) -> None:
        client, _ = _client(_response(save_replay=sc2api_pb2.ResponseSaveReplay(data=b"replay")))
        assert client.save_replay() == b"replay"

    def test_quit_forgives_a_connection_that_has_already_gone(self) -> None:
        class ClosedTransport:
            def request(self, request: sc2api_pb2.Request) -> sc2api_pb2.Response:
                raise ConnectionClosedError("gone")

            def close(self) -> None: ...

        Client(ClosedTransport()).quit()

    def test_closing_the_client_releases_the_transport(self) -> None:
        client, transport = _client()
        client.close()
        assert transport.closed


class TestWebSocketTransport:
    def _transport(self, websocket: FakeWebSocket) -> WebSocketTransport:
        return WebSocketTransport(cast(WebSocket, websocket))

    def test_a_request_goes_out_serialized_and_the_answer_comes_back_parsed(self) -> None:
        answer = _response(ping=sc2api_pb2.ResponsePing(base_build=93333))
        websocket = FakeWebSocket(answer.SerializeToString())
        response = self._transport(websocket).request(sc2api_pb2.Request(ping=sc2api_pb2.RequestPing()))
        assert response.ping.base_build == 93333
        assert sc2api_pb2.Request.FromString(websocket.sent[0]).HasField("ping")

    def test_a_closed_socket_fails_the_send(self) -> None:
        websocket = FakeWebSocket()
        websocket.close()
        with pytest.raises(ConnectionClosedError):
            self._transport(websocket).request(sc2api_pb2.Request(ping=sc2api_pb2.RequestPing()))

    def test_a_socket_that_closes_mid_request_fails_the_receive(self) -> None:
        websocket = FakeWebSocket()
        with pytest.raises(ConnectionClosedError):
            self._transport(websocket).request(sc2api_pb2.Request(ping=sc2api_pb2.RequestPing()))

    def test_a_game_that_never_answers_raises_a_timeout(self) -> None:
        websocket = FakeWebSocket(timeout=True)
        with pytest.raises(ConnectionTimeoutError):
            self._transport(websocket).request(sc2api_pb2.Request(ping=sc2api_pb2.RequestPing()))

    def test_a_text_frame_is_not_a_response(self) -> None:
        """The protocol is binary throughout, so text is the game or a proxy saying something went wrong."""
        websocket = FakeWebSocket("Bad Request")
        with pytest.raises(ProtocolError, match="text where the protocol is binary"):
            self._transport(websocket).request(sc2api_pb2.Request(ping=sc2api_pb2.RequestPing()))

    def test_closing_closes_the_socket(self) -> None:
        websocket = FakeWebSocket()
        self._transport(websocket).close()
        assert websocket.closed


class TestGamePorts:
    def test_the_ladder_layout_skips_the_first_port(self) -> None:
        assert GamePorts.from_start_port(5000) == GamePorts(
            server=PortPair(5002, 5003), players=(PortPair(5004, 5005),)
        )


class TestCreatingAGame:
    def test_the_map_and_the_players_reach_the_request(self) -> None:
        client, transport = _client(_response(create_game=sc2api_pb2.ResponseCreateGame()))
        client.create_game(Path("/sc2/Maps/PylonAIE.SC2Map"), [Participant(), Computer()])
        request = transport.requests[0].create_game
        assert request.local_map.map_path.endswith("PylonAIE.SC2Map")
        assert [setup.type for setup in request.player_setup] == [sc2api_pb2.Participant, sc2api_pb2.Computer]

    def test_a_participant_says_nothing_about_itself(self) -> None:
        """The race and the name are settled at the join, and the game ignores them here."""
        client, transport = _client(_response(create_game=sc2api_pb2.ResponseCreateGame()))
        client.create_game("map", [Participant()])
        setup = transport.requests[0].create_game.player_setup[0]
        assert not setup.HasField("race") and not setup.HasField("player_name")

    def test_a_computer_carries_how_it_plays(self) -> None:
        client, transport = _client(_response(create_game=sc2api_pb2.ResponseCreateGame()))
        opponent = Computer(race=Race.ZERG, difficulty=Difficulty.HARD, build=AIBuild.RUSH, name="Roachy")
        client.create_game("map", [Participant(), opponent])
        setup = transport.requests[0].create_game.player_setup[1]
        assert (setup.race, setup.difficulty, setup.ai_build) == (
            Race.ZERG.value,
            Difficulty.HARD.value,
            AIBuild.RUSH.value,
        )
        assert setup.player_name == "Roachy"

    def test_an_unnamed_computer_keeps_the_name_the_game_gives_it(self) -> None:
        client, transport = _client(_response(create_game=sc2api_pb2.ResponseCreateGame()))
        client.create_game("map", [Computer()])
        assert not transport.requests[0].create_game.player_setup[0].HasField("player_name")

    def test_the_game_settings_reach_the_request(self) -> None:
        client, transport = _client(_response(create_game=sc2api_pb2.ResponseCreateGame()))
        client.create_game("map", [Participant()], realtime=True, disable_fog=True, random_seed=7)
        request = transport.requests[0].create_game
        assert request.realtime and request.disable_fog
        assert request.random_seed == 7

    def test_no_seed_asked_for_leaves_the_game_to_pick_one(self) -> None:
        """Zero is a seed like any other, so an unset field is the only way to say `any`."""
        client, transport = _client(_response(create_game=sc2api_pb2.ResponseCreateGame()))
        client.create_game("map", [Participant()])
        assert not transport.requests[0].create_game.HasField("random_seed")

    def test_a_refused_creation_raises_even_without_a_top_level_error(self) -> None:
        refusal = sc2api_pb2.ResponseCreateGame(
            error=sc2api_pb2.ResponseCreateGame.InvalidMapPath, error_details="no such map"
        )
        client, _ = _client(_response(create_game=refusal))
        with pytest.raises(ProtocolError, match="InvalidMapPath.*no such map"):
            client.create_game("map", [Participant()])

    def test_a_creation_the_game_did_not_answer_raises(self) -> None:
        """An unset create_game field would otherwise read as a refusal-free success."""
        client, _ = _client(_response(ping=sc2api_pb2.ResponsePing()))
        with pytest.raises(ProtocolError, match="asked for create_game and answered ping"):
            client.create_game("map", [Participant()])


class _BrokenTransport:
    """A `Transport` that never gets an answer."""

    def request(self, request: sc2api_pb2.Request) -> sc2api_pb2.Response:
        raise ConnectionClosedError("the connection to the game closed mid-request")

    def close(self) -> None:
        pass


def _recorder(path: Path, *responses: sc2api_pb2.Response) -> RecordingTransport:
    """A recorder into `path`, over a game that will answer `responses`."""
    return RecordingTransport(FakeTransport(*responses), path)


_VERSION = _response(ping=sc2api_pb2.ResponsePing(game_version="5.0.14." + "0" * 100))


class TestRecording:
    def test_a_whole_exchange_survives_the_round_trip(self, tmp_path: Path) -> None:
        recorder = _recorder(tmp_path / "game.sc2rec", _VERSION)
        Client(recorder).ping()
        recorder.close()

        (exchange,) = list(recorder.recording)
        assert exchange.request.HasField("ping")
        assert exchange.response.ping.game_version == _VERSION.ping.game_version

    def test_a_recording_can_be_read_again(self, tmp_path: Path) -> None:
        """Reading re-opens the file, so a corpus serves any number of tests."""
        recorder = _recorder(tmp_path / "game.sc2rec", _VERSION)
        Client(recorder).ping()
        recorder.close()
        assert list(recorder.recording) == list(recorder.recording)

    def test_a_recording_is_far_smaller_than_the_game_it_holds(self, tmp_path: Path) -> None:
        """Committing a corpus is only affordable because consecutive observations barely differ."""
        path = tmp_path / "game.sc2rec"
        crowd = [raw_pb2.Unit(tag=index, unit_type=48, health=45.0) for index in range(500)]
        answers = [
            _response(
                observation=sc2api_pb2.ResponseObservation(
                    observation=sc2api_pb2.Observation(game_loop=loop, raw_data=raw_pb2.ObservationRaw(units=crowd))
                )
            )
            for loop in range(200)
        ]
        recorder = _recorder(path, *answers)
        client = Client(recorder)
        for _ in answers:
            client.observation()
        recorder.close()

        raw = sum(len(answer.SerializeToString()) for answer in answers)
        assert raw > 1_000_000
        assert path.stat().st_size < raw // 20

    def test_a_request_the_game_never_answered_is_not_recorded(self, tmp_path: Path) -> None:
        recorder = RecordingTransport(_BrokenTransport(), tmp_path / "game.sc2rec")
        with pytest.raises(ConnectionClosedError):
            recorder.request(sc2api_pb2.Request(ping=sc2api_pb2.RequestPing()))
        recorder.close()
        assert list(recorder.recording) == []

    def test_closing_closes_the_transport_underneath_and_may_be_repeated(self, tmp_path: Path) -> None:
        game = FakeTransport()
        recorder = RecordingTransport(game, tmp_path / "game.sc2rec")
        recorder.close()
        recorder.close()
        assert game.closed

    def test_a_file_that_is_not_a_recording_says_so(self, tmp_path: Path) -> None:
        path = tmp_path / "junk.sc2rec"
        path.write_bytes(lzma.compress(b"whatever this file is, it is not one of ours"))
        with pytest.raises(ProtocolError, match="not a recording"):
            list(Recording(path))

    def test_a_recording_cut_short_says_so(self, tmp_path: Path) -> None:
        path = _truncated(tmp_path, cut=5)
        with pytest.raises(ProtocolError, match="short of a Response"):
            list(Recording(path))

    def test_a_recording_ending_on_an_unanswered_request_says_so(self, tmp_path: Path) -> None:
        path = _truncated(tmp_path, cut=len(_VERSION.SerializeToString()) + 4)
        with pytest.raises(ProtocolError, match="never answered"):
            list(Recording(path))


def _truncated(tmp_path: Path, *, cut: int) -> Path:
    """A recording of one exchange with its last `cut` bytes lost, as a run killed mid-write would leave it."""
    path = tmp_path / "game.sc2rec"
    recorder = _recorder(path, _VERSION)
    Client(recorder).ping()
    recorder.close()
    path.write_bytes(lzma.compress(lzma.decompress(path.read_bytes())[:-cut]))
    return path


class TestReplay:
    def _recorded(self, tmp_path: Path) -> Recording:
        """A game created, joined and observed once, as a recording."""
        recorder = _recorder(
            tmp_path / "game.sc2rec",
            _response(create_game=sc2api_pb2.ResponseCreateGame()),
            _response(join_game=sc2api_pb2.ResponseJoinGame(player_id=2)),
            _response(observation=sc2api_pb2.ResponseObservation(observation=sc2api_pb2.Observation(game_loop=48))),
        )
        client = Client(recorder)
        client.create_game("map", [Participant(), Computer()])
        client.join_game(Race.TERRAN)
        client.observation()
        client.close()
        return recorder.recording

    def test_a_recorded_conversation_drives_a_client_with_no_game(self, tmp_path: Path) -> None:
        client = Client(ReplayTransport(self._recorded(tmp_path)))
        client.create_game("map", [Participant(), Computer()])
        assert client.join_game(Race.TERRAN) == 2
        assert client.observation().observation.game_loop == 48

    def test_the_details_of_a_request_need_not_match(self, tmp_path: Path) -> None:
        """Only the question is replayed, so a caller may ask about a loop the recording did not."""
        client = Client(ReplayTransport(self._recorded(tmp_path)))
        client.create_game("other map", [Computer()])
        assert client.join_game(Race.ZERG, name="someone else") == 2

    def test_a_question_the_recording_was_not_asked_raises(self, tmp_path: Path) -> None:
        client = Client(ReplayTransport(self._recorded(tmp_path)))
        with pytest.raises(ProtocolError, match="answers create_game next, and was asked for ping"):
            client.ping()

    def test_a_recording_that_has_run_out_says_so(self, tmp_path: Path) -> None:
        client = Client(ReplayTransport(self._recorded(tmp_path)))
        client.create_game("map", [Participant(), Computer()])
        client.join_game(Race.TERRAN)
        client.observation()
        with pytest.raises(ProtocolError, match="no answer left, and was asked for ping"):
            client.ping()

    def test_a_request_after_closing_raises(self, tmp_path: Path) -> None:
        transport = ReplayTransport(self._recorded(tmp_path))
        transport.close()
        with pytest.raises(ConnectionClosedError):
            transport.request(sc2api_pb2.Request(ping=sc2api_pb2.RequestPing()))
