"""
Main class for PajGPS data handling.
Singleton class to handle data fetching and storing for all the sensors to read from.
This class is responsible for fetching data from the PajGPS API and storing it.
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
REQUEST_TIMEOUT = 5  # 5 seconds x 3 requests per update = 24 seconds (must stay below SCAN_INTERVAL)
API_URL = "https://open.iopgps.com/api/"


class IOPGPSDevice:
    """Representation of single Paj GPS device."""
 
    # Basic attributes
    imei: str
    name: str
    mobile:str
    battery_percentage: str

    def __init__(self, imei: str) -> None:
        """Initialize the IOPGPSDevice class."""
        self.imei = imei

class IOPGPSPositionData:
    """Representation of single IOPGPS device tracking data."""

    imei: str
    lat: str
    lng: str
    gpsTime: int
    address: str

    def __init__(self, imei: str, lat: str, lng: str, gpsTime: int, address: str) -> None:
        """Initialize the PajGPSTracking class."""
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
        self.expiresIn = json["expiresIn"]

    def __str__(self):
        return f"token: {self.token}, userID: {self.expiresIn}"

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
    token: str
    expiresIn: int

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
        Clean all instances of PajGPSData.
        This is used for testing purposes to reset the singleton instances.
        """
        IOPGPSDataInstances.clear()

    @staticmethod
    async def make_get_request(url: str, headers: dict, params: dict, timeout: int = REQUEST_TIMEOUT):
        """Reusable function for making GET requests."""
        async with aiohttp.ClientSession(timeout=ClientTimeout(total=timeout)) as session:
            async with session.get(url, headers=headers, params=params, timeout=ClientTimeout(total=timeout)) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    json = await response.json()
                    if json.get("error"):
                        raise ApiError(json)
        # Close the session
        await session.close()

    @staticmethod
    async def make_post_request(url: str, headers: dict, payload: dict, params: dict,
                                timeout: int = REQUEST_TIMEOUT):
        """Reusable function for making POST requests."""
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, params=params, timeout=ClientTimeout(total=timeout)) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    json = await response.json()
                    raise ApiError(json)
        # Close the session
        await session.close()

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
            self.expiresIn = authen_response.expiresIn
            self.token = authen_response.token
            return authen_response.token
        except ApiError as e:
            _LOGGER.error(f"Error while getting login token: {e.error}")
            return None
        except TimeoutError as e:
            _LOGGER.error("Timeout while getting login token.")
        except Exception as e:
            _LOGGER.error(f"Error while getting login token: {e}")
            return None

    async def refresh_token(self, forced: bool = False) -> None:
        # Refresh token once every 10 minutes
        if (int(time.time()) > self.expiresIn) or self.token is None or forced:
            _LOGGER.debug("Refreshing token...")
            try:
                self.user = self.user
                self.key = self.key
                # Fetch new token
                new_token = await self.get_authen_token()
                if new_token:
                    self.token = new_token
                    _LOGGER.debug("Token refreshed successfully.")
                else:
                    _LOGGER.error("Failed to refresh token.")
            except TimeoutError as e:
                _LOGGER.error("Timeout while getting login token.")
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
            'accessToken' : f'{self.token}'
        }


    async def async_update(self, forced: bool = False) -> None:
        """
        Update the data from the PajGPS API.
        This method is called by the update coordinator.
        It fetches the data from the API and updates the internal state.
        """
        # Check if we need to update data
        if (int(time.time()) > self.expiresIn) and not forced:
            return

        async with self.update_lock:
            # Check again if we need to update data
            if (int(time.time()) > self.expiresIn) and not forced:
                return

            # Check if we need to refresh token
            await self.refresh_token()

            # Fetch the new data from the API
            await self.update_devices_data()
            await self.update_position_data()


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
                    "mobile": device.mobile,
                    "battery_percentage": device.battery_percentage,
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
        Gets the position data for all the devices from API and saves them in self.positions_json and self.positions.
        Using aiohttp to avoid blocking.
        Corresponding CURL command:

        curl --location 'https://open.iopgps.com/api/device/location?imei=863019175495698' \
            --header 'accessToken: 1234560800eb43d8ace818b9867a987a'
            --data ''
        """
        url = API_URL + "device/location"
        headers = self.get_standard_headers()
        try:
            positions = []
            for device in self.devices:
                params = {
                    "imei": device.imei
                }
                json = await self.make_get_request(url, headers=headers, params=params)
                # self.positions_json = json
                pos = IOPGPSPositionData(device.imei, json["lat"], json["lng"], int(json["gpsTime"]), json["address"]) # type: ignore
                positions.append(pos)
            self.positions = positions
        except ApiError as e:
            _LOGGER.error(f"Error while getting tracking data: {e.error}")
            self.positions = []
        except TimeoutError as e:
            _LOGGER.warning("Timeout while getting tracking data.")
        except Exception as e:
            _LOGGER.error(f"Error updating position data: {e}")
            self.positions = []

    async def update_devices_data(self) -> None:
        """
        Gets info about all devices in the account from the API and saves them in self.devices_json and self.devices.
        Using aiohttp to avoid blocking.
        Corresponding CURL command:
        curl --location 'https://open.iopgps.com/api/device/' \
        --header 'accessToken: 1234560800eb43d8ace818b9867a987a'
        """
        url = API_URL + "device"
        headers = self.get_standard_headers() # Assuming get_standard_headers() returns a dict
        try:
            json = await self.make_get_request(url, headers, params={}) # Pass an empty dict for params
            new_devices = []
            for device in json["data"]: # type: ignore
                url = API_URL + "device/detail/"
                parameters = {
                    "imei": device["imei"]
                }
                json_device = await self.make_get_request(url, headers, params=parameters)
                json_device = json_device["data"] #type: ignore
                device_data = IOPGPSDevice(device["imei"])
                device_data.name = device["name"]
                device_data.imei = device["imei"]
                device_data.mobile = device["mobile"]
                device_data.battery_percentage = json_device["deviceStatus"]["batteryPercentage"]
                new_devices.append(device_data)
            self.devices = new_devices
        except ApiError as e:
            _LOGGER.error(f"Error while getting devices data: {e.error}")
            self.devices = []
        except TimeoutError as e:
            _LOGGER.warning("Timeout while getting devices data.")
        except Exception as e:
            _LOGGER.error(f"Error while updating Paj GPS devices: {e}")
            self.devices = []
