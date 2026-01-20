"""
Platform for GPS sensor integration.
This module is responsible for setting up the GPS sensor entities
and updating their state based on the data received from the IOPGPS API.
"""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant import config_entries
from homeassistant.helpers.entity import DeviceInfo # type: ignore

from custom_components.iopgps.const import DOMAIN, VERSION
from custom_components.iopgps.iopgps_data import IOPGPSData
import logging

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=30)

class IOPGPSPositionSensor(TrackerEntity):
    """
    Representation of a IOPGPS position sensor.
    Takes the data from base IOPGPSData object created in async_setup_entry.
    """
    _iopgps_data:IOPGPSData
    _device_imei:str
    _longitude: float | None = None
    _latitude: float | None = None

    def __init__(self, iopgps_data: IOPGPSData, device_imei: str) -> None:
        """Initialize the sensor."""
        self._iopgps_data = iopgps_data
        self._device_imei = device_imei
        self._device_name = f"{self._iopgps_data.get_device(device_imei).name}" # type: ignore
        self._attr_unique_id = f"iopgps_{self._iopgps_data.guid}_{self._device_imei}_gps"
        self._attr_name = f"{self._device_name} Location"
        self._attr_icon = "mdi:map-marker"

    @property
    def device_info(self) -> DeviceInfo | None: # type: ignore
        """Return the device info."""
        if self._iopgps_data is None:
            return None
        return self._iopgps_data.get_device_info(self._device_imei) # type: ignore

    @property
    def should_poll(self) -> bool: # type: ignore
        return True

    @property
    def latitude(self) -> float | None: # type: ignore
        """Return latitude value of the device."""
        if self._latitude is not None:
            return self._latitude
        else:
            return None

    @property
    def longitude(self) -> float | None: # type: ignore
        """Return longitude value of the device."""
        if self._longitude is not None:
            return self._longitude
        else:
            return None


    @property
    def source_type(self) -> str: # type: ignore
        """Return the source type, eg gps or router, of the device."""
        return "gps"

    async def async_update(self) -> None:
        """Update the GPS sensor data."""
        await self._iopgps_data.async_update()
        position_data = self._iopgps_data.get_position(self._device_imei)
        if position_data is not None:
            if position_data.lat is not None and position_data.lng is not None:
                self._latitude = float(position_data.lat)
                self._longitude = float(position_data.lng)
            else:
                self._latitude = None
                self._longitude = None
        else:
            self._latitude = None
            self._longitude = None

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Add sensors for passed config_entry in HA."""
    _LOGGER.debug("Starting setup for IOPGPS integration")

    # Get the entry name
    entry_name = config_entry.data.get("entry_name", "My IOPGPS account")

    # Validate email and password
    guid = config_entry.data.get("guid")
    user = config_entry.data.get("user")
    key = config_entry.data.get("key")
    if not user or not key:
        _LOGGER.error("Username or key not set in config entry")
        return

    # Create main IOPGPS data object from iopgps_data.py
    iopgps_data = IOPGPSData.get_instance(guid, entry_name, user, key) # type: ignore

    # Update the data
    await iopgps_data.async_update()

    # Add the IOPGPS position sensors to the entity registry
    devices = iopgps_data.get_device_ids()
    if devices is not None:
        _LOGGER.debug("Adding IOPGPS position sensors")
        entities = []
        for device_imei in devices:
            entities.append(IOPGPSPositionSensor(iopgps_data, device_imei))
        if entities and async_add_entities:
            async_add_entities(entities, update_before_add=True)
        else:
            _LOGGER.warning("No new IOPGPS devices to add")