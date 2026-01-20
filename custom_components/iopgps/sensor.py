"""
Platform for GPS sensor integration.
This module is responsible for setting up the battery level entity
and updating its state based on the data received from the IOPGPS API.
"""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant import config_entries
from homeassistant.helpers.entity import DeviceInfo # type: ignore

from custom_components.iopgps.const import DOMAIN, VERSION
from custom_components.iopgps.iopgps_data import IOPGPSData, IOPGPSDevice, IOPGPSPositionData
import logging

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=30)

class IOPGPSBatterySensor(SensorEntity):
    """
    Representation of a IOPGPS battery level sensor.
    Takes the data from base IOPGPSData object created in async_setup_entry.
    """
    _iopgps_data:IOPGPSData
    _device_imie:str
    _battery_level: int

    def __init__(self, iopgps_data: IOPGPSData, device_imie: str) -> None:
        """Initialize the sensor."""
        self._iopgps_data = iopgps_data
        self._device_imie = device_imie
        self._device_name = f"{self._iopgps_data.get_device(device_imie).name}" # type: ignore
        self._attr_unique_id = f"iopgps_{self._iopgps_data.guid}_{self._device_imie}_battery"
        self._attr_name = f"{self._device_name} Battery Level"
        self._attr_icon = "mdi:battery"

    async def async_update(self) -> None:
        """Update the sensor state."""
        try:
            await self._iopgps_data.async_update()
            position_data:IOPGPSPositionData = self._iopgps_data.get_position(self._device_imie)  # type: ignore
            device_data:IOPGPSDevice = self._iopgps_data.get_device(self._device_imie)  # type: ignore
            if position_data is not None:
                if device_data.battery_percentage is not None: # type: ignore
                    self._battery_level = device_data.battery_percentage  # type: ignore
                else:
                    self._battery_level = None  # type: ignore
        except Exception as e:
            _LOGGER.error("Error updating battery sensor: %s", e)
            self._battery_level = None # type: ignore

    @property
    def device_info(self) -> DeviceInfo | None: # type: ignore
        """Return the device info."""
        if self._iopgps_data is None:
            return None
        return self._iopgps_data.get_device_info(self._device_imie) # type: ignore

    @property
    def should_poll(self) -> bool: # type: ignore
        return True

    @property
    def device_class(self) -> SensorDeviceClass | str | None: 
        return SensorDeviceClass.BATTERY

    @property
    def state_class(self) -> SensorStateClass | str | None:
        return SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        if self._battery_level is not None:
            new_value = int(self._battery_level)
            # Make sure value is between 0 and 100
            if new_value < 0:
                new_value = 0
            elif new_value > 100:
                new_value = 100
            return new_value
        else:
            return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        return "%"

    @property
    def icon(self) -> str | None:
        """Set the icon based on battery level in 10% increments."""
        battery_level = self._battery_level
        if battery_level is not None:
            if battery_level == 100:
                return "mdi:battery"
            elif battery_level >= 90:
                return "mdi:battery-90"
            elif battery_level >= 80:
                return "mdi:battery-80"
            elif battery_level >= 70:
                return "mdi:battery-70"
            elif battery_level >= 60:
                return "mdi:battery-60"
            elif battery_level >= 50:
                return "mdi:battery-50"
            elif battery_level >= 40:
                return "mdi:battery-40"
            elif battery_level >= 30:
                return "mdi:battery-30"
            elif battery_level >= 20:
                return "mdi:battery-20"
            elif battery_level >= 10:
                return "mdi:battery-10"
            else:
                return "mdi:battery-alert"
        else:
            return "mdi:battery-alert"

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return the device info."""
        if self._iopgps_data is None:
            return None
        return self._iopgps_data.get_device_info(self._device_imei) # type: ignore

    @property
    def should_poll(self) -> bool:
        return True

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
        _LOGGER.error("User or key not set in config entry")
        return

    # Create main IOPGPS data object from iopgps_data.py
    iopgps_data = IOPGPSData.get_instance(guid, entry_name, user, key) # type: ignore

    # Update the data
    await iopgps_data.async_update()

    # Add the IOPGPS sensors to the entity registry
    devices = iopgps_data.get_device_ids()
    if devices is not None:
        _LOGGER.debug("Devices found: %s", devices)
        entities = []
        for device_id in devices:
            entities.append(IOPGPSBatterySensor(iopgps_data, device_id))

        if entities and async_add_entities:
            async_add_entities(entities, update_before_add=True)
    else:
        _LOGGER.error("No devices found for entry: %s", entry_name)
