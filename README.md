#  IOPGPS Tracker Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

## Introduction
This is a fork of [PAJ GPS Tracker Integration for Home Assistant](https://github.com/skipperro/pajgps-homeassistant) but for [IOPGPS devices](https://www.iopgps.com/). 
This integration enables you to incorporate IOPGPS devices from https://www.iopgps.com/ into your Home Assistant setup.

## Disclaimer

- This integration is created without acknowledgement and support from IOPGPS; therefore, **this integration is not official software from IOPGPS**.<br>
- It's a custom integration created entirely by me (pruet), and thus IOPGPS is not responsible for any damage/issues caused by this integration, nor it offers any end-user support for it. Also, the use of this integration is at your own risk.
- I develop this integration solely for tracking my dogs (Kimmim and Maloon) on my HASSIO dashboard, so if you have the other use-cases and would like to contribute, I will be more than welcome to accept your code.

## Features
- [x] Device tracking (Longitude, Latitude)
- [x] Device battery level
- [x] Support for multiple accounts

## Planned features
- [ ] Device status (moving, stopped, etc.)
- [ ] Device speed
- [ ] Notifications (SOS, low battery, etc.)
- [ ] Elevation
- [ ] Geofencing

## Supported devices

While this integration was primarily tested with the **GPS30**, it leverages the standard API provided by IOPGPS. Therefore, it should be compatible with other IOPGPS devices. If you encounter any issues with different devices, please report them.
## Installation

1. **Make a proper setup of your IOPGPS device**. You need to have an account on https://www.iopgps.com/ and your device must be properly configured and connected to the platform. Also, you need to get access on API token (Your profile icon -> System Configuration -> API Key Request).
2. Install this integration with HACS (adding this repository may be required), or copy the contents of this
repository into the `custom_components/iopgps` directory.
2. Restart Home Assistant.
3. Start the configuration flow:
   - [![Start Config Flow](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=pajgps)
   - Or: Go to `Configuration` -> `Integrations` and click the `+ Add Integration`. Select `PAJ GPS` from the list.
   - If the integration is not found try to refresh the HA page without using cache (Ctrl+F5).
4. Provide your user name and API key you get from the website. This data will be saved only in your Home Assistant and is required to generate authorization token.
5. Device Tracker Entities will be created for all your devices.

## Configuration

The integration will automatically discover all your devices connected to your account on https://www.iopgps.com/. 
They will be added as entities to Home Assistant based on their ID from the API (not the number on the device).

There is no need to configure anything else.