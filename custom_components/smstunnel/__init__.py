"""The SMSTunnel integration.

Sends SMS through your own Android phone, using your own SIM card, via the
SMSTunnel service. Set up from the UI; exposes a notify service.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Integrarea expune doar serviciul de notificare.
PLATFORMS: list[Platform] = [Platform.NOTIFY]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SMSTunnel from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = dict(entry.data)

    # Platforma notify (legacy) nu se incarca prin async_forward_entry_setups,
    # ci prin discovery, primind entry_id-ul ca sa isi ia configuratia.
    hass.async_create_task(
        async_load_platform(
            hass,
            Platform.NOTIFY,
            DOMAIN,
            {"entry_id": entry.entry_id, "name": entry.title},
            hass.data[DOMAIN].get("yaml_config", {}),
        )
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
