"""Scaffold tests: the package imports, and its dependencies are present and self-owned."""

import sc2nachos


def test_version_is_exposed() -> None:
    """The package exposes a version string."""
    assert isinstance(sc2nachos.__version__, str)
    assert sc2nachos.__version__


def test_protobuf_protocol_is_importable() -> None:
    """The s2clientprotocol bindings NachOS is built on are installed."""
    from s2clientprotocol import sc2api_pb2

    assert sc2api_pb2.Request is not None


def test_no_dependency_on_burnysc2() -> None:
    """NachOS must never import the library it replaces.

    AvocaDOS installs both during the migration, so an accidental import would otherwise go unnoticed until
    burnysc2 is finally removed.
    """
    import sys

    assert "sc2" not in sys.modules, "importing sc2nachos must not pull in burnysc2"
