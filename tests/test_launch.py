"""Finding and starting StarCraft II, without StarCraft II."""

import socket
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from sc2nachos.launch import (
    MINIMUM_BASE_BUILD,
    GameLaunchError,
    GameProcess,
    GameVersionError,
    Installation,
    InstallationNotFoundError,
    free_port,
)
from sc2nachos.launch._process import launch_command
from sc2nachos.protocol import Client, WebSocketTransport


def make_install(root: Path, *builds: int, maps: str = "Maps") -> Installation:
    """A directory tree shaped like an installation, holding `builds` and nothing real."""
    for build in builds:
        version = root / "Versions" / f"Base{build}"
        version.mkdir(parents=True)
        (version / "SC2_x64.exe").write_bytes(b"")
        (version / "SC2_x64").write_bytes(b"")
    (root / maps).mkdir(parents=True, exist_ok=True)
    return Installation(root)


@pytest.fixture
def sleeper() -> Iterator["subprocess.Popen[bytes]"]:
    """A process that outlives the test unless something stops it."""
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    yield process
    if process.poll() is None:
        process.kill()
        process.wait()


class TestFinding:
    def test_sc2path_wins(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SC2PATH", str(tmp_path))
        assert Installation.find(system="Windows").base == tmp_path

    def test_the_launchers_own_record_is_read(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A non-default install shows up in ExecuteInfo.txt, which the launcher rewrites as it runs."""
        home, install = tmp_path / "home", tmp_path / "games" / "StarCraft II"
        install.mkdir(parents=True)
        record = home / "Documents" / "StarCraft II" / "ExecuteInfo.txt"
        record.parent.mkdir(parents=True)
        record.write_text(f"executable = {install}\\Versions\\Base95841\\SC2_x64.exe\n", encoding="utf-8")

        monkeypatch.delenv("SC2PATH", raising=False)
        monkeypatch.setenv("USERPROFILE", str(home))
        monkeypatch.setenv("HOME", str(home))
        assert Installation.find(system="Windows").base == install

    def test_a_missing_installation_says_where_it_looked(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SC2PATH", raising=False)
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("HOME", str(tmp_path))
        with pytest.raises(InstallationNotFoundError, match="Applications"):
            Installation.find(system="Darwin")

    def test_an_unsupported_platform_is_named(self) -> None:
        with pytest.raises(InstallationNotFoundError, match="Java"):
            Installation.find(system="Java")


class TestVersions:
    def test_the_newest_build_is_the_default(self, tmp_path: Path) -> None:
        install = make_install(tmp_path, 75689, 95841, 93333)
        assert install.builds() == {75689, 93333, 95841}
        assert install.executable(system="Windows").parent.name == "Base95841"

    def test_a_build_can_be_asked_for(self, tmp_path: Path) -> None:
        install = make_install(tmp_path, 75689, 95841)
        assert install.executable(base_build=75689, system="Linux").parent.name == "Base75689"

    def test_an_absent_build_lists_what_is_there(self, tmp_path: Path) -> None:
        install = make_install(tmp_path, 95841)
        with pytest.raises(GameVersionError, match=r"95299 is not installed.*\[95841\]"):
            install.executable(base_build=95299, system="Windows")

    def test_a_build_older_than_the_raw_interface_is_refused(self, tmp_path: Path) -> None:
        install = make_install(tmp_path, MINIMUM_BASE_BUILD - 1)
        with pytest.raises(GameVersionError, match="raw interface"):
            install.executable(system="Windows")

    def test_an_installation_without_versions_is_not_one(self, tmp_path: Path) -> None:
        install = Installation(tmp_path)
        assert install.builds() == frozenset()
        with pytest.raises(GameVersionError, match="Base<build>"):
            install.executable(system="Windows")

    def test_directories_that_are_not_builds_are_ignored(self, tmp_path: Path) -> None:
        install = make_install(tmp_path, 95841)
        (tmp_path / "Versions" / "Shaders").mkdir()
        (tmp_path / "Versions" / "Base").mkdir()
        assert install.builds() == {95841}

    def test_the_executable_differs_by_platform(self, tmp_path: Path) -> None:
        install = make_install(tmp_path, 95841)
        assert install.executable(system="Windows").name == "SC2_x64.exe"
        assert install.executable(system="Linux").name == "SC2_x64"
        assert install.executable(system="Darwin").name == "SC2"


class TestLayout:
    def test_either_capitalization_of_the_map_directory_is_found(self, tmp_path: Path) -> None:
        """Blizzard's installers disagree about it, and only a case-sensitive filesystem cares."""
        assert make_install(tmp_path / "upper", 95841, maps="Maps").maps.is_dir()
        assert make_install(tmp_path / "lower", 95841, maps="maps").maps.is_dir()

    def test_only_windows_needs_a_working_directory(self, tmp_path: Path) -> None:
        install = Installation(tmp_path)
        assert install.working_directory(system="Windows") == tmp_path / "Support64"
        assert install.working_directory(system="Linux") is None
        assert install.working_directory(system="Darwin") is None


class TestCommand:
    def _command(self, **overrides: object) -> list[str]:
        arguments: dict = {
            "data_directory": Path("/sc2"),
            "temp_directory": Path("/tmp/x"),
            "host": "127.0.0.1",
            "port": 5000,
            "fullscreen": False,
            "window": (1024, 768),
            "window_position": None,
        }
        arguments.update(overrides)
        return launch_command(Path("/sc2/SC2_x64"), **arguments)

    def test_the_client_is_told_where_to_listen(self) -> None:
        command = self._command()
        assert command[0] == str(Path("/sc2/SC2_x64"))
        assert command[command.index("-listen") + 1] == "127.0.0.1"
        assert command[command.index("-port") + 1] == "5000"

    def test_a_windowed_game_carries_its_size(self) -> None:
        command = self._command(window=(800, 600))
        assert command[command.index("-displayMode") + 1] == "0"
        assert command[command.index("-windowwidth") + 1] == "800"
        assert command[command.index("-windowheight") + 1] == "600"

    def test_a_fullscreen_game_carries_no_window(self) -> None:
        command = self._command(fullscreen=True)
        assert command[command.index("-displayMode") + 1] == "1"
        assert "-windowwidth" not in command

    def test_a_window_position_is_optional(self) -> None:
        assert "-windowx" not in self._command()
        assert self._command(window_position=(20, 30))[-1] == "30"


class TestProcess:
    def test_a_free_port_is_free(self) -> None:
        port = free_port()
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", port))

    def test_terminating_stops_the_client_and_takes_its_directory(
        self, tmp_path: Path, sleeper: "subprocess.Popen[bytes]"
    ) -> None:
        temp_directory = tmp_path / "sc2nachos-test"
        temp_directory.mkdir()
        game = GameProcess(sleeper, url="ws://127.0.0.1:5000/sc2api", temp_directory=temp_directory)
        assert game.is_running
        game.terminate()
        assert not game.is_running
        assert not temp_directory.exists()

    def test_terminating_twice_is_not_an_error(self, tmp_path: Path, sleeper: "subprocess.Popen[bytes]") -> None:
        game = GameProcess(sleeper, url="ws://127.0.0.1:5000/sc2api", temp_directory=tmp_path / "gone")
        game.terminate()
        game.terminate()

    def test_the_context_manager_terminates(self, tmp_path: Path, sleeper: "subprocess.Popen[bytes]") -> None:
        with GameProcess(sleeper, url="ws://127.0.0.1:5000/sc2api", temp_directory=tmp_path / "gone") as game:
            assert game.is_running
        assert not game.is_running

    def test_waiting_returns_once_something_answers(self, tmp_path: Path, sleeper: "subprocess.Popen[bytes]") -> None:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            game = GameProcess(sleeper, url="ws://127.0.0.1/sc2api", temp_directory=tmp_path / "gone")
            game.wait_until_listening(host="127.0.0.1", port=port, timeout=5)
            game.terminate()

    def test_a_client_that_dies_is_not_waited_out(self, tmp_path: Path) -> None:
        process = subprocess.Popen([sys.executable, "-c", "raise SystemExit(3)"])
        game = GameProcess(process, url="ws://127.0.0.1:1/sc2api", temp_directory=tmp_path / "gone")
        with pytest.raises(GameLaunchError, match="exited with code 3"):
            game.wait_until_listening(host="127.0.0.1", port=free_port(), timeout=10)

    def test_a_client_that_never_listens_times_out(self, tmp_path: Path, sleeper: "subprocess.Popen[bytes]") -> None:
        game = GameProcess(sleeper, url="ws://127.0.0.1/sc2api", temp_directory=tmp_path / "gone")
        with pytest.raises(GameLaunchError, match="did not listen"):
            game.wait_until_listening(host="127.0.0.1", port=free_port(), timeout=0.5)
        game.terminate()


@pytest.mark.integration
class TestAgainstTheRealGame:
    """Run with `pytest -m integration`. Starts a client, so it is slow and needs the game installed."""

    def test_a_launched_client_answers(self) -> None:
        with GameProcess.launch(window=(640, 480)) as game:
            client = Client(WebSocketTransport.connect(game.url))
            ping = client.ping()
            assert ping.base_build >= MINIMUM_BASE_BUILD
            assert ping.game_version.endswith(str(ping.base_build))
            client.quit()
            client.close()
        assert not game.is_running
