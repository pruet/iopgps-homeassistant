"""
Platform for binary sensor integration.
This module is responsible for setting up moving/motion binary sensor entities
and updating their states based on the data received from the IOPGPS API.
"""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from custom_components.iopgps.iopgps_data import IOPGPSData

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=60)


class IOPGPSMovingBinarySensor(BinarySensorEntity):
    """Representation of an IOPGPS moving status binary sensor."""

    _iopgps_data: IOPGPSData
    _device_imei: str

    def __init__(self, iopgps_data: IOPGPSData, device_imei: str) -> None:
        """Initialize the binary sensor."""
        self._iopgps_data = iopgps_data
        self._device_imei = device_imei
        device = self._iopgps_data.get_device(device_imei)
        self._device_name = f"{device.name}" if device and device.name else device_imei
        self._attr_unique_id = f"iopgps_{self._iopgps_data.guid}_{self._device_imei}_moving"
        self._attr_name = f"{self._device_name} Moving"
        self._attr_device_class = BinarySensorDeviceClass.MOVING

    async def async_update(self) -> None:
        """Update the binary sensor state."""
        await self._iopgps_data.async_update()

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return the device info."""
        if self._iopgps_data is None:
            return None
        return self._iopgps_data.get_device_info(self._device_imei)

    @property
    def should_poll(self) -> bool:
        return True

    @property
    def is_on(self) -> bool | None:
        """Return true if the device is currently moving."""
        device = self._iopgps_data.get_device(self._device_imei)
        if device is None:
            return None
        # status == 1 indicates moving; speed > 0 also indicates motion
        return (device.status == 1) or (device.speed is not None and device.speed > 0)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Add binary sensors for passed config_entry in HA."""
    _LOGGER.debug("Starting setup for IOPGPS binary sensor integration")

    guid = config_entry.data.get("guid")
    entry_name = config_entry.data.get("entry_name", "My IOPGPS account")
    user = config_entry.data.get("user")
    key = config_entry.data.get("key")
    if not user or not key:
        _LOGGER.error("User or key not set in config entry")
        return

    iopgps_data = IOPGPSData.get_instance(guid, entry_name, user, key)
    await iopgps_data.async_update()

    devices = iopgps_data.get_device_ids()
    if devices:
        _LOGGER.debug("Devices found for binary sensor: %s", devices)
        entities = [IOPGPSMovingBinarySensor(iopgps_data, device_id) for device_id in devices]
        if entities and async_add_entities:
            async_add_entities(entities, update_before_add=True)
    else:
        _LOGGER.error("No devices found for entry: %s", entry_name)
