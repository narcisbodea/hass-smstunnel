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

from .const import DATA_CONFIG, DATA_SERVICE, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Integrarea expune doar serviciul de notificare.
PLATFORMS: list[Platform] = [Platform.NOTIFY]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SMSTunnel from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    # Serviciul notify se adauga aici cand notify.py il creeaza.
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_CONFIG: dict(entry.data),
        DATA_SERVICE: None,
    }

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
    """Unload a config entry: its notify action stops at once."""
    entries = hass.data.get(DOMAIN, {})
    entry_data = entries.pop(entry.entry_id, None)
    service = entry_data[DATA_SERVICE] if entry_data else None

    # Home Assistant nu descarca platformele notify legacy: fara asta,
    # notify.smstunnel trimitea mai departe, cu cheia intrarii sterse, pana la
    # repornire. notify.async_reset_platform nu e o varianta: opreste
    # descoperirea notify pentru toate celelalte integrari.
    # registered_targets apare in async_setup al lui Home Assistant, chiar
    # inainte de inregistrarea actiunii; fara el, actiunea nu exista inca.
    if service is not None and hasattr(service, "registered_targets"):
        await service.async_unregister_services()

        # Toate intrarile SMSTunnel au aceeasi actiune, notify.smstunnel, si
        # doar prima o inregistreaza: daca era a celei sterse, o preia alta.
        for other in entries.values():
            other_service = other[DATA_SERVICE]
            if other_service is not None and hasattr(
                other_service, "registered_targets"
            ):
                await other_service.async_register_services()
                break

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
