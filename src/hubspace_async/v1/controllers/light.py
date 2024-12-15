"""Controller holding and managing HubSpace resources of type `light`."""

from ... import device
from ..models import features, light
from ..models.resource import ResourceTypes
from ..util import process_names, process_range
from .base import BaseResourcesController


class LightController(BaseResourcesController[type[light.Light]]):
    """Controller holding and managing HubSpace resources of type `fan`."""

    ITEM_TYPE_ID = ResourceTypes.DEVICE
    ITEM_TYPE = ResourceTypes.LIGHT
    ITEM_CLS = light.Light
    ITEM_MAPPING = {
        "on": "power",
        "color": "color-rgb",
        "color_mode": "color-mode",
        "color_temperature": "color-temperature",
        "dimming": "brightness",
        "effect": "color-sequence",
    }
    ITEM_INSTANCE_MAPPING = {}

    async def turn_on(self, device_id: str) -> None:
        """Turn on the light."""
        await self.set_state(device_id, on=True)

    async def turn_off(self, device_id: str) -> None:
        """Turn off the light."""
        await self.set_state(device_id, on=False)

    async def set_color_temperature(self, device_id: str, temperature: int) -> None:
        """Set Color Temperature to light. Turn on light if it's currently off."""
        await self.set_state(
            device_id, on=True, temperature=temperature, color_mode="white"
        )

    async def set_brightness(self, device_id: str, brightness: int) -> None:
        """Set brightness of the light. Turn on light if it's currently off."""
        await self.set_state(device_id, on=True, brightness=brightness)

    async def set_rgb(self, device_id: str, red: int, green: int, blue: int) -> None:
        """Set RGB of the light. Turn on light if it's currently off."""
        await self.set_state(
            device_id, on=True, color=(red, green, blue), color_mode="color"
        )

    async def set_effect(self, device_id: str, effect: str) -> None:
        """Set effect of the light. Turn on light if it's currently off."""
        await self.set_state(device_id, on=True, effect=effect, color_mode="sequence")

    async def initialize_elem(self, item: dict) -> None:
        """Initialize the element"""
        self._logger.info("Initializing %s", item["id"])
        hs_device = device.get_hs_device(item)
        on: features.OnFeature | None = None
        color_temp: features.ColorTemperatureFeature | None = None
        color: features.ColorFeature | None = None
        color_mode: features.ColorModeFeature | None = None
        dimming: features.DimmingFeature | None = None
        effect: features.EffectFeature | None = None
        for state in hs_device.states:
            func_def = device.get_function_from_device(
                hs_device, state.functionClass, state.functionInstance
            )
            if state.functionClass == "power":
                on = features.OnFeature(on=state.value == "on")
            elif state.functionClass == "color-temperature":
                if len(func_def["values"]) > 1:
                    avail_temps = process_color_temps(func_def["values"])
                else:
                    avail_temps = process_range(func_def["values"][0])
                prefix = "K" if func_def.get("type", None) != "numeric" else ""
                color_temp = features.ColorTemperatureFeature(
                    temperature=state.value, supported=avail_temps, prefix=prefix
                )
            elif state.functionClass == "brightness":
                temp_bright = process_range(func_def["values"][0])
                dimming = features.DimmingFeature(
                    brightness=state.value, supported=temp_bright
                )
            elif state.functionClass == "color-sequence":
                current_effect = state.value
                effects = process_effects(hs_device.functions)
                effect = features.EffectFeature(effect=current_effect, effects=effects)
            elif state.functionClass == "color-rgb":
                color = features.ColorFeature(
                    red=state.value["color-rgb"].get("r", 0),
                    green=state.value["color-rgb"].get("g", 0),
                    blue=state.value["color-rgb"].get("b", 0),
                )
            elif state.functionClass == "color-mode":
                color_mode = features.ColorModeFeature(state.value)

        self._items[item["id"]] = light.Light(
            hs_device.functions,
            id=hs_device.id,
            on=on,
            dimming=dimming,
            color_mode=color_mode,
            color_temperature=color_temp,
            color=color,
            effect=effect,
        )

    async def set_state(
        self,
        device_id: str,
        on: bool | None = None,
        temperature: int | None = None,
        brightness: int | None = None,
        color_mode: str | None = None,
        color: tuple[int, int, int] | None = None,
        effect: str | None = None,
    ) -> None:
        """Set supported feature(s) to fan resource."""
        update_obj = light.LightPut()
        cur_item = await self.get_device(device_id)
        if on is not None:
            update_obj.on = features.OnFeature(on=on)
        if temperature is not None:
            update_obj.color_temperature = features.ColorTemperatureFeature(
                temperature=temperature,
                supported=cur_item.color_temperature.supported,
                prefix=cur_item.color_temperature.prefix,
            )
        if brightness is not None:
            update_obj.dimming = features.DimmingFeature(
                brightness=brightness, supported=cur_item.dimming.supported
            )
        if color is not None:
            update_obj.color_rgb = features.ColorFeature(
                red=color[0], green=color[1], blue=color[2]
            )
        if color_mode is not None:
            update_obj.color_mode = features.ColorModeFeature(mode=color_mode)
        if effect is not None:
            update_obj.effect = features.EffectFeature(
                effect=effect, effects=cur_item.effect.effects
            )
        await self.update(device_id, update_obj)


def process_color_temps(color_temps: dict) -> list[int]:
    """Determine the supported color temps

    :param color_temps: Result from functions["values"]
    """
    supported_temps = []
    for temp in color_temps:
        color_temp = temp["name"]
        if isinstance(color_temp, str) and color_temp.endswith("K"):
            color_temp = color_temp[0:-1]
        supported_temps.append(int(color_temp))
    return sorted(supported_temps)


def process_effects(functions: list[dict]) -> dict[str, set]:
    """Determine the supported effects"""
    supported_effects = {}
    for function in functions:
        if function["functionClass"] == "color-sequence":
            supported_effects[function["functionInstance"]] = set(
                process_names(function["values"])
            )
    return supported_effects
