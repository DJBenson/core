"""Config flow for evohome."""

from __future__ import annotations

import logging
from typing import Any

import evohomeasync2 as ec2
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import selector

from .const import CONF_LOCATION_IDX, DOMAIN, SCAN_INTERVAL_DEFAULT, SCAN_INTERVAL_MINIMUM
from .storage import TokenManager

_LOGGER = logging.getLogger(__name__)


class EvohomeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for evohome."""

    VERSION = 1

    async def async_step_import(self, user_input: dict | None = None):
        """Handle import from YAML."""
        if user_input is None:
            return self.async_abort(reason="import_failed")

        if CONF_USERNAME not in user_input or CONF_PASSWORD not in user_input:
            _LOGGER.error(
                "Invalid YAML configuration: missing required fields (username and/or password)"
            )
            return self.async_abort(reason="import_failed")

        # Check if already configured BEFORE the try block so the abort propagates
        await self.async_set_unique_id(user_input[CONF_USERNAME])
        self._abort_if_unique_id_configured()

        try:
            token_manager = TokenManager(
                self.hass,
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                async_get_clientsession(self.hass),
            )
            client = ec2.EvohomeClient(token_manager)

            await client.update(dont_update_status=True)

            location_idx = int(user_input.get(CONF_LOCATION_IDX, 0))
            num_locations = len(client.locations)
            if location_idx < 0 or location_idx >= num_locations:
                _LOGGER.error(
                    "Invalid location_idx in YAML: %s (valid range is 0-%s)",
                    location_idx,
                    num_locations - 1,
                )
                return self.async_abort(reason="invalid_location_idx")

            scan_interval = user_input.get(CONF_SCAN_INTERVAL)
            if scan_interval is None:
                scan_interval = int(SCAN_INTERVAL_DEFAULT.total_seconds())
            elif isinstance(scan_interval, dict):
                scan_interval = int(vol.Coerce(int)(scan_interval.get("seconds", 0)))
            elif hasattr(scan_interval, "total_seconds"):
                scan_interval = int(scan_interval.total_seconds())
            else:
                scan_interval = int(scan_interval)

            if scan_interval < int(SCAN_INTERVAL_MINIMUM.total_seconds()):
                _LOGGER.error(
                    "Invalid scan_interval in YAML: %s seconds (minimum is %s seconds)",
                    scan_interval,
                    int(SCAN_INTERVAL_MINIMUM.total_seconds()),
                )
                return self.async_abort(reason="invalid_scan_interval")

            data = {
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
                CONF_LOCATION_IDX: location_idx,
                CONF_SCAN_INTERVAL: scan_interval,
            }
            return self.async_create_entry(title=user_input[CONF_USERNAME], data=data)
        except Exception as err:
            _LOGGER.error("Error importing Evohome YAML config: %s", err)
            return self.async_abort(reason="import_failed")

    async def async_step_user(self, user_input: dict | None = None):
        """Handle the initial step."""
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_USERNAME])
            self._abort_if_unique_id_configured()

            data = {
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
                CONF_LOCATION_IDX: int(user_input[CONF_LOCATION_IDX]),
                CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
            }
            return self.async_create_entry(title=user_input[CONF_USERNAME], data=data)

        default_scan_interval = int(SCAN_INTERVAL_DEFAULT.total_seconds())
        min_scan_interval = int(SCAN_INTERVAL_MINIMUM.total_seconds())
        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): selector({"text": {}}),
                vol.Required(CONF_PASSWORD): selector({"text": {"type": "password"}}),
                vol.Optional(CONF_LOCATION_IDX, default=0): selector(
                    {"number": {"min": 0, "step": 1, "mode": "box"}}
                ),
                vol.Optional(CONF_SCAN_INTERVAL, default=default_scan_interval): selector(
                    {
                        "number": {
                            "min": min_scan_interval,
                            "step": 1,
                            "mode": "box",
                        }
                    }
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Handle the reconfigure step."""
        config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if config_entry is None:
            return self.async_abort(reason="reconfigure_failed")

        if user_input is not None:
            data = {
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
                CONF_LOCATION_IDX: int(user_input[CONF_LOCATION_IDX]),
                CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
            }
            return self.async_update_reload_and_abort(
                config_entry,
                data=data,
                reason="reconfigure_successful",
            )

        default_scan_interval = int(SCAN_INTERVAL_DEFAULT.total_seconds())
        min_scan_interval = int(SCAN_INTERVAL_MINIMUM.total_seconds())
        entry_data = config_entry.data
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_USERNAME, default=entry_data.get(CONF_USERNAME, "")
                ): selector({"text": {}}),
                vol.Required(
                    CONF_PASSWORD, default=entry_data.get(CONF_PASSWORD, "")
                ): selector({"text": {"type": "password"}}),
                vol.Optional(
                    CONF_LOCATION_IDX,
                    default=entry_data.get(CONF_LOCATION_IDX, 0),
                ): selector({"number": {"min": 0, "step": 1, "mode": "box"}}),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=entry_data.get(CONF_SCAN_INTERVAL, default_scan_interval),
                ): selector(
                    {
                        "number": {
                            "min": min_scan_interval,
                            "step": 1,
                            "mode": "box",
                        }
                    }
                ),
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
        )
