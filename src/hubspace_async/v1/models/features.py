"""Feature Schemas used by various HubSpace resources."""

from dataclasses import dataclass

from ..util import percentage_to_ordered_list_item


@dataclass
class ColorModeFeature:
    """Represent the current mode (ie white, color) Feature object"""

    mode: str

    @property
    def hs_value(self):
        return self.mode


@dataclass
class ColorFeature:
    """Represent `RGB` Feature object"""

    red: int
    green: int
    blue: int

    @property
    def hs_value(self):
        return {
            "value": {
                "color-rgb": {
                    "r": self.red,
                    "g": self.green,
                    "b": self.blue,
                }
            }
        }


@dataclass
class ColorTemperatureFeature:
    """Represent Current temperature Feature"""

    temperature: int
    supported: list[int]
    prefix: str | None = None

    @property
    def hs_value(self):
        return f"{self.temperature}{self.prefix}"


@dataclass
class DimmingFeature:
    """Represent Current temperature Feature"""

    brightness: int
    supported: list[int]

    @property
    def hs_value(self):
        return self.brightness


@dataclass
class DirectionFeature:
    """Represent Current Fan direction Feature"""

    forward: bool

    @property
    def hs_value(self):
        return "forward" if self.forward else "reverse"


@dataclass
class EffectFeature:
    """Represent the current effect"""

    effect: str
    effects: dict[str, set[str]]

    @property
    def hs_value(self):
        val = {
            "value": self.effect,
            "functionInstance": "preset",
        }
        for instance, items in self.effects.items():
            if self.effect in items:
                val["functionInstance"] = instance
                break
        return val


@dataclass
class ModeFeature:
    """Represent Current Fan mode Feature"""

    mode: str | None
    modes: set[str]

    @property
    def hs_value(self):
        return self.mode


@dataclass
class OnFeature:
    """Represent `On` Feature object as used by various HubSpace resources."""

    on: bool

    @property
    def hs_value(self):
        return "on" if self.on else "off"


@dataclass
class SpeedFeature:
    """Represent Current Fan speed Feature"""

    speed: int
    speeds: list[str]

    @property
    def hs_value(self):
        return percentage_to_ordered_list_item(self.speeds, self.speed)
