"""NachOS — an event-driven StarCraft II bot API for Python."""

from sc2nachos.__about__ import __version__
from sc2nachos.api import Api, NotPlayingError
from sc2nachos.run import Bot, run_ladder, run_local

__all__ = ["Api", "Bot", "NotPlayingError", "__version__", "run_ladder", "run_local"]
