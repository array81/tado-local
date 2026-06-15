"""Services for Tado Local """

from __future__ import annotations

import logging
import aiohttp

from homeassistant.core import  HomeAssistant, ServiceCall
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_services(
    hass: HomeAssistant, coordinator: DataUpdateCoordinator, base_url: str
) -> None:
    """Set up the services for Tado Local."""

    async def _async_send_all_zones_update(heating_enabled: bool, persistent: bool):
        url = f"{base_url}/zones/set"
        params = {
            "heating_enabled": "true" if heating_enabled else "false",
            "persistant": "true" if persistent else "false",
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, params=params) as response:
                    if response.status != 200:
                        _LOGGER.error("Errore update Tado: %s", await response.text())
                        
            except Exception as err:
                _LOGGER.error("Errore connessione update: %s", err)

    async def handle_resume_schedules(call: ServiceCall) -> None:
        """Service to resume all schedules."""
        persistent = call.data.get("persistent", False)
        _LOGGER.debug("Service call: resume_all_schedules(persistent=%s)", persistent)
        await _async_send_all_zones_update(True, persistent)
        await coordinator.async_request_refresh()

    async def handle_turn_off_all(call: ServiceCall) -> None:
        """Service to turn off all zones."""
        persistent = call.data.get("persistent", False)
        _LOGGER.debug("Service call: turn_off_all_zones(persistent=%s)", persistent)
        await _async_send_all_zones_update(False, persistent)
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN, "resume_all_schedules", handle_resume_schedules
    )
    hass.services.async_register(
        DOMAIN, "turn_off_all_zones", handle_turn_off_all
    )

async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Tado Local services."""
    hass.services.async_remove(DOMAIN, "resume_all_schedules")
    hass.services.async_remove(DOMAIN, "turn_off_all_zones")
    