import os
import time
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import custom_components.iopgps.iopgps_data as iopgps_data
from dotenv import load_dotenv

class IOPGPSDataTest(unittest.IsolatedAsyncioTestCase):

    data: iopgps_data.IOPGPSData

    def setUp(self) -> None:
        """
        This function is called before each test case.
        """
        load_dotenv()
        user = os.getenv('IOPGPS_USER')
        key = os.getenv('IOPGPS_KEY')
        entry_name = "test_entry"
        iopgps_data.IOPGPSData.clean_instances()
        self.data = iopgps_data.IOPGPSData.get_instance("test-guid", entry_name, user, key) # type: ignore


    async def test_login(self):
        """
        Test if credentials are set and if login token is valid.
        """
        assert self.data.user is not None
        assert self.data.key is not None
        if self.data.user is None or self.data.key is None:
            return
        # Test login with valid credentials
        token = await self.data.get_authen_token()
        assert token is not None
        # Test if login token is valid bearer header
        if token is not None:
            assert len(token) > 20

    async def test_refresh_token(self):
        """
        Test the refresh_token method.
        """
        with patch.object(self.data, 'get_authen_token', new=AsyncMock(return_value="new_token")):
            self.data.token = None # type: ignore
            await self.data.refresh_token()
            assert self.data.token == "new_token"

    async def test_async_update(self):
        """
        Test the async_update method.
        """
        with (patch.object(self.data, 'refresh_token', new=AsyncMock()), \
             patch.object(self.data, 'update_position_data', new=AsyncMock()), \
             patch.object(self.data, 'update_devices_data', new=AsyncMock())):
            await self.data.async_update()


    def test_get_standard_headers(self):
        """
        Test the get_standard_headers method.
        """
        self.data.token = "test_token"
        headers = self.data.get_standard_headers()
        assert headers["accessToken"] == "Bearer test_token"
        assert headers["accept"] == "application/json"

    async def test_refresh_token_skipped(self):
        """
        Test that refresh_token skips refreshing if the token is still valid.
        """
        self.data.token = "valid_token"
        with patch.object(self.data, 'get_authen_token', new=AsyncMock()) as mock_get_authen_token:
            await self.data.refresh_token()

    async def test_two_instances(self):
        """
        Test that two instances of IOPGPSData are created with different entry names.
        """
        entry_name_1 = "test_entry_1"
        entry_name_2 = "test_entry_2"
        user_1 = "user_1@email.com"
        user_2 = "user_2@email.com"
        key_1 = "key_1"
        key_2 = "key_2"

        iopgps_data.IOPGPSData.clean_instances()
        data_1 = iopgps_data.IOPGPSData.get_instance("guid1", entry_name_1, user_1, key_1)
        data_2 = iopgps_data.IOPGPSData.get_instance("guid2", entry_name_2, user_2, key_2)
        assert data_1 is not data_2
        assert data_1.guid != data_2.guid
        assert data_1.entry_name != data_2.entry_name
        assert data_1.user != data_2.user
        assert data_1.key != data_2.key

    async def test_singleton(self):
        """
        Test that only one instance of IOPGPSData is created with the same entry name.
        """
        entry_name = "test_entry"
        user = "user@email.com"
        key = "password"
        iopgps_data.IOPGPSData.clean_instances()
        data_1 = iopgps_data.IOPGPSData.get_instance("guid1", entry_name, user, key)
        data_2 = iopgps_data.IOPGPSData.get_instance("guid1", entry_name, user, key)
        assert data_1 is data_2
        assert data_1.guid == data_2.guid
        assert data_1.entry_name == data_2.entry_name
        assert data_1.user == data_2.user
        assert data_1.key == data_2.key
        # Test if changes in one instance are reflected in the other
        data_1.token = "should_be_same_token"
        assert data_2.token == "should_be_same_token"

    async def test_update_data(self):
        """
        Test the update_position_data method.
        """
        await self.data.refresh_token()
        await self.data.update_devices_data()
        assert self.data.devices is not None
        assert len(self.data.devices) > 0
        for dev in self.data.devices:
            assert dev.name is not None
            assert dev.imei is not None

        assert self.data.get_device_ids() is not None
        assert len(self.data.get_device_ids()) > 0

        await self.data.update_position_data()
        assert self.data.positions is not None
        assert len(self.data.positions) > 0
        for pos in self.data.positions:
            assert pos.lat is not None
            assert pos.lng is not None
