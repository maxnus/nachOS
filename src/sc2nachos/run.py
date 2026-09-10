"""Playing a game, on a client this library starts or one a ladder has already started."""

from contextlib import suppress
from pathlib import Path

from sc2nachos.api import Api
from sc2nachos.launch import GameProcess, Installation, Map
from sc2nachos.match import Computer, Participant, Race, Result
from sc2nachos.protocol import (
    Client,
    ConnectionClosedError,
    GamePorts,
    RecordingTransport,
    Transport,
    WebSocketTransport,
)


def run_local(
    api: Api,
    game_map: Map | str,
    opponent: Computer,
    *,
    race: Race,
    name: str | None = None,
    realtime: bool = False,
    time_limit: float | None = None,
    random_seed: int | None = None,
    record_to: Path | None = None,
    installation: Installation | None = None,
    window: tuple[int, int] = (1024, 768),
) -> Result:
    """Start a game client, create a match on `game_map` against `opponent`, and play it out.

    The client is stopped and its temporary directory removed however the game ends.
    """
    installation = installation or Installation.find()
    chosen = game_map if isinstance(game_map, Map) else Map.find(game_map, installation=installation)
    with GameProcess.launch(installation, window=window) as game:
        client = _connect(game.url, record_to)
        try:
            client.create_game(chosen.path, [Participant(), opponent], realtime=realtime, random_seed=random_seed)
            client.join_game(race, name=name)
            return api.play(client, realtime=realtime, time_limit=time_limit)
        finally:
            _hang_up(client, stop_the_client=True)


def run_ladder(
    api: Api,
    *,
    race: Race,
    host: str,
    port: int,
    start_port: int | None = None,
    name: str | None = None,
    realtime: bool = False,
    time_limit: float | None = None,
    record_to: Path | None = None,
) -> Result:
    """Join the game a ladder has already set up, and play it out.

    The ladder starts the client and creates the match, and hands its address and `start_port` to the bot on
    the command line. A game against the built-in computer has no `start_port`, since nobody else is joining.
    """
    client = _connect(f"ws://{host}:{port}/sc2api", record_to)
    try:
        ports = GamePorts.from_start_port(start_port) if start_port is not None else None
        client.join_game(race, name=name, ports=ports)
        return api.play(client, realtime=realtime, time_limit=time_limit)
    finally:
        # The ladder owns the client it started, so it is left running to be told what to do next.
        _hang_up(client, stop_the_client=False)


def _connect(url: str, record_to: Path | None) -> Client:
    """A client talking to the game at `url`, writing the whole conversation down if asked to."""
    transport: Transport = WebSocketTransport.connect(url)
    if record_to is not None:
        transport = RecordingTransport(transport, record_to)
    return Client(transport)


def _hang_up(client: Client, *, stop_the_client: bool) -> None:
    """Leave the game and let go of the connection, whatever state the game was left in."""
    with suppress(ConnectionClosedError):
        client.leave_game()
    if stop_the_client:
        client.quit()
    client.close()
