"""Unit tests for IOPGPS entities and data parsing."""
import unittest
from unittest.mock import AsyncMock, patch

from custom_components.iopgps.iopgps_data import IOPGPSData, IOPGPSDevice, IOPGPSPositionData
from custom_components.iopgps.sensor import (
    IOPGPSBatterySensor,
    IOPGPSSpeedSensor,
    IOPGPSTodayDistanceSensor,
    IOPGPSTotalDistanceSensor,
)
from custom_components.iopgps.binary_sensor import IOPGPSMovingBinarySensor
from custom_components.iopgps.device_tracker import IOPGPSPositionSensor


class IOPGPSEntitiesTest(unittest.IsolatedAsyncioTestCase):
    """Test suite for IOPGPS sensors and device tracker."""

    def setUp(self) -> None:
        IOPGPSData.clean_instances()
        self.data = IOPGPSData.get_instance("test-guid", "Test Entry", "test_user", "test_key")
        self.imei = "863019175495698"

        # Create a mock device with comprehensive status
        device = IOPGPSDevice(self.imei)
        device.name = "Kim Mim"
        device.battery_percentage = 85
        device.speed = 12.5
        device.status = 1
        device.status_desc = "Moving"
        device.today_mile = 3.42
        device.total_mile = 120.5
        device.location_type = 1
        device.address = "Chiang Mai, Thailand"
        device.device_mobile = "0673120921"
        self.data.devices = [device]

        pos = IOPGPSPositionData(self.imei, "18.7883", "98.9853", 1791981868, "Chiang Mai, Thailand")
        self.data.positions = [pos]

    def test_battery_sensor(self):
        sensor = IOPGPSBatterySensor(self.data, self.imei)
        self.assertEqual(sensor.native_value, 85)
        self.assertEqual(sensor.native_unit_of_measurement, "%")
        self.assertEqual(sensor.icon, "mdi:battery-80")
        self.assertEqual(sensor.unique_id, f"iopgps_test-guid_{self.imei}_battery")

    def test_speed_sensor(self):
        sensor = IOPGPSSpeedSensor(self.data, self.imei)
        self.assertEqual(sensor.native_value, 12.5)
        self.assertEqual(sensor.native_unit_of_measurement, "km/h")
        self.assertEqual(sensor.icon, "mdi:speedometer")
        self.assertEqual(sensor.unique_id, f"iopgps_test-guid_{self.imei}_speed")

    def test_today_distance_sensor(self):
        sensor = IOPGPSTodayDistanceSensor(self.data, self.imei)
        self.assertEqual(sensor.native_value, 3.42)
        self.assertEqual(sensor.native_unit_of_measurement, "km")
        self.assertEqual(sensor.icon, "mdi:map-marker-distance")
        self.assertEqual(sensor.unique_id, f"iopgps_test-guid_{self.imei}_today_distance")

    def test_total_distance_sensor(self):
        sensor = IOPGPSTotalDistanceSensor(self.data, self.imei)
        self.assertEqual(sensor.native_value, 120.5)
        self.assertEqual(sensor.native_unit_of_measurement, "km")
        self.assertEqual(sensor.icon, "mdi:counter")
        self.assertEqual(sensor.unique_id, f"iopgps_test-guid_{self.imei}_total_distance")

    def test_moving_binary_sensor(self):
        binary = IOPGPSMovingBinarySensor(self.data, self.imei)
        self.assertTrue(binary.is_on)
        self.assertEqual(binary.unique_id, f"iopgps_test-guid_{self.imei}_moving")

        # Test stationary state
        device = self.data.get_device(self.imei)
        device.status = 2
        device.speed = 0.0
        self.assertFalse(binary.is_on)

    def test_device_tracker_attributes(self):
        tracker = IOPGPSPositionSensor(self.data, self.imei)
        attrs = tracker.extra_state_attributes
        self.assertEqual(attrs["address"], "Chiang Mai, Thailand")
        self.assertEqual(attrs["location_type"], "GPS")
        self.assertEqual(attrs["speed_kmh"], 12.5)
        self.assertEqual(attrs["today_distance_km"], 3.42)
        self.assertEqual(attrs["total_distance_km"], 120.5)
        self.assertEqual(attrs["status_desc"], "Moving")
        self.assertEqual(attrs["device_mobile"], "0673120921")

    async def test_update_devices_data_parsing(self):
        mock_devices_response = {
            "data": [{"imei": self.imei}]
        }
        mock_detail_response = {
            "data": {
                "deviceBrief": {
                    "name": "Kim Mim",
                    "deviceMobile": "0673120921",
                    "endTime": 1823439736,
                },
                "deviceStatus": {
                    "batteryPercentage": "77",
                    "speed": 8.5,
                    "status": 1,
                    "statusDesc": "Driving",
                    "todayMile": "1.25",
                    "totalMile": "55.0",
                    "locationType": 1,
                    "address": "Nimman Rd",
                    "gpsTime": 1791981868,
                    "heartTime": 1791985644,
                }
            }
        }

        with patch.object(self.data, 'make_get_request') as mock_req:
            mock_req.side_effect = [mock_devices_response, mock_detail_response]
            await self.data.update_devices_data()

            device = self.data.get_device(self.imei)
            self.assertIsNotNone(device)
            self.assertEqual(device.name, "Kim Mim")
            self.assertEqual(device.battery_percentage, 77)
            self.assertEqual(device.speed, 8.5)
            self.assertEqual(device.status, 1)
            self.assertEqual(device.status_desc, "Driving")
            self.assertEqual(device.today_mile, 1.25)
            self.assertEqual(device.total_mile, 55.0)
            self.assertEqual(device.location_type, 1)
            self.assertEqual(device.address, "Nimman Rd")
            self.assertEqual(device.device_mobile, "0673120921")
