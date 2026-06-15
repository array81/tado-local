import logging
from urllib.parse import urlparse
from homeassistant.core import HomeAssistant
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.network import get_url

from .const import DOMAIN, MANUFACTURER, format_model, MASTER_DEVICE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Configura i sensori binari Tado Local."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    base_url = data["base_url"]
    
    # if the base_url contains localhost, replace it with the actual HA host to ensure connectivity from other devices
    if "localhost" in base_url:
        ha_host = urlparse(get_url(hass)).hostname
        base_url = base_url.replace("localhost", ha_host)
    
    entities = []
    
    zones = coordinator.data.get("zones", [])
    for zone in zones:
        entities.append(TadoZoneHeating(coordinator, zone))
        entities.append(TadoZoneOpenWindow(coordinator, zone))
        if zone.get("zone_type", "HEATING") == "AIR_CONDITIONING":
            entities.append(TadoZoneCooling(coordinator, zone))
        
    devices = coordinator.data.get("devices", [])
    for device in devices:
        dev_type = device.get("device_type", "Device")
        if dev_type == MASTER_DEVICE:
            # Add TadoLocal status fields to MASTER_DEVICE (internet bridge) entity
            entities.append(TadoBridgeConnected(coordinator, device))
            entities.append(TadoCloudEnbled(coordinator, device))
            entities.append(TadoCloudAuthtenticated(coordinator, device, base_url))
        else:
            # The internet bridge does not have a battery
            entities.append(TadoDeviceBattery(coordinator, device))

    async_add_entities(entities)


class TadoZoneHeating(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:radiator"
    _attr_translation_key = "heating_active"

    def __init__(self, coordinator, zone_data):
        super().__init__(coordinator)
        self._zone_id = zone_data.get("zone_id") or zone_data.get("id")
        self._zone_name = zone_data.get("name")
        self._attr_unique_id = f"tado_local_heating_{self._zone_id}"
        self._tado_zone_id = zone_data.get("tado_zone_id", "")

    @property
    def device_info(self):
        return {
            "configuration_url": f"https://app.tado.com/en/main/home/zoneV2/{self._tado_zone_id}/",
            "identifiers": {(DOMAIN, "zone", self._zone_id)},
            "name": self._zone_name,
            "manufacturer": MANUFACTURER,
            "model": format_model("zone_control"),
        }

    @property
    def is_on(self):
        zones = self.coordinator.data.get("zones", [])
        for zone in zones:
            zid = zone.get("zone_id") or zone.get("id")
            if zid == self._zone_id:
                state = zone.get("state", zone)
                val = state.get("cur_heating", 0)
                # cur_heating can be 0=off, 1=heating, 2=cooling
                return val == 1
        return False
    
class TadoZoneCooling(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:air-conditioner"
    _attr_translation_key = "cooling_active"

    def __init__(self, coordinator, zone_data):
        super().__init__(coordinator)
        self._zone_id = zone_data.get("zone_id") or zone_data.get("id")
        self._zone_name = zone_data.get("name")
        self._attr_unique_id = f"tado_local_cooling_{self._zone_id}"
        self._tado_zone_id = zone_data.get("tado_zone_id", "")

    @property
    def device_info(self):
        return {
            "configuration_url": f"https://app.tado.com/en/main/home/zoneV2/{self._tado_zone_id}/",
            "identifiers": {(DOMAIN, "zone", self._zone_id)},
            "name": self._zone_name,
            "manufacturer": MANUFACTURER,
            "model": format_model("zone_control"),
        }

    @property
    def is_on(self):
        zones = self.coordinator.data.get("zones", [])
        for zone in zones:
            zid = zone.get("zone_id") or zone.get("id")
            if zid == self._zone_id:
                state = zone.get("state", zone)
                val = state.get("cur_heating", 0)
                # cur_heating can be 0=off, 1=heating, 2=cooling
                return val == 2
        return False


class TadoZoneOpenWindow(CoordinatorEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.WINDOW
    _attr_has_entity_name = True
    _attr_translation_key = "open_window"

    def __init__(self, coordinator, zone_data):
        super().__init__(coordinator)
        self._zone_id = zone_data.get("zone_id") or zone_data.get("id")
        self._zone_name = zone_data.get("name")
        self._attr_unique_id = f"tado_local_window_{self._zone_id}"
        self._tado_zone_id = zone_data.get("tado_zone_id", "")

    @property
    def device_info(self):
        return {
            "configuration_url": f"https://app.tado.com/en/main/home/zoneV2/{self._tado_zone_id}/",
            "identifiers": {(DOMAIN, "zone", self._zone_id)},
            "name": self._zone_name,
            "manufacturer": MANUFACTURER,
            "model": format_model("zone_control"),
        }

    @property
    def is_on(self):
        zones = self.coordinator.data.get("zones", [])
        for zone in zones:
            zid = zone.get("zone_id") or zone.get("id")
            if zid == self._zone_id:
                state = zone.get("state", zone)
                return state.get("window_open", False)
        return False


class TadoDeviceBattery(CoordinatorEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.BATTERY
    _attr_has_entity_name = True
    _attr_translation_key = "battery_low"

    def __init__(self, coordinator, device_data):
        super().__init__(coordinator)
        self._device_id = device_data.get("device_id") or device_data.get("id")
        self._serial = device_data.get("serial_number")
        if not self._serial:
            self._serial = f"Unknown_{self._device_id}"

        self._attr_unique_id = f"tado_local_batt_{self._device_id}"
        
        via_device = None
        zone_id = device_data.get("zone_id")
        if zone_id:
            via_device = (DOMAIN, "zone", zone_id)

        raw_model = device_data.get("device_type", "Device")
        model = device_data.get("model")
        if model:
            raw_model += " " + model
        sw_version = device_data.get("firmware_version", None) 

        self._device_info_data = {
            "configuration_url": f"https://app.tado.com/en/main/settings/home/rooms-and-devices/device/{self._serial}",
            "identifiers": {(DOMAIN, "device", self._device_id)},
            "name": f"Tado {self._serial}",
            "manufacturer": MANUFACTURER,
            "model": format_model(raw_model),
            "via_device": via_device,
            "sw_version": sw_version,
            "serial_number": self._serial
        }

    @property
    def device_info(self):
        return self._device_info_data

    @property
    def is_on(self):
        devices = self.coordinator.data.get("devices", [])
        for dev in devices:
            did = dev.get("device_id") or dev.get("id")
            if did == self._device_id:
                state = dev.get("state", dev)
                return state.get("battery_low", False)
        return False

class TadoBridgeConnected(CoordinatorEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_icon = "mdi:lan-connect"
    _attr_translation_key = "bridge_connected"

    def __init__(self, coordinator, device_data):
        super().__init__(coordinator)
        self._device_id = device_data.get("device_id") or device_data.get("id")
        self._attr_unique_id = f"tado_local_bridge_{self._device_id}"
        self._device_info_data = {
            "identifiers": {(DOMAIN, "device", self._device_id)}
        }

    @property
    def device_info(self):
        return self._device_info_data

    @property
    def is_on(self):
        status = self.coordinator.data.get("status", None)
        if not status:
            return False
        return status.get("bridge_connected", False)

class TadoCloudEnbled(CoordinatorEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_icon = "mdi:cloud-check-variant"
    _attr_translation_key = "cloud_api_enabled"

    def __init__(self, coordinator, device_data):
        super().__init__(coordinator)
        self._device_id = device_data.get("device_id") or device_data.get("id")
        self._attr_unique_id = f"tado_local_cloud_{self._device_id}"
        self._device_info_data = {
            "identifiers": {(DOMAIN, "device", self._device_id)}
        }

    @property
    def device_info(self):
        return self._device_info_data

    @property
    def is_on(self):
        status = self.coordinator.data.get("status", None)
        if not status:
            return False
        api = status.get("cloud_api", None)
        if not api:
            return False
        return api.get("enabled", False)

class TadoCloudAuthtenticated(CoordinatorEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_icon = "mdi:cloud-key"
    _attr_translation_key = "cloud_api_authenticated"

    def __init__(self, coordinator, device_data, base_url):
        super().__init__(coordinator)
        self._device_id = device_data.get("device_id") or device_data.get("id")
        self._attr_unique_id = f"tado_local_auth{self._device_id}"
        self._base_url = base_url
        self._device_info_data = {
            "identifiers": {(DOMAIN, "device", self._device_id)},
            "configuration_url": self._base_url
        }

    @property
    def device_info(self):
        return self._device_info_data

    @property
    def is_on(self):
        status = self.coordinator.data.get("status", None)
        if not status:
            return False
        api = status.get("cloud_api", None)
        if not api:
            return False
        return api.get("authenticated", False)