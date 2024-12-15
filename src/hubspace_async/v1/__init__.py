"""Controls HubSpace devices on v1 API"""

import asyncio
import copy
import logging
from contextlib import asynccontextmanager
from typing import Any, Generator, Optional

import aiohttp

from .. import const as hs_const
from ..auth import HubSpaceAuth
from ..device import HubSpaceDevice, get_hs_device
from . import v1_const
from .controllers.fan import FanController
from .controllers.light import LightController


class HubSpaceBridgeV1:
    """Controls HubSpace devices on v1 API"""

    _web_session: Optional[aiohttp.ClientSession] = None

    def __init__(
        self,
        username: str,
        password: str,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        self._web_session: aiohttp.ClientSession = session
        self._account_id: Optional[str] = None
        self._auth = HubSpaceAuth(username, password)
        self.logger = logging.getLogger(f"{__package__}[{username}]")
        self.logger.addHandler(logging.StreamHandler())
        self.logger.setLevel(logging.DEBUG)
        self._binary_sensors = None
        self._fans: FanController = FanController(self)
        self._lights: LightController = LightController(self)
        self._locks = None
        self._sensors = None
        self._switches = None
        self._valves = None

    @property
    def binary_sensors(self) -> None:
        return self._binary_sensors

    @property
    def fans(self) -> FanController:
        return self._fans

    @property
    def lights(self) -> LightController:
        return self._lights

    @property
    def locks(self) -> None:
        return self._locks

    @property
    def sensors(self) -> None:
        return self._sensors

    @property
    def switches(self) -> None:
        return self._switches

    @property
    def valves(self) -> None:
        return self._valves

    @property
    async def account_id(self) -> str:
        """Get the account ID for the HubSpace account

        If the account is not set, look it up and cache it for later.
        """
        if not self._account_id:
            self._account_id = await self.get_account_id()
        return self._account_id

    async def get_account_id(self) -> str:
        """Lookup the account ID associated with the login"""
        self.logger.debug("Querying API for account id")
        headers = {"host": "api2.afero.net"}
        res = await self.request(
            "GET", v1_const.HUBSPACE_ACCOUNT_ID_URL, headers=headers
        )
        return res.get("accountAccess")[0].get("account").get("accountId")

    async def initialize(self) -> None:
        """Query HubSpace API for all data"""
        hs_data = await self.fetch_data()
        await asyncio.gather(
            self.fans.initialize(hs_data),
            self.lights.initialize(hs_data),
            # self._config.initialize(hs_data),
            # self._devices.initialize(hs_data),
            # self._lights.initialize(hs_data),
            # self._scenes.initialize(hs_data),
            # self._sensors.initialize(hs_data),
            # self._groups.initialize(hs_data),
        )

    async def fetch_data(self) -> list[dict[Any, str]]:
        """Query the API"""
        self.logger.debug("Querying API for all data")
        headers = {
            "host": v1_const.HUBSPACE_DATA_HOST,
        }
        params = {"expansions": "state"}
        return await self.request(
            "get",
            v1_const.HUBSPACE_DATA_URL.format(await self.account_id),
            headers=headers,
            params=params,
        )

    async def extract_devices(
        self, hs_data: list[dict[Any, str]]
    ) -> list[HubSpaceDevice]:
        for element in hs_data:
            elem_id = element.get("id")
            type_id = element.get("typeId")
            devices: list[HubSpaceDevice | None] = []
            if type_id == "metadevice.device":
                self.logger.debug("Adding a new device, %s", elem_id)
                devices.append(await self.process_hs_json_dev(get_hs_device(element)))
            else:
                self.logger.debug(
                    "Unable to process a result of type %s", element.get("typeId")
                )
            return devices

    async def process_hs_json_dev(self, dev: HubSpaceDevice) -> None:
        mapped = hs_const.DEVICE_CLASS_TO_ENTITY_MAP.get(dev.device_class)
        if not mapped:
            self.logger.debug(
                "Unable to process %s as %s is not mapped",
                dev.friendly_name,
                dev.device_class,
            )
            return

    @asynccontextmanager
    async def create_request(
        self, method: str, url: str, **kwargs
    ) -> Generator[aiohttp.ClientResponse, None, None]:
        """
        Make a request to any path with V2 request method (auth in header).

        Returns a generator with aiohttp ClientResponse.
        """
        if self._web_session is None:
            connector = aiohttp.TCPConnector(
                limit_per_host=3,
            )
            self._web_session = aiohttp.ClientSession(connector=connector)

        token = await self._auth.token(self._web_session)
        headers = get_headers(
            **{
                "authorization": f"Bearer {token}",
            }
        )
        headers.update(kwargs.get("headers", {}))
        kwargs["headers"] = headers
        kwargs["ssl"] = True
        async with self._web_session.request(method, url, **kwargs) as res:
            yield res

    async def request(self, method: str, url: str, **kwargs) -> dict | list[dict]:
        """Make request on the api and return response data."""
        retries = 0
        self.logger.info("Making request [%s] to %s with %s", method, url, kwargs)
        while retries < hs_const.MAX_RETRIES:
            retries += 1
            if retries > 1:
                retry_wait = 0.25 * retries
                await asyncio.sleep(retry_wait)
            async with self.create_request(method, url, **kwargs) as resp:
                # 503 means the service is temporarily unavailable, back off a bit.
                # 429 means the bridge is rate limiting/overloaded, we should back off a bit.
                if resp.status in [429, 503]:
                    continue
                elif resp.status == 403:
                    raise aiohttp.web_exceptions.HTTPForbidden()
                else:
                    return await resp.json()


def get_headers(**kwargs):
    headers = copy.copy(v1_const.DEFAULT_HEADERS)
    headers.update(kwargs)
    return headers
