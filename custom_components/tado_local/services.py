"""Services for Tado Local """

from __future__ import annotations

import logging
import aiohttp
from typing import Any, Dict

from homeassistant.core import  HomeAssistant, ServiceCall
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, CONF_IP_ADDRESS, CONF_PORT, CONF_UPDATE_INTERVAL, PLATFORMS

_LOGGER = logging.getLogger(__name__)

async def async_setup_services(
    hass: HomeAssistant, coordinator: DataUpdateCoordinator, base_url: str
) -> None:
    """Set up the services for Tado Local."""

    async def _async_send_zone_update(zone_id, temperature):
        url = f"{base_url}/zones/{zone_id}/set"
        params = {"temperature": str(temperature)}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, params=params) as response:
                    if response.status != 200:
                        _LOGGER.error("Errore update Tado: %s", await response.text())
                        
            except Exception as err:
                _LOGGER.error("Errore connessione update: %s", err)

    async def handle_resume_schedules(call: ServiceCall) -> None:
        """Service to resume all schedules."""
        _LOGGER.debug("Service call: resume_all_schedules")
        current_data = coordinator.data
        zones_list = current_data.get("zones", [])
        for zone in zones_list:
            zid = zone.get("zone_id") or zone.get("id")
            await _async_send_zone_update(zid, -1)

        await coordinator.async_request_refresh()

    async def handle_turn_off_all(call: ServiceCall) -> None:
        """Service to turn off all zones."""
        _LOGGER.debug("Service call: turn_off_all_zones")
        current_data = coordinator.data
        zones_list = current_data.get("zones", [])
        for zone in zones_list:
            zid = zone.get("zone_id") or zone.get("id")
            await _async_send_zone_update(zid, 0)

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
    