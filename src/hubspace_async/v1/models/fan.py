from dataclasses import dataclass, field

from ..models import features
from .resource import ResourceTypes


@dataclass
class Fan:
    """Representation of a HubSpace Fan"""

    id: str
    on: features.OnFeature
    speed: features.SpeedFeature
    direction: features.DirectionFeature

    # Defined at initialization
    instances: dict = field(default_factory=lambda: dict(), repr=False, init=False)

    type: ResourceTypes = ResourceTypes.FAN

    def __init__(self, functions: list, **kwargs):
        for key, value in kwargs.items():
            if key == "instances":
                continue
            setattr(self, key, value)
        instances = {}
        for function in functions:
            try:
                if function["functionInstance"]:
                    instances[function["functionClass"]] = function["functionInstance"]
            except KeyError:
                continue
        self.instances = instances

    def get_instance(self, elem):
        """Lookup the instance associated with the elem"""
        return self.instances.get(elem, None)

    @property
    def supports_direction(self):
        return self.direction is not None

    @property
    def supports_speed(self):
        return self.speed is not None

    @property
    def is_on(self) -> bool:
        """Return bool if fan is currently powered on."""
        if self.on is not None:
            return self.on.on
        return False


@dataclass
class FanPut:
    """States that can be updated for a Fan"""

    on: features.OnFeature | None = None
    speed: features.SpeedFeature | None = None
    direction: features.DirectionFeature | None = None
