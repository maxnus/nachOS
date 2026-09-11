"""The recorded games everything above the protocol is tested against, and what they have to hold."""

from pathlib import Path

import pytest
from s2clientprotocol import sc2api_pb2

from sc2nachos import Api
from sc2nachos.match import Computer, Participant, Race, Result
from sc2nachos.protocol import Client, Recording, ReplayTransport

# Recorded by `tools/record_corpus.py`, which says what each game is.
CORPUS = sorted((Path(__file__).parent / "corpus").glob("*.sc2rec"))


def _observations(recording: Recording) -> list[sc2api_pb2.ResponseObservation]:
    """Every observation in `recording`, in the order the game made them."""
    return [exchange.response.observation for exchange in recording if exchange.response.HasField("observation")]


def test_there_is_a_corpus() -> None:
    assert CORPUS, "tests/corpus holds no recordings, so nothing below ran"


@pytest.mark.parametrize("path", CORPUS, ids=lambda path: path.stem)
def test_a_recorded_game_replays_to_its_end_asking_what_it_asked(path: Path) -> None:
    """A change to what the library asks a game, or in what order, shows up here as a question unanswered."""
    recording = Recording(path)
    last = _observations(recording)[-1]
    client = Client(ReplayTransport(recording))
    # A recording answers each kind of request in turn and never reads what was asked, so the setup is asked again
    # without its details.
    client.create_game("recorded", [Participant(), Computer()])
    player = client.join_game(Race.RANDOM)

    api = Api()
    result = api.play(client)

    assert api.step == last.observation.game_loop
    assert result is {entry.player_id: Result(entry.result) for entry in last.player_result}[player]
    client.leave_game()
    client.quit()

