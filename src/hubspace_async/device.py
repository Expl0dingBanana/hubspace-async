__all__ = [
    "HubSpaceDevice",
    "HubSpaceState",
    "get_hs_device",
]
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class HubSpaceState:
    """State of a given function

    :param functionClass: Function class for the state (ie, power)
    :param value: Value to set for the function_class
    :param lastUpdateTime: Last time the state was updated (in epoch ms).
    :param functionInstance: Additional information about the function (ie, light-power).
        Default: None
    """

    functionClass: str
    value: Any
    lastUpdateTime: Optional[int] = None
    functionInstance: Optional[str] = None


@dataclass
class HubSpaceDevice:
    id: str
    device_id: str
    model: str
    device_class: str
    default_name: str
    default_image: str
    friendly_name: str
    functions: list[dict] = field(default=list)
    states: list[HubSpaceState] = field(default=list)
    children: list[str] = field(default=list)
    manufacturerName: Optional[str] = field(default=None)

    def __hash__(self):
        return hash((self.id, self.friendly_name))

    def __post_init__(self):
        if not self.model and self.default_image == "ceiling-fan-snyder-park-icon":
            self.model = "DriskolFan"
        if not self.model and self.default_image == "ceiling-fan-vinings-icon":
            self.model = "VinwoodFan"
        if (
            self.device_class == "fan"
            and self.model == "TBD"
            and self.default_image == "ceiling-fan-chandra-icon"
        ):
            self.model = "ZandraFan"
        if (
            self.model == "TBD"
            and self.default_image == "ceiling-fan-ac-cct-dardanus-icon"
        ):
            self.model = "NevaliFan"
        if (
            self.device_class == "fan"
            and not self.model
            and self.default_image == "ceiling-fan-slender-icon"
        ):
            self.model = "TagerFan"
        if self.model == "Smart Stake Timer":
            self.model = "YardStake"
        if self.default_image == "a19-e26-color-cct-60w-smd-frosted-icon":
            self.model = "12A19060WRGBWH2"


def get_hs_device(hs_device: dict[str, Any]) -> HubSpaceDevice:
    """Convert the HubSpace device definition into a HubSpaceDevice"""
    description = hs_device.get("description", {})
    device = description.get("device", {})
    processed_states: list[HubSpaceState] = []
    for state in hs_device.get("state", {}).get("values", []):
        processed_states.append(
            HubSpaceState(
                functionClass=state.get("functionClass"),
                value=state.get("value"),
                lastUpdateTime=state.get("lastUpdateTime"),
                functionInstance=state.get("functionInstance"),
            )
        )
    dev_dict = {
        "id": hs_device.get("id"),
        "device_id": hs_device.get("deviceId"),
        "model": device.get("model"),
        "device_class": device.get("deviceClass"),
        "default_name": device.get("defaultName"),
        "default_image": description.get("defaultImage"),
        "friendly_name": hs_device.get("friendlyName"),
        "functions": description.get("functions", []),
        "states": processed_states,
        "children": hs_device.get("children", []),
        "manufacturerName": device.get("manufacturerName"),
    }
    return HubSpaceDevice(**dev_dict)


def get_function_from_device(
    hs_device: HubSpaceDevice, function_class: str, function_instance
) -> dict:
    for func in hs_device.functions:
        if func.get("functionClass") != function_class:
            continue
        if func.get("functionInstance") != function_instance:
            continue
        return func
    return None
