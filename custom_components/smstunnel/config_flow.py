"""Config flow for the SMSTunnel integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

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
        # Cheia e secreta: camp de parola, afisat ca puncte (un camp "str"
        # ar arata cheia in clar pe ecran). Toate campurile sunt selectoare:
        # amestecate cu "str", Home Assistant 2026.10 arata "Required" sub
        # Recipients chiar de la deschiderea formularului.
        vol.Required(CONF_API_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Required(CONF_RECIPIENTS): TextSelector(),
        vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): TextSelector(),
        vol.Optional(CONF_DEFAULT_COUNTRY_CODE): TextSelector(),
        vol.Optional(CONF_DEVICE_ID): TextSelector(),
    }
)


# Schimbarea setarilor unei intrari existente. Cheia e optionala: lasata
# goala, ramane cea de acum (o cheie se vede o singura data in panou, deci
# nu o cerem din nou doar ca sa schimbe cineva un numar). Exceptie: cand se
# schimba adresa serverului, cheia trebuie scrisa din nou.
STEP_RECONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_API_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Required(CONF_RECIPIENTS): TextSelector(),
        vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): TextSelector(),
        vol.Optional(CONF_DEFAULT_COUNTRY_CODE): TextSelector(),
        vol.Optional(CONF_DEVICE_ID): TextSelector(),
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

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Change the settings of an entry without removing it."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry is None:
            return self.async_abort(reason="entry_not_found")

        # Toate intrarile SMSTunnel au aceeasi actiune, notify.smstunnel, si
        # doar una o tine. Schimbarea reincarca intrarea, iar la reincarcare
        # actiunea ar trece la cealalta intrare: alertele ar pleca spre alte
        # numere. Cu mai multe intrari incarcate nu schimbam nimic de aici.
        if any(
            other.entry_id != entry.entry_id
            and other.state is config_entries.ConfigEntryState.LOADED
            for other in self.hass.config_entries.async_entries(DOMAIN)
        ):
            return self.async_abort(reason="single_entry_only")

        errors: dict[str, str] = {}
        current = dict(entry.data)

        if user_input is not None:
            recipients = parse_recipients(user_input[CONF_RECIPIENTS])
            base_url = user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL).rstrip("/")
            typed_key = user_input.get(CONF_API_KEY)
            api_key = typed_key or current[CONF_API_KEY]
            same_server = base_url == current.get(
                CONF_BASE_URL, DEFAULT_BASE_URL
            ).rstrip("/")
            unique_id = f"{base_url}::{recipients[0]}" if recipients else None

            if not recipients:
                errors[CONF_RECIPIENTS] = "no_recipients"
            elif not typed_key and not same_server:
                # Cheia salvata a fost scrisa pentru serverul de acum. Nu o
                # trimitem niciodata la alta adresa: cine schimba serverul
                # scrie cheia din nou.
                errors[CONF_API_KEY] = "key_required_for_new_server"
            elif any(
                other.entry_id != entry.entry_id and other.unique_id == unique_id
                for other in self.hass.config_entries.async_entries(DOMAIN)
            ):
                # Aceeasi regula ca la adaugare: un server si un prim numar
                # apartin unei singure intrari.
                errors["base"] = "already_configured"
            else:
                # Cheia (noua, sau cea pastrata cand serverul e acelasi) e
                # verificata pe serverul ales, ca la adaugare: nimic nu se
                # salveaza daca nu merge.
                error = await self._async_validate(base_url, api_key)
                if error:
                    errors["base"] = error

            if not errors:
                data = {
                    CONF_API_KEY: api_key,
                    CONF_BASE_URL: base_url,
                    CONF_RECIPIENTS: recipients,
                }
                if user_input.get(CONF_DEFAULT_COUNTRY_CODE):
                    data[CONF_DEFAULT_COUNTRY_CODE] = user_input[
                        CONF_DEFAULT_COUNTRY_CODE
                    ].strip()
                if user_input.get(CONF_DEVICE_ID):
                    data[CONF_DEVICE_ID] = user_input[CONF_DEVICE_ID].strip()

                # Intrarea se reincarca singura cand i se schimba datele
                # (_async_update_listener din __init__.py), deci actiunea
                # notify.smstunnel foloseste setarile noi fara repornire.
                self.hass.config_entries.async_update_entry(
                    entry, data=data, unique_id=unique_id
                )
                return self.async_abort(reason="reconfigure_successful")

        # Formularul porneste de la setarile de acum (sau de la ce a scris
        # omul, daca a fost o eroare). Cheia nu e aratata niciodata.
        shown = user_input if user_input is not None else {
            CONF_RECIPIENTS: ", ".join(current.get(CONF_RECIPIENTS, [])),
            CONF_BASE_URL: current.get(CONF_BASE_URL, DEFAULT_BASE_URL),
            CONF_DEFAULT_COUNTRY_CODE: current.get(CONF_DEFAULT_COUNTRY_CODE),
            CONF_DEVICE_ID: current.get(CONF_DEVICE_ID),
        }
        suggested = {
            key: value
            for key, value in shown.items()
            if key != CONF_API_KEY and value
        }
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_RECONFIGURE_SCHEMA, suggested
            ),
            errors=errors,
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
