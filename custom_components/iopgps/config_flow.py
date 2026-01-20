"""Config flow for PAJ GPS Tracker integration."""
from __future__ import annotations
import logging
import uuid
from typing import Any, Dict, Optional
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from . import IOPGPSData
from .const import DOMAIN

big_int = vol.All(vol.Coerce(int), vol.Range(min=300))

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = vol.Schema(
            {
                vol.Required('entry_name', default='My Paj GPS Account'): cv.string,
                vol.Required('user', default=''): cv.string,
                vol.Required('key', default=''): cv.string,
            }
        )

class CustomFlow(config_entries.ConfigFlow, domain=DOMAIN):
    data: Optional[Dict[str, Any]]

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        errors: Dict[str, str] = {}
        if user_input is not None:
            self.data = user_input
            # Create new guid for the entry
            self.data['guid'] = str(uuid.uuid4())
            # If entry_name is null or empty string, add error
            if not self.data['entry_name'] or self.data['entry_name'] == '':
                errors['base'] = 'entry_name_required'
            # If user is null or empty string, add error
            if not self.data['user'] or self.data['user'] == '':
                errors['base'] = 'user_required'
            # If key is null or empty string, add error
            if not self.data['key'] or self.data['key'] == '':
                errors['base'] = 'key_required'
            if not errors:
                return self.async_create_entry(title=f"{self.data['entry_name']}", data=self.data)

        return self.async_show_form(step_id="user", data_schema=CONFIG_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry # type: ignore

    async def async_step_init(
        self, user_input: Dict[str, Any] = None # type: ignore
    ) -> Dict[str, Any]:
        errors: Dict[str, str] = {}

        default_entry_name = ''
        if 'entry_name' in self.config_entry.data:
            default_entry_name = self.config_entry.data['entry_name']
        if 'entry_name' in self.config_entry.options:
            default_entry_name = self.config_entry.options['entry_name']
        default_user = ''
        if 'user' in self.config_entry.data:
            default_user = self.config_entry.data['user']
        if 'user' in self.config_entry.options:
            default_user = self.config_entry.options['user']
        default_key = ''
        if 'key' in self.config_entry.data:
            default_key = self.config_entry.data['key']
        if 'key' in self.config_entry.options:
            default_key = self.config_entry.options['key']

        if user_input is not None:
            # If user is null or empty string, add error
            if not user_input['user'] or user_input['user'] == '':
                errors['base'] = 'user_required'
            # If key is null or empty string, add error
            if not user_input['key'] or user_input['key'] == '':
                errors['base'] = 'key_required'
            if not errors:
                # Update the config entry with the new data
                new_data = {
                    'guid': self.config_entry.data['guid'],
                    'entry_name': user_input['entry_name'],
                    'user': user_input['user'],
                    'key': user_input['key'],
                }

                # Get existing instance of PajGPSData
                iop_data = IOPGPSData.get_instance(
                    self.config_entry.data['guid'],
                    self.config_entry.data['entry_name'],
                    self.config_entry.data['user'],
                    self.config_entry.data['key'],
                )
                iop_data.entry_name = new_data['entry_name']
                iop_data.user = new_data['user']
                iop_data.key = new_data['key']
                self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
                await iop_data.refresh_token(True)
                await iop_data.async_update(True)

                # Rename the entry in the UI
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=new_data,
                    title=new_data['entry_name'],
                )

                return self.async_create_entry(title=f"{new_data['entry_name']}", data=new_data) # type: ignore



        OPTIONS_SCHEMA = vol.Schema(
            {
                vol.Required('entry_name', default=default_entry_name): cv.string,
                vol.Required('user', default=default_user): cv.string,
                vol.Required('key', default=default_key): cv.string,
            }
        )
        return self.async_show_form(step_id="init", data_schema=OPTIONS_SCHEMA, errors=errors) # type: ignore
