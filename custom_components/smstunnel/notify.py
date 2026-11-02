"""Notify platform for SMSTunnel."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_TARGET,
    BaseNotificationService,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_DEFAULT_COUNTRY_CODE,
    CONF_DEVICE_ID,
    CONF_RECIPIENTS,
    DATA_CONFIG,
    DATA_SERVICE,
    DOMAIN,
    MAX_MESSAGE_LENGTH,
    PATH_SEND,
    REQUEST_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> SmsTunnelNotificationService | None:
    """Return the notify service."""
    if discovery_info is None:
        return None

    entry_id = discovery_info["entry_id"]
    entry_data = hass.data.get(DOMAIN, {}).get(entry_id)
    if not entry_data:
        # Intrarea a fost stearsa inainte sa ajunga platforma aici.
        return None

    service = SmsTunnelNotificationService(hass, entry_id, entry_data[DATA_CONFIG])
    # Tinut minte ca sa fie scos la stergerea intrarii (async_unload_entry).
    entry_data[DATA_SERVICE] = service
    return service


class SmsTunnelNotificationService(BaseNotificationService):
    """Send SMS through SMSTunnel."""

    def __init__(
        self, hass: HomeAssistant, entry_id: str, config: dict[str, Any]
    ) -> None:
        """Initialise the service."""
        self.hass = hass
        self._entry_id = entry_id
        self._api_key: str = config[CONF_API_KEY]
        self._base_url: str = config[CONF_BASE_URL].rstrip("/")
        self._recipients: list[str] = config[CONF_RECIPIENTS]
        self._country_code: str | None = config.get(CONF_DEFAULT_COUNTRY_CODE)
        self._device_id: str | None = config.get(CONF_DEVICE_ID)

    async def async_send_message(self, message: str = "", **kwargs: Any) -> None:
        """Send an SMS to the configured recipients (or to `target`)."""
        # Serviciul unei intrari sterse sau reincarcate (de ex. chiar cand
        # actiunea se inregistra): cheia lui nu mai trimite nimic.
        entry_data = self.hass.data.get(DOMAIN, {}).get(self._entry_id)
        if not entry_data or entry_data[DATA_SERVICE] is not self:
            _LOGGER.warning("SMSTunnel: this integration was removed, nothing sent")
            return

        if not message:
            _LOGGER.warning("SMSTunnel: empty message, nothing sent")
            return

        # `target` permite suprascrierea destinatarilor la apel,
        # util pentru automatizari care aleg destinatarul dinamic.
        targets: list[str] = kwargs.get(ATTR_TARGET) or self._recipients
        if isinstance(targets, str):
            targets = [targets]

        data: dict[str, Any] = kwargs.get(ATTR_DATA) or {}

        # Titlul e optional in HA; il prefixam ca sa nu se piarda informatia.
        title = kwargs.get("title")
        text = f"{title}: {message}" if title else message

        if len(text) > MAX_MESSAGE_LENGTH:
            _LOGGER.warning(
                "SMSTunnel: message truncated from %s to %s characters",
                len(text),
                MAX_MESSAGE_LENGTH,
            )
            text = text[: MAX_MESSAGE_LENGTH - 1] + "…"

        session = async_get_clientsession(self.hass)

        for number in targets:
            payload: dict[str, Any] = {"to": number, "message": text}

            device_id = data.get("device_id") or self._device_id
            if device_id:
                payload["deviceId"] = device_id

            country_code = data.get("default_country_code") or self._country_code
            if country_code:
                payload["defaultCountryCode"] = country_code

            try:
                async with session.post(
                    f"{self._base_url}{PATH_SEND}",
                    json=payload,
                    headers={
                        "X-API-Key": self._api_key,
                        "Content-Type": "application/json",
                    },
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                ) as resp:
                    if resp.status == 429:
                        # 30 de cereri/minut in API. Merita spus explicit,
                        # altfel pare ca s-a pierdut mesajul fara motiv.
                        _LOGGER.error(
                            "SMSTunnel: rate limit reached (30 requests/minute). "
                            "Message to %s was not sent",
                            number,
                        )
                        continue

                    if resp.status >= 400:
                        body = await resp.text()
                        _LOGGER.error(
                            "SMSTunnel: sending to %s failed (HTTP %s): %s",
                            number,
                            resp.status,
                            body[:200],
                        )
                        continue

                    _LOGGER.debug("SMSTunnel: message sent to %s", number)

            except aiohttp.ClientError as err:
                # Un destinatar picat nu trebuie sa-i blocheze pe ceilalti.
                _LOGGER.error("SMSTunnel: connection error sending to %s: %s", number, err)
            except TimeoutError:
                _LOGGER.error("SMSTunnel: timeout sending to %s", number)
