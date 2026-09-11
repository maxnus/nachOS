"""Geometry primitives in the game's coordinate space."""

from sc2nachos.geometry._area import Area
from sc2nachos.geometry._circle import Circle
from sc2nachos.geometry._grid import Grid, MutableGrid
from sc2nachos.geometry._path import TilePath
from sc2nachos.geometry._point import Point, Point3D, PointLike
from sc2nachos.geometry._shapes import Rectangle, Tile, TileSet

__all__ = [
    "Area",
    "Circle",
    "Grid",
    "MutableGrid",
    "Point",
    "Point3D",
    "PointLike",
    "Rectangle",
    "Tile",
    "TilePath",
    "TileSet",
]
