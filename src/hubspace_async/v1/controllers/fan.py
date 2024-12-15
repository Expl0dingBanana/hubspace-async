"""Controller holding and managing HubSpace resources of type `fan`."""

from ... import device
from ..models import fan, features
from ..models.resource import ResourceTypes
from .base import BaseResourcesController


class FanController(BaseResourcesController[type[fan.Fan]]):
    """Controller holding and managing HubSpace resources of type `fan`."""

    ITEM_TYPE_ID = ResourceTypes.DEVICE
    ITEM_TYPE = ResourceTypes.FAN
    ITEM_CLS = fan.Fan
    ITEM_MAPPING = {
        "on": "power",
        "speed": "fan-speed",
        "direction": "fan-reverse",
    }
    ITEM_INSTANCE_MAPPING = {}

    async def turn_on(self, device_id: str) -> None:
        """Turn on the fan."""
        await self.set_state(device_id, on=True)

    async def turn_off(self, device_id: str) -> None:
        """Turn off the fan."""
        await self.set_state(device_id, on=False)

    async def set_speed(self, device_id: str, speed: int) -> None:
        """Set the speed of the fan, as a percentage."""
        await self.set_state(device_id, on=True, speed=speed)

    async def set_direction(self, device_id: str, forward: bool) -> None:
        """Set the direction of the fan to forward."""
        cur_item = await self.get_device(device_id)
        if not cur_item.is_on:
            # Thanks HubSpace for this one!
            self._logger.info("Fan is not running so direction will not be set")
        await self.set_state(device_id, forward=forward)

    async def initialize_elem(self, item: dict) -> None:
        """Initialize the element"""
        self._logger.info("Initializing %s", item["id"])
        hs_device = device.get_hs_device(item)
        on: features.OnFeature | None = None
        speed: features.SpeedFeature | None = None
        direction: features.DirectionFeature | None = None
        for state in hs_device.states:
            if state.functionClass == "power":
                on = features.OnFeature(on=state.value == "on")
            elif state.functionClass == "fan-speed":
                speeds = device.get_function_from_device(
                    hs_device, state.functionClass, state.functionInstance
                )
                tmp_speed = set()
                for value in speeds["values"]:
                    if not value["name"].endswith("-000"):
                        tmp_speed.add(value["name"])
                speed = features.SpeedFeature(
                    speed=state.value, speeds=list(sorted(tmp_speed))
                )
            elif state.functionClass == "fan-reverse":
                direction = features.DirectionFeature(forward=state.value == "forward")

        self._items[item["id"]] = fan.Fan(
            hs_device.functions,
            id=hs_device.id,
            on=on,
            speed=speed,
            direction=direction,
        )

    async def set_state(
        self,
        device_id: str,
        on: bool | None = None,
        speed: int | None = None,
        forward: bool | None = None,
    ) -> None:
        """Set supported feature(s) to fan resource."""
        update_obj = fan.FanPut()
        cur_item = await self.get_device(device_id)
        if on is not None:
            update_obj.on = features.OnFeature(on=on)
        if speed is not None:
            if speed == 0:
                update_obj.on = features.OnFeature(on=False)
            else:
                update_obj.speed = features.SpeedFeature(
                    speed=speed, speeds=cur_item.speed.speeds
                )
        if forward is not None:
            update_obj.direction = features.DirectionFeature(forward=forward)
        await self.update(device_id, update_obj)
