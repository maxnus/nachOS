"""Playing a game, on a client this library starts or one a ladder has already started."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sc2nachos.api import Api
from sc2nachos.launch import GameProcess, Installation, Map
from sc2nachos.match import Computer, Participant, Player, Race, Result
from sc2nachos.protocol import Client, GamePorts, RecordingTransport, Transport, WebSocketTransport


@dataclass(frozen=True, slots=True)
class ApiBot:
    """A player driven by an api of ours, as which race and under what name.

    The other kind of player is a `Computer`, which the game drives itself and which needs no client.
    """

    api: Api
    race: Race
    name: str | None = None


def run_local(
    game_map: Map | str,
    players: Sequence[ApiBot | Computer],
    *,
    realtime: bool = False,
    time_limit: float | None = None,
    random_seed: int | None = None,
    record_to: Path | None = None,
    installation: Installation | None = None,
    window: tuple[int, int] = (1024, 768),
) -> Result:
    """Start a game client, create a match on `game_map` between `players`, and play it out.

    Exactly one player is an `ApiBot`, because one client plays one player. The client is stopped and its
    temporary directory removed however the game ends.
    """
    bot = _only_bot(players)
    if isinstance(game_map, str):
        installation = installation or Installation.find()
        game_map = Map.find(game_map, installation=installation)
    # A participant tells the game that a client will fill the slot; who fills it is settled at the join.
    setups: list[Player] = [Participant() if isinstance(player, ApiBot) else player for player in players]

    with GameProcess.launch(installation, window=window) as game:
        client = _connect(game.url, record_to)
        try:
            client.create_game(game_map.path, setups, realtime=realtime, random_seed=random_seed)
            client.join_game(bot.race, name=bot.name)
            return bot.api.play(client, realtime=realtime, time_limit=time_limit)
        finally:
            client.leave_game()
            client.quit()
            client.close()


def run_ladder(
    bot: ApiBot,
    *,
    host: str,
    port: int,
    start_port: int | None = None,
    realtime: bool = False,
    time_limit: float | None = None,
    record_to: Path | None = None,
) -> Result:
    """Join the game a ladder has already set up, and play it out.

    The ladder starts the client and creates the match, then hands the bot its address and `start_port` on the
    command line. A game against the built-in computer has no `start_port`, since nobody else is joining.
    """
    client = _connect(f"ws://{host}:{port}/sc2api", record_to)
    try:
        ports = GamePorts.from_start_port(start_port) if start_port is not None else None
        client.join_game(bot.race, name=bot.name, ports=ports)
        return bot.api.play(client, realtime=realtime, time_limit=time_limit)
    finally:
        # The ladder owns the client it started, so it is left running to be told what to do next.
        client.leave_game()
        client.close()


def _only_bot(players: Sequence[ApiBot | Computer]) -> ApiBot:
    """The player this process plays. Two of them would need a client each, which is not supported yet."""
    bots = [player for player in players if isinstance(player, ApiBot)]
    if len(bots) != 1:
        raise ValueError(f"one process plays exactly one bot, and {len(bots)} were given")
    return bots[0]


def _connect(url: str, record_to: Path | None) -> Client:
    """A client talking to the game at `url`, writing the whole conversation down if asked to."""
    transport: Transport = WebSocketTransport.connect(url)
    if record_to is not None:
        transport = RecordingTransport(transport, record_to)
    return Client(transport)
