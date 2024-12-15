import time
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Generic, TypeVar

from ...device import HubSpaceDevice
from .. import v1_const
from ..models.resource import ResourceTypes

if TYPE_CHECKING:
    from .. import HubSpaceBridgeV1


HubSpaceResource = TypeVar("HubSpaceResource")


class BaseResourcesController(Generic[HubSpaceResource]):
    """Base Controller for HubSpace devices"""

    ITEM_TYPE_ID: ResourceTypes | None = None
    ITEM_TYPE: ResourceTypes | None = None
    ITEM_CLS = None
    ITEM_MAPPING: dict = {}

    def __init__(self, bridge: "HubSpaceBridgeV1") -> None:
        """Initialize instance."""
        self._bridge = bridge
        self._items: dict[str, HubSpaceResource] = {}
        self._logger = bridge.logger.getChild(self.ITEM_TYPE.value)
        self._initialized: bool = False

    @property
    def items(self) -> list[HubSpaceDevice]:
        """Return all items for this resource."""
        return list(self._items.values())

    async def initialize(self, initial_data: list[dict]) -> None:
        """Initialize controller by fetching all items for this resource type from bridge."""
        for element in initial_data:
            if element["typeId"] != self.ITEM_TYPE_ID.value:
                self._logger.debug(
                    "TypeID [%s] does not match %s",
                    element["typeId"],
                    self.ITEM_TYPE_ID.value,
                )
                continue
            dev_class = (
                element.get("description", {}).get("device", {}).get("deviceClass")
            )
            if dev_class != self.ITEM_TYPE.value:
                self._logger.debug(
                    "Device Class [%s] does not match %s",
                    dev_class,
                    self.ITEM_TYPE.value,
                )
                continue
            await self.initialize_elem(element)

    async def initialize_elem(self, element: dict) -> None:
        pass

    async def update(
        self, device_id: str, obj_in: HubSpaceResource, instance: str | None = None
    ) -> None:
        """Update HubSpace with the new data

        :param device_id: HubSpace Device ID
        :param obj_in: HubSpace Resource elements to change
        :param instance: Instance for the HubSpace Resource
        """
        url = v1_const.HUBSPACE_DEVICE_STATE.format(
            await self._bridge.account_id, device_id
        )
        cur_item = self._items.get(device_id)
        if cur_item is None:
            self._logger.warning("received update for unknown item %s", device_id)
            return
        hs_states = dataclass_to_hs(cur_item, obj_in, self.ITEM_MAPPING)
        # @TODO - Implement bluetooth logic for update
        if True:
            headers = {
                "host": v1_const.HUBSPACE_DATA_HOST,
                "content-type": "application/json; charset=utf-8",
            }
            payload = {"metadeviceId": str(device_id), "values": hs_states}
            await self._bridge.request("put", url, json=payload, headers=headers)
        # Update the state of the item to match the new states
        update_dataclass(cur_item, obj_in)

    async def get_device(self, device_id) -> HubSpaceResource:
        cur_item = self._items.get(device_id)
        if cur_item is None:
            self._logger.warning("received update for unknown item %s", device_id)
            return
        return cur_item


def update_dataclass(elem: HubSpaceResource, cls: dataclass):
    """Updates the element with the latest changes"""
    for f in fields(cls):
        cur_val = getattr(cls, f.name, None)
        if cur_val is None:
            continue
        setattr(elem, f.name, cur_val)


def dataclass_to_hs(
    elem: HubSpaceResource, cls: dataclass, mapping: dict
) -> list[dict]:
    """Convert the current state to be consumed by HubSpace"""
    states = []
    for f in fields(cls):
        cur_val = getattr(cls, f.name, None)
        if cur_val is None:
            continue
        hs_key = mapping.get(f.name, f.name)
        new_state = {
            "functionClass": hs_key,
            "functionInstance": elem.get_instance(hs_key),
            "lastUpdateTime": int(time.time()),
            "value": None,
        }
        new_val = cur_val.hs_value
        if isinstance(new_val, dict):
            new_state.update(new_val)
        else:
            new_state["value"] = new_val
        states.append(new_state)
    return states
