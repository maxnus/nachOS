"""Minerals and vespene, whatever they are being counted for."""

from __future__ import annotations

from dataclasses import dataclass
from typing import final


@final
@dataclass(frozen=True, slots=True)
class Resources:
    """An amount of minerals and vespene, whether spent, held, earned or averaged.

    Whole where the game gave it and where it has only been added up, fractional once it is scaled or divided.
    """

    minerals: float
    """Minerals."""
    vespene: float
    """Vespene."""

    @property
    def total(self) -> float:
        """Both added together, counting a unit of vespene the same as a unit of minerals."""
        return self.minerals + self.vespene

    def __add__(self, other: Resources) -> Resources:
        """Both amounts together."""
        return Resources(self.minerals + other.minerals, self.vespene + other.vespene)

    def __sub__(self, other: Resources) -> Resources:
        """What is left of this after `other`, which goes negative where there is not enough."""
        return Resources(self.minerals - other.minerals, self.vespene - other.vespene)

    def __neg__(self) -> Resources:
        """This much owed rather than held."""
        return Resources(-self.minerals, -self.vespene)

    def __mul__(self, factor: float) -> Resources:
        """This much `factor` times over."""
        return Resources(self.minerals * factor, self.vespene * factor)

    def __rmul__(self, factor: float) -> Resources:
        """This much `factor` times over."""
        return self * factor

    def __truediv__(self, divisor: float) -> Resources:
        """This much shared out `divisor` ways."""
        return Resources(self.minerals / divisor, self.vespene / divisor)

    def covers(self, other: Resources) -> bool:
        """Whether there is enough here for `other`, in both minerals and vespene."""
        return self.minerals >= other.minerals and self.vespene >= other.vespene
