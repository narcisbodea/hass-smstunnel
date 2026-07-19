"""Config flow for the SMSTunnel integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_DEFAULT_COUNTRY_CODE,
    CONF_DEVICE_ID,
    CONF_RECIPIENTS,
    DEFAULT_BASE_URL,
    DEFAULT_NAME,
    DOMAIN,
    PATH_USAGE,
    REQUEST_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_RECIPIENTS): str,
        vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
        vol.Optional(CONF_DEFAULT_COUNTRY_CODE): str,
        vol.Optional(CONF_DEVICE_ID): str,
    }
)


def parse_recipients(raw: str) -> list[str]:
    """Split a comma/semicolon/newline separated list into clean numbers."""
    parts = raw.replace(";", ",").replace("\n", ",").split(",")
    return [p.strip() for p in parts if p.strip()]


class SmsTunnelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the SMSTunnel configuration flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            recipients = parse_recipients(user_input[CONF_RECIPIENTS])
            base_url = user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL).rstrip("/")

            if not recipients:
                errors[CONF_RECIPIENTS] = "no_recipients"
            else:
                # Validam cheia inainte de a salva, ca sa nu descopere
                # utilizatorul abia la prima alerta ca nu merge.
                error = await self._async_validate(base_url, user_input[CONF_API_KEY])
                if error:
                    errors["base"] = error

            if not errors:
                data = {
                    CONF_API_KEY: user_input[CONF_API_KEY],
                    CONF_BASE_URL: base_url,
                    CONF_RECIPIENTS: recipients,
                }
                if user_input.get(CONF_DEFAULT_COUNTRY_CODE):
                    data[CONF_DEFAULT_COUNTRY_CODE] = user_input[
                        CONF_DEFAULT_COUNTRY_CODE
                    ].strip()
                if user_input.get(CONF_DEVICE_ID):
                    data[CONF_DEVICE_ID] = user_input[CONF_DEVICE_ID].strip()

                await self.async_set_unique_id(f"{base_url}::{recipients[0]}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=DEFAULT_NAME, data=data)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def _async_validate(self, base_url: str, api_key: str) -> str | None:
        """Return an error key if the credentials cannot be used."""
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                f"{base_url}{PATH_USAGE}",
                headers={"X-API-Key": api_key},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                if resp.status in (401, 403):
                    return "invalid_auth"
                if resp.status >= 400:
                    _LOGGER.debug("SMSTunnel validation failed: HTTP %s", resp.status)
                    return "cannot_connect"
        except aiohttp.ClientError as err:
            _LOGGER.debug("SMSTunnel validation error: %s", err)
            return "cannot_connect"
        except TimeoutError:
            return "cannot_connect"

        return None
