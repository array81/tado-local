"""Provides diagnostics for Tado Local."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN

async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a Tado Local config entry."""

    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    return {
        
        "data": _hide_sensitive_info(coordinator.data),
    }

def _hide_sensitive_info(data: Any) -> Any:
    """Recursively sanitize sensitive values in diagnostics data."""
    if isinstance(data, dict):
        return {
            key: _mask_serial_number(value)
            if key in ["leader_serial", "serial_number"]
            else "**secret**"
            if key in ["home_id", "uuid"]
            else _hide_sensitive_info(value)
            for key, value in data.items()
        }

    if isinstance(data, list):
        return [_hide_sensitive_info(item) for item in data]

    return data

def _mask_serial_number(value: Any) -> Any:
    """Mask characters at positions 3 through 9 with 'x'."""
    if not isinstance(value, str):
        return value

    if len(value) < 3:
        return value

    start_index = 2
    end_index = min(9, len(value))

    return f"{value[:start_index]}{'x' * (end_index - start_index)}{value[end_index:]}"
