import asyncio
import logging
import json
import aiohttp
import async_timeout
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .services import async_setup_services
from .const import DOMAIN, CONF_IP_ADDRESS, CONF_PORT, CONF_UPDATE_INTERVAL, PLATFORMS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura l'integrazione da una config entry."""
    
    # Legge dai dati iniziali o dalle opzioni modificate
    config = entry.options if entry.options else entry.data
    
    ip = config.get(CONF_IP_ADDRESS, entry.data.get(CONF_IP_ADDRESS))
    port = config.get(CONF_PORT, entry.data.get(CONF_PORT))
    interval = config.get(CONF_UPDATE_INTERVAL, entry.data.get(CONF_UPDATE_INTERVAL))
    
    base_url = f"http://{ip}:{port}"

    async def async_get_data():
        """Polling di backup: scarica dati completi (Zone + Device)."""
        async with aiohttp.ClientSession() as session:
            try:
                async with async_timeout.timeout(15):
                    # Zone
                    async with session.get(f"{base_url}/zones") as resp_zones:
                        if resp_zones.status != 200:
                            raise UpdateFailed(f"Errore API Zones: {resp_zones.status}")
                        zones_json = await resp_zones.json()

                    # Device
                    async with session.get(f"{base_url}/devices") as resp_devices:
                        if resp_devices.status != 200:
                            raise UpdateFailed(f"Errore API Devices: {resp_devices.status}")
                        devices_json = await resp_devices.json()

                    # Server status
                    async with session.get(f"{base_url}/status") as resp_status:
                        if resp_status.status != 200:
                            raise UpdateFailed(f"Errore API Status: {resp_status.status}")
                        status_info = await resp_status.json()

                    zones_list = zones_json.get("zones", zones_json) if isinstance(zones_json, dict) else zones_json
                    devices_list = devices_json.get("devices", devices_json) if isinstance(devices_json, dict) else devices_json

                    return {
                        "zones": zones_list,
                        "devices": devices_list,
                        "status": status_info
                    }

            except Exception as err:
                raise UpdateFailed(f"Errore di connessione: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="tado_local_data",
        update_method=async_get_data,
        update_interval=timedelta(seconds=interval),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "base_url": base_url,
    }

    # Avviamo il background task per gli eventi SSE (Push)
    entry.async_create_background_task(
        hass, 
        sse_listener(hass, coordinator, base_url), 
        "tado_local_sse_listener"
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Listener per ricaricare se le opzioni cambiano
    entry.async_on_unload(entry.add_update_listener(update_listener))

    await async_setup_services(hass, coordinator, base_url)
    
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Ricarica l'integrazione quando le opzioni cambiano."""
    await hass.config_entries.async_reload(entry.entry_id)

async def sse_listener(hass: HomeAssistant, coordinator: DataUpdateCoordinator, base_url: str):
    """Ascolta lo stream SSE."""
    url = f"{base_url}/events"
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=None) as response:
                    async for line in response.content:
                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data:"):
                            json_str = line_str[5:].strip()
                            try:
                                event_data = json.loads(json_str)
                                handle_event(coordinator, event_data)
                            except json.JSONDecodeError:
                                pass
        except Exception:
            await asyncio.sleep(10)

def handle_event(coordinator: DataUpdateCoordinator, event: dict):
    """Aggiorna i dati locali."""
    event_type = event.get("type")
    current_data = coordinator.data
    zones_list = current_data.get("zones", [])
    devices_list = current_data.get("devices", [])
    updated = False

    if event_type == "zone":
        zone_id = event.get("zone_id")
        new_state = event.get("state")
        if zone_id and new_state:
            for zone in zones_list:
                zid = zone.get("zone_id") or zone.get("id")
                if zid == zone_id:
                    zone["state"] = new_state
                    updated = True
                    break

    elif event_type == "device":
        device_id = event.get("device_id")
        new_state = event.get("state")
        if device_id and new_state:
            for device in devices_list:
                did = device.get("device_id") or device.get("id")
                if did == device_id:
                    device["state"] = new_state
                    updated = True
                    break

    if updated:
        coordinator.async_set_updated_data({
            "zones": zones_list,
            "devices": devices_list
        })

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok