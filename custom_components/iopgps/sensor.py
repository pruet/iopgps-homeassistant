"""
Platform for GPS sensor integration.
This module is responsible for setting up sensors:
- Battery level
- Speed
- Today's distance (exercise)
- Total distance (odometer)
and updating their states based on data received from the IOPGPS API.
"""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfLength, UnitOfSpeed
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from custom_components.iopgps.iopgps_data import IOPGPSData

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=60)


class IOPGPSBatterySensor(SensorEntity):
    """
    Representation of an IOPGPS battery level sensor.
    Takes the data from base IOPGPSData object created in async_setup_entry.
    """
    _iopgps_data: IOPGPSData
    _device_imei: str
    _battery_level: int | None = None

    def __init__(self, iopgps_data: IOPGPSData, device_imei: str) -> None:
        """Initialize the sensor."""
        self._iopgps_data = iopgps_data
        self._device_imei = device_imei
        device = self._iopgps_data.get_device(device_imei)
        self._device_name = f"{device.name}" if device and device.name else device_imei
        self._attr_unique_id = f"iopgps_{self._iopgps_data.guid}_{self._device_imei}_battery"
        self._attr_name = f"{self._device_name} Battery Level"
        self._attr_icon = "mdi:battery"

    async def async_update(self) -> None:
        """Update the sensor state."""
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
    def device_class(self) -> SensorDeviceClass | str | None: 
        return SensorDeviceClass.BATTERY

    @property
    def state_class(self) -> SensorStateClass | str | None:
        return SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        device = self._iopgps_data.get_device(self._device_imei)
        if device and device.battery_percentage is not None:
            try:
                new_value = int(device.battery_percentage)
                if new_value < 0:
                    new_value = 0
                elif new_value > 100:
                    new_value = 100
                return new_value
            except (ValueError, TypeError):
                return None
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        return "%"

    @property
    def icon(self) -> str | None:
        """Set the icon based on battery level in 10% increments."""
        battery_level = self.native_value
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
        return "mdi:battery-alert"


class IOPGPSSpeedSensor(SensorEntity):
    """Representation of an IOPGPS speed sensor."""

    _iopgps_data: IOPGPSData
    _device_imei: str

    def __init__(self, iopgps_data: IOPGPSData, device_imei: str) -> None:
        """Initialize the sensor."""
        self._iopgps_data = iopgps_data
        self._device_imei = device_imei
        device = self._iopgps_data.get_device(device_imei)
        self._device_name = f"{device.name}" if device and device.name else device_imei
        self._attr_unique_id = f"iopgps_{self._iopgps_data.guid}_{self._device_imei}_speed"
        self._attr_name = f"{self._device_name} Speed"
        self._attr_icon = "mdi:speedometer"

    async def async_update(self) -> None:
        """Update the sensor state."""
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
    def device_class(self) -> SensorDeviceClass | str | None:
        return SensorDeviceClass.SPEED

    @property
    def state_class(self) -> SensorStateClass | str | None:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        return UnitOfSpeed.KILOMETERS_PER_HOUR

    @property
    def native_value(self) -> float | None:
        device = self._iopgps_data.get_device(self._device_imei)
        return device.speed if device else None


class IOPGPSTodayDistanceSensor(SensorEntity):
    """Representation of an IOPGPS today's exercise/distance sensor."""

    _iopgps_data: IOPGPSData
    _device_imei: str

    def __init__(self, iopgps_data: IOPGPSData, device_imei: str) -> None:
        """Initialize the sensor."""
        self._iopgps_data = iopgps_data
        self._device_imei = device_imei
        device = self._iopgps_data.get_device(device_imei)
        self._device_name = f"{device.name}" if device and device.name else device_imei
        self._attr_unique_id = f"iopgps_{self._iopgps_data.guid}_{self._device_imei}_today_distance"
        self._attr_name = f"{self._device_name} Today Distance"
        self._attr_icon = "mdi:map-marker-distance"

    async def async_update(self) -> None:
        """Update the sensor state."""
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
    def device_class(self) -> SensorDeviceClass | str | None:
        return SensorDeviceClass.DISTANCE

    @property
    def state_class(self) -> SensorStateClass | str | None:
        return SensorStateClass.TOTAL

    @property
    def native_unit_of_measurement(self) -> str | None:
        return UnitOfLength.KILOMETERS

    @property
    def native_value(self) -> float | None:
        device = self._iopgps_data.get_device(self._device_imei)
        return device.today_mile if device else None


class IOPGPSTotalDistanceSensor(SensorEntity):
    """Representation of an IOPGPS total distance (odometer) sensor."""

    _iopgps_data: IOPGPSData
    _device_imei: str

    def __init__(self, iopgps_data: IOPGPSData, device_imei: str) -> None:
        """Initialize the sensor."""
        self._iopgps_data = iopgps_data
        self._device_imei = device_imei
        device = self._iopgps_data.get_device(device_imei)
        self._device_name = f"{device.name}" if device and device.name else device_imei
        self._attr_unique_id = f"iopgps_{self._iopgps_data.guid}_{self._device_imei}_total_distance"
        self._attr_name = f"{self._device_name} Total Distance"
        self._attr_icon = "mdi:counter"

    async def async_update(self) -> None:
        """Update the sensor state."""
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
    def device_class(self) -> SensorDeviceClass | str | None:
        return SensorDeviceClass.DISTANCE

    @property
    def state_class(self) -> SensorStateClass | str | None:
        return SensorStateClass.TOTAL_INCREASING

    @property
    def native_unit_of_measurement(self) -> str | None:
        return UnitOfLength.KILOMETERS

    @property
    def native_value(self) -> float | None:
        device = self._iopgps_data.get_device(self._device_imei)
        return device.total_mile if device else None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Add sensors for passed config_entry in HA."""
    _LOGGER.debug("Starting setup for IOPGPS sensor integration")

    entry_name = config_entry.data.get("entry_name", "My IOPGPS account")
    guid = config_entry.data.get("guid")
    user = config_entry.data.get("user")
    key = config_entry.data.get("key")
    if not user or not key:
        _LOGGER.error("User or key not set in config entry")
        return

    iopgps_data = IOPGPSData.get_instance(guid, entry_name, user, key)
    await iopgps_data.async_update()

    devices = iopgps_data.get_device_ids()
    if devices:
        _LOGGER.debug("Devices found: %s", devices)
        entities = []
        for device_id in devices:
            entities.extend([
                IOPGPSBatterySensor(iopgps_data, device_id),
                IOPGPSSpeedSensor(iopgps_data, device_id),
                IOPGPSTodayDistanceSensor(iopgps_data, device_id),
                IOPGPSTotalDistanceSensor(iopgps_data, device_id),
            ])

        if entities and async_add_entities:
            async_add_entities(entities, update_before_add=True)
    else:
        _LOGGER.error("No devices found for entry: %s", entry_name)
