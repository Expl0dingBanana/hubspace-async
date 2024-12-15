__all__ = ["HubSpaceConnection"]

import copy
import datetime
import logging
from contextlib import suppress
from dataclasses import asdict
from typing import Any, Optional

from aiohttp import ClientSession

from . import const
from .auth import HubSpaceAuth
from .device import HubSpaceDevice, HubSpaceState, get_hs_device
from .room import HubSpaceRoom, get_hs_room

logger = logging.getLogger(__name__)


class HubSpaceConnection:
    """Connect to the HubSpace API

    :param username: Username containing the devices
    :param password: Password for the username

    :ivar devices: Dictionary of HubSpaceDevice objects from the API referenced by
        their id
    :ivar raw_devices: Dictionary of dictionary objects (raw response) that are of
        the type "metadevice.device" from the API and referenced by their ID.
    :ivar raw_rooms: Dictionary of dictionary objects (raw response) that are of
        the type "metadevice.room" from the API and referenced by their ID.
    :ivar raw_homes: Dictionary of dictionary objects (raw response) that are of
        the type "metadevice.device" from the API and referenced by their ID.
    """

    def __init__(
        self, username: str, password: str, websession: Optional[ClientSession] = None
    ):
        self._auth = HubSpaceAuth(username, password)
        self.client = websession or ClientSession()
        self._account_id: Optional[str] = None
        self._devices: dict[str, HubSpaceDevice] = {}
        self._rooms: dict[str, HubSpaceRoom] = {}
        self.raw_devices: dict[str, Any] = {}
        self.raw_rooms: dict[str, Any] = {}
        self.raw_homes: dict[str, Any] = {}

    @property
    async def account_id(self) -> str:
        """Get the account ID for the HubSpace account

        If the account is not set, look it up and cache it for later.
        """
        if not self._account_id:
            self._account_id = await self.get_account_id()
        return self._account_id

    @property
    async def has_data(self) -> bool:
        """Determine if the API has previously been queried"""
        return any([self.raw_homes, self.raw_rooms, self.devices])

    @property
    async def devices(self) -> dict[str, HubSpaceDevice]:
        """Get all devices associated with the HubSpace account

        If devices is not populated, it will first populate the data. If the devices
        need to be refreshed, manually running `populate_data` is required.
        """
        if not self._devices:
            await self.populate_data()
        return self._devices

    @property
    async def rooms(self) -> dict[str, HubSpaceRoom]:
        """Get all rooms associated with the HubSpace account

        If rooms is not populated, it will first populate the data. If the devices
        need to be refreshed, manually running `populate_data` is required.
        """
        if not self._rooms:
            await self.populate_data()
        return self._rooms

    async def get_account_id(self) -> str:
        """Lookup the account ID associated with the login"""
        logger.debug("Querying API for account id")
        token = await self._auth.token(self.client)
        headers = get_headers(
            **{
                "authorization": f"Bearer {token}",
                "host": "api2.afero.net",
            }
        )
        async with self.client.get(
            const.HUBSPACE_ACCOUNT_ID_URL, headers=headers
        ) as response:
            account_id = (
                (await response.json())
                .get("accountAccess")[0]
                .get("account")
                .get("accountId")
            )
            return account_id

    async def _get_api_data(self) -> list[dict[str, str]]:
        """Query the API"""
        logger.debug("Querying API for all data")
        token = await self._auth.token(self.client)
        headers = get_headers(
            **{
                "authorization": f"Bearer {token}",
                "host": const.HUBSPACE_DATA_HOST,
            }
        )
        params = {"expansions": "state"}
        async with self.client.get(
            const.HUBSPACE_DATA_URL.format(await self.account_id),
            headers=headers,
            params=params,
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return data

    async def populate_data(self) -> None:
        """Query the API and populate the data"""
        await self._process_api_results(await self._get_api_data())

    async def _process_api_results(self, data: list[dict[str, Any]]) -> None:
        """Processes the results and populates the required fields

        :param data: Data to be processed from the API
        """
        for element in data:
            elem_id = element.get("id")
            type_id = element.get("typeId")
            if type_id == "metadevice.home":
                logger.debug("Adding a new home, %s", elem_id)
                self.raw_homes[elem_id] = element
            if type_id == "metadevice.room":
                logger.debug("Adding a new room, %s", elem_id)
                self.raw_rooms[elem_id] = element
            elif type_id == "metadevice.device":
                logger.debug("Adding a new device, %s", elem_id)
                self.raw_devices[elem_id] = element
                self._devices[elem_id] = get_hs_device(element)
            else:
                logger.debug(
                    "Unable to process a result of type %s", element.get("typeId")
                )
        # Populate rooms
        for room in self.raw_rooms.values():
            children: list[HubSpaceDevice] = []
            for child_id in room.get("children", []):
                with suppress(KeyError):
                    children.append((await self.devices)[child_id])
            self._rooms[room["id"]] = get_hs_room(room, children=children)

    async def get_room_by_id(self, room_id: str) -> dict[str, Any]:
        """Lookup a room by the ID

        :param room_id: ID of the device
        """
        if not self.has_data:
            await self._get_api_data()
        return self.raw_rooms[room_id]

    async def get_room_by_friendly_name(self, room_id: str) -> dict[str, Any]:
        """Lookup a device by the ID

        :param room_id: Friendly Name of the Device
        """
        if not self.has_data:
            await self._get_api_data()
        for device in self.raw_rooms.values():
            if device.get("friendlyName") == room_id:
                return device
        raise KeyError("Unable to find a device with a friendly name of %s" % room_id)

    async def get_device_state(self, device_id: str) -> list[HubSpaceState]:
        """Get all states for a given device

        :param device_id: ID of the device
        """
        logger.debug("Querying API for device [%s] states", device_id)
        url = const.HUBSPACE_DEVICE_STATE.format(await self.account_id, device_id)
        token = await self._auth.token(self.client)
        headers = get_headers(
            **{
                "authorization": f"Bearer {token}",
                "host": const.HUBSPACE_DATA_HOST,
            }
        )
        async with self.client.get(url, headers=headers) as response:
            response.raise_for_status()
            states = []
            for state in (await response.json())["values"]:
                try:
                    states.append(
                        HubSpaceState(
                            functionClass=state["functionClass"],
                            lastUpdateTime=state["lastUpdateTime"],
                            functionInstance=state.get("functionInstance"),
                            value=state["value"],
                        )
                    )
                except KeyError:
                    logger.debug("Skipping the state %s", state["functionClass"])
            return states

    async def set_device_states(
        self, device_id: str, new_states: list[HubSpaceState]
    ) -> None:
        """Set one or more states with a single API call


        :param device_id: ID of the device
        :param new_states: All states to set with the corresponding data
        """
        logger.debug(
            "Update the device [%s] with new states: %s", device_id, new_states
        )
        token = await self._auth.token(self.client)
        headers = get_headers(
            **{
                "authorization": f"Bearer {token}",
                "host": const.HUBSPACE_DATA_HOST,
                "content-type": "application/json; charset=utf-8",
            }
        )
        payload_states = []
        for state in new_states:
            state.lastUpdateTime = int(datetime.datetime.now().timestamp())
            payload_states.append(asdict(state))
        payload = {"metadeviceId": str(device_id), "values": payload_states}
        url = const.HUBSPACE_DEVICE_STATE.format(await self.account_id, device_id)
        async with self.client.put(url, headers=headers, json=payload) as response:
            response.raise_for_status()

    async def set_device_state(self, device_id: str, state: HubSpaceState) -> None:
        """Sets a state for the given device

        :param device_id: ID of the device
        :param state: State to set. last_update_time will be updated to now
        """
        await self.set_device_states(device_id, [state])


def get_headers(**kwargs):
    headers = copy.copy(const.DEFAULT_HEADERS)
    headers.update(kwargs)
    return headers
