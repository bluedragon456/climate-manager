"""Runtime state storage for Climate Manager."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import STORAGE_KEY, STORAGE_VERSION
from .models import RuntimeState

_DATETIME_FIELDS = {
    "manual_override_until",
    "last_command_time",
    "windows_open_since",
    "windows_closed_since",
}


class RuntimeStore:
    """Persist runtime state."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store[dict[str, Any]](hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry_id}")

    async def async_load(self) -> RuntimeState:
        """Load runtime state from storage."""
        data = await self._store.async_load() or {}
        for field in _DATETIME_FIELDS:
            value = data.get(field)
            if value:
                try:
                    data[field] = dt_util.parse_datetime(value)
                except (TypeError, ValueError):
                    data[field] = None
        return RuntimeState(**data)

    async def async_save(self, runtime: RuntimeState) -> None:
        """Save runtime state to storage."""
        data = asdict(runtime)
        for field in _DATETIME_FIELDS:
            value = data.get(field)
            if isinstance(value, datetime):
                data[field] = value.isoformat()
        await self._store.async_save(data)
