import logging
import aiohttp
from typing import Any, Dict

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    ClimateEntityFeature,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
    PRECISION_TENTHS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, MANUFACTURER, format_model

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Configura le entità Climate."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    base_url = data["base_url"]

    entities = []
    zones_list = coordinator.data.get("zones", [])
    
    for zone in zones_list:
        entities.append(TadoLocalClimate(coordinator, zone, base_url))

    async_add_entities(entities)


class TadoLocalClimate(CoordinatorEntity, ClimateEntity):
    """Rappresentazione di una Zona Tado Local."""

    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = PRECISION_TENTHS
    
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE 
        | ClimateEntityFeature.TURN_OFF 
        | ClimateEntityFeature.TURN_ON
    )
    
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF, HVACMode.AUTO]

    def __init__(self, coordinator, initial_data, base_url):
        super().__init__(coordinator)
        self._zone_id = initial_data.get("zone_id") or initial_data.get("id")
        self._attr_name = "" # remove double name from Climate control 
        self._device_name = initial_data.get("name", f"Zone {self._zone_id}")
        self._attr_unique_id = f"tado_local_zone_{self._zone_id}"
        self._base_url = base_url

    @property
    def device_info(self):
        """Device Info per la Zona Logica."""
        return {
            "identifiers": {(DOMAIN, "zone", self._zone_id)},
            "name": self._device_name,
            "manufacturer": MANUFACTURER,
            "model": format_model("zone_control"), # Usa "Zone Control" formattato
        }

    @property
    def _zone_data(self) -> dict:
        raw_data = self.coordinator.data
        zones_list = raw_data.get("zones", [])
        for zone in zones_list:
            zid = zone.get("zone_id") or zone.get("id")
            if zid == self._zone_id:
                return zone.get("state", zone)
        return {}

    @property
    def current_temperature(self):
        return self._zone_data.get("cur_temp_c")

    @property
    def target_temperature(self):
        return self._zone_data.get("target_temp_c")

    @property
    def hvac_mode(self) -> HVACMode:
        mode = self._zone_data.get("mode") 
        if mode == 0:
            return HVACMode.OFF
        return HVACMode.HEAT

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        temp_param = None
        if hvac_mode == HVACMode.OFF:
            temp_param = 0
        elif hvac_mode == HVACMode.AUTO:
            temp_param = -1
        elif hvac_mode == HVACMode.HEAT:
            target = self.target_temperature
            if target is None or target < 5:
                target = 21
            temp_param = target

        if temp_param is not None:
            await self._async_send_zone_update(temp_param)

    async def async_set_temperature(self, **kwargs) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        await self._async_send_zone_update(temp)

    async def _async_send_zone_update(self, temperature):
        url = f"{self._base_url}/zones/{self._zone_id}/set"
        params = {"temperature": str(temperature)}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, params=params) as response:
                    if response.status != 200:
                        _LOGGER.error("Errore update Tado: %s", await response.text())
                    else:
                        await self.coordinator.async_request_refresh()
            except Exception as err:
                _LOGGER.error("Errore connessione update: %s", err)