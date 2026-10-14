"""
Main class for IOPGPS data handling.
Singleton class to handle data fetching and storing for all the sensors to read from.
This class is responsible for fetching data from the IOPGPS API and storing it.
It also acts as a gateway for the sensors to make only few API calls which results all sensors can read
instead of each sensor making its own API calls.
"""
import asyncio
import logging
import time
from datetime import timedelta
import aiohttp
from aiohttp import ClientTimeout
import hashlib
from homeassistant.helpers.device_registry import DeviceInfo
from custom_components.iopgps.const import DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=30)
REQUEST_TIMEOUT = 10  # 10 seconds per request
API_URL = "https://open.iopgps.com/api/"


class IOPGPSDevice:
    """Representation of single IOPGPS device."""

    # Basic attributes
    imei: str
    name: str | None = None
    battery_percentage: int | None = None
    speed: float | None = None
    status: int | None = None
    status_desc: str | None = None
    today_mile: float | None = None
    total_mile: float | None = None
    location_type: int | None = None
    address: str | None = None
    device_mobile: str | None = None
    end_time: int | None = None
    gps_time: int | None = None
    heart_time: int | None = None

    def __init__(self, imei: str) -> None:
        """Initialize the IOPGPSDevice class."""
        self.imei = imei
        self.name = None
        self.battery_percentage = None
        self.speed = None
        self.status = None
        self.status_desc = None
        self.today_mile = None
        self.total_mile = None
        self.location_type = None
        self.address = None
        self.device_mobile = None
        self.end_time = None
        self.gps_time = None
        self.heart_time = None

class IOPGPSPositionData:
    """Representation of single IOPGPS device tracking data."""

    imei: str
    lat: str
    lng: str
    gpsTime: int
    address: str

    def __init__(self, imei: str, lat: str, lng: str, gpsTime: int, address: str) -> None:
        """Initialize the IOPGPSTracking class."""
        self.imei = imei
        self.lat = lat
        self.lng = lng
        self.gpsTime = gpsTime
        self.address = address 

class AuthenResponse:
    token:str
    expiresIn:int

    def __init__(self, json):
        self.token = json["accessToken"]
        self.expiresIn = int(json["expiresIn"])

    def __str__(self):
        return f"token: {self.token}, expiresIn: {self.expiresIn}"

class ApiError(Exception):
    error = None
    def __init__(self, json):
        self.error = json["error"]

IOPGPSDataInstances: dict[str, "IOPGPSData"] = {}

class IOPGPSData:
    """Main class for IOPGPS data handling."""

    guid: str

    # Credentials properties
    user: str
    key: str
    token: str | None = None
    expiresIn: int = 0
    last_update: float = 0

    # Update properties
    update_lock = asyncio.Lock()

    # Pure json responses from API
    devices_json: str
    positions_json: str

    # Deserialized data
    devices: list[IOPGPSDevice] = []
    positions: list[IOPGPSPositionData] = []

    def __init__(self, guid: str, entry_name: str, user: str, key: str) -> None:
        """
        Initialize the IOPGPSData class.
        """

        self.guid = guid
        self.entry_name = entry_name
        self.user = user
        self.key = key
        self.token = None
        self.expiresIn = 0
        self.last_update = 0
        self.devices = []
        self.positions = []

    @classmethod
    def get_instance(cls, guid: str, entry_name: str, user: str, key: str) -> "IOPGPSData":
        """
        Get or create a singleton instance of IOPGPSData for the given entry_name.
        """
        if guid not in IOPGPSDataInstances:
            IOPGPSDataInstances[guid] = cls(guid, entry_name, user, key)
        return IOPGPSDataInstances[guid]

    @classmethod
    def clean_instances(cls) -> None:
        """
        Clean all instances of IOPGPSData.
        This is used for testing purposes to reset the singleton instances.
        """
        IOPGPSDataInstances.clear()

    @staticmethod
    async def make_get_request(url: str, headers: dict, params: dict, timeout: int = REQUEST_TIMEOUT):
        """Reusable function for making GET requests."""
        connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
        async with aiohttp.ClientSession(connector=connector, timeout=ClientTimeout(total=timeout)) as session:
            async with session.get(url, headers=headers, params=params) as response:
                json_data = await response.json()
                if response.status == 200:
                    return json_data
                else:
                    raise ApiError(json_data)

    @staticmethod
    async def make_post_request(url: str, headers: dict, payload: dict, params: dict,
                                timeout: int = REQUEST_TIMEOUT):
        """Reusable function for making POST requests."""
        connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
        async with aiohttp.ClientSession(connector=connector, timeout=ClientTimeout(total=timeout)) as session:
            async with session.post(url, headers=headers, json=payload, params=params) as response:
                json_data = await response.json()
                if response.status == 200:
                    return json_data
                else:
                    raise ApiError(json_data)

    async def get_authen_token(self) -> str | None:
        """
        Get login token from HTTP Post request to API_URL/login.
        Use aiohttp instead of requests to avoid blocking
        Corresponding CURL command:
        curl --location 'https://open.iopgps.com/api/auth/' \
        --header 'Content-Type: application/json' \
        --data '{
            "appid": "XX5698",
            "time" : 1768713467,
            "signature" : "99f81958bc6f0634dff0a9f7a2a06556"
        }'
        Signature = md5(md5(key)+time), See https://www.iopgps.com/doc/view?api=iop#tag/1.Authentication/paths/~1api~1auth/post
        Returns LoginResponse.token or None
        """
        if not self.user or not self.key:
            _LOGGER.error("Cannot authenticate: user or key not set")
            return None

        timestamp = str(int(time.time()))
        signature = hashlib.md5((hashlib.md5(self.key.encode()).hexdigest() + timestamp).encode()).hexdigest()

        url = API_URL + "auth/"
        payload = {
            'appid' : self.user,
            'time' : timestamp,
            'signature' : signature
        }
        headers = {
            'accept': 'application/json'
        }
        params = {
        }
        try:
            json = await self.make_post_request(url, headers, payload=payload, params=params)
            authen_response = AuthenResponse(json)
            self.expiresIn = int(authen_response.expiresIn) + int(time.time())
            self.token = authen_response.token
            return authen_response.token
        except ApiError as e:
            _LOGGER.error(f"Error while getting login token: {e.error}")
            return None
        except TimeoutError:
            _LOGGER.error("Timeout while getting login token.")
            return None
        except Exception as e:
            _LOGGER.error(f"Error while getting login token: {e}")
            return None

    async def refresh_token(self, forced: bool = False) -> None:
        if (int(time.time()) >= self.expiresIn) or self.token is None or forced:
            _LOGGER.debug("Refreshing token...")
            try:
                # Fetch new token
                new_token = await self.get_authen_token()
                if new_token:
                    self.token = new_token
                    _LOGGER.debug("Token refreshed successfully.")
                else:
                    _LOGGER.error("Failed to refresh token.")
                    self.clean_data()
            except TimeoutError:
                _LOGGER.error("Timeout while getting login token.")
                self.clean_data()
            except Exception as e:
                _LOGGER.error(f"Error during token refresh: {e}")
                self.clean_data()
        else:
            _LOGGER.debug("Token refresh skipped (still valid).")

    def clean_data(self):
        self.devices = []
        self.positions = []

    def get_standard_headers(self) -> dict:
        """
        Get standard headers for API requests.
        :return: dict with headers
        """
        return {
            'accessToken': f'{self.token}' if self.token else '',
            'accept': 'application/json',
        }


    async def async_update(self, forced: bool = False) -> None:
        """
        Update the data from the IOPGPS API.
        This method is called by the update coordinator.
        It fetches the data from the API and updates the internal state.
        """
        async with self.update_lock:
            # Throttle requests if polled within 10 seconds unless forced
            if not forced and (time.time() - self.last_update < 10):
                return

            # Check if we need to refresh token
            await self.refresh_token(forced=forced)
            if not self.token:
                _LOGGER.error("Cannot update IOPGPS data: No valid authentication token")
                return

            # Fetch the new data from the API
            await self.update_devices_data()
            await self.update_position_data()
            self.last_update = time.time()


    def get_device(self, device_imei: str) -> IOPGPSDevice | None:
        """Get device by id."""
        for device in self.devices:
            if device.imei == device_imei:
                return device
        return None

    def get_device_ids(self) -> list[str]:
        """Get device imeis."""
        return [device.imei for device in self.devices]
 
    def get_device_info(self, device_imei: str) -> dict | None:
        """Get device info by id."""
        for device in self.devices:
            if device.imei == device_imei:
                return {
                    "identifiers": {
                        (DOMAIN, f"{self.guid}_{device.imei}")
                    },
                    "name": f"{device.name}",
                    "manufacturer": "IOPGPS",
                    "model" : "GPS Tracker",
                    "sw_version": VERSION,
                }
        return None

    def get_position(self, imei: str) -> IOPGPSPositionData | None:
        """Get position data by device id."""
        for position in self.positions:
            if position.imei == imei:
                return position
        return None
 
    async def update_position_data(self) -> None:
        """
        Gets the position data for all the devices from API and saves them in self.positions.
        Using aiohttp to avoid blocking.
        """
        url = API_URL + "device/location"
        headers = self.get_standard_headers()
        positions_by_imei = {pos.imei: pos for pos in self.positions}
        for device in self.devices:
            params = {
                "imei": device.imei
            }
            try:
                json = await self.make_get_request(url, headers=headers, params=params)
                pos = IOPGPSPositionData(
                    device.imei,
                    json.get("lat"),
                    json.get("lng"),
                    int(json.get("gpsTime", 0)),
                    json.get("address", "")
                )
                positions_by_imei[device.imei] = pos
            except ApiError as e:
                _LOGGER.error(f"Error while getting tracking data for {device.imei}: {e.error}")
            except (TimeoutError, asyncio.TimeoutError):
                _LOGGER.warning(f"Timeout while getting tracking data for {device.imei}.")
            except Exception as e:
                _LOGGER.error(f"Error updating position data for {device.imei}: {e}")

        self.positions = list(positions_by_imei.values())

    async def update_devices_data(self) -> None:
        """
        Gets info about all devices in the account from the API and saves them in self.devices.
        Using aiohttp to avoid blocking.
        """
        url = API_URL + "device"
        headers = self.get_standard_headers()
        try:
            json = await self.make_get_request(url, headers=headers, params={})
            devices_list = json.get("data", [])
        except ApiError as e:
            _LOGGER.error(f"Error while getting devices list: {e.error}")
            return
        except (TimeoutError, asyncio.TimeoutError):
            _LOGGER.warning("Timeout while getting devices list.")
            return
        except Exception as e:
            _LOGGER.error(f"Error while updating IOPGPS devices: {e}")
            return

        devices_by_imei = {dev.imei: dev for dev in self.devices}
        for device in devices_list:
            imei = device.get("imei")
            if not imei:
                continue
            detail_url = API_URL + "device/detail/"
            parameters = {"imei": imei}
            try:
                json_device = await self.make_get_request(detail_url, headers=headers, params=parameters)
                data_dict = json_device.get("data", {})
                device_status = data_dict.get("deviceStatus", {})
                device_brief = data_dict.get("deviceBrief", {})

                device_data = devices_by_imei.get(imei, IOPGPSDevice(imei))
                device_data.imei = imei

                name = device_brief.get("name")
                if name:
                    device_data.name = name
                device_data.device_mobile = device_brief.get("deviceMobile")
                device_data.end_time = device_brief.get("endTime")

                # Parse battery percentage
                bat = device_status.get("batteryPercentage")
                if bat is not None:
                    try:
                        device_data.battery_percentage = int(bat)
                    except (ValueError, TypeError):
                        pass

                # Parse speed
                spd = device_status.get("speed")
                if spd is not None:
                    try:
                        device_data.speed = float(spd)
                    except (ValueError, TypeError):
                        pass

                # Parse status & description
                st = device_status.get("status")
                if st is not None:
                    try:
                        device_data.status = int(st)
                    except (ValueError, TypeError):
                        pass
                if "statusDesc" in device_status:
                    device_data.status_desc = device_status.get("statusDesc")

                # Parse todayMile & totalMile
                tm = device_status.get("todayMile")
                if tm is not None:
                    try:
                        device_data.today_mile = float(tm)
                    except (ValueError, TypeError):
                        pass

                tot = device_status.get("totalMile")
                if tot is not None:
                    try:
                        device_data.total_mile = float(tot)
                    except (ValueError, TypeError):
                        pass

                loc_type = device_status.get("locationType")
                if loc_type is not None:
                    try:
                        device_data.location_type = int(loc_type)
                    except (ValueError, TypeError):
                        pass

                if "address" in device_status:
                    device_data.address = device_status.get("address")
                if "gpsTime" in device_status:
                    device_data.gps_time = device_status.get("gpsTime")
                if "heartTime" in device_status:
                    device_data.heart_time = device_status.get("heartTime")

                devices_by_imei[imei] = device_data
            except ApiError as e:
                _LOGGER.error(f"Error getting detail for device {imei}: {e.error}")
            except (TimeoutError, asyncio.TimeoutError):
                _LOGGER.warning(f"Timeout getting detail for device {imei}.")
            except Exception as e:
                _LOGGER.error(f"Error getting detail for device {imei}: {e}")

        self.devices = list(devices_by_imei.values())
