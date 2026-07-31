"""Runtime state storage for Climate Manager."""
from __future__ import annotations

from dataclasses import asdict, fields
from datetime import datetime
import hashlib
import json
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import STORAGE_KEY, STORAGE_VERSION
from .models import RuntimeState

_DATETIME_FIELDS = {
    "manual_override_started_at",
    "manual_override_until",
    "last_command_time",
    "windows_open_since",
    "windows_closed_since",
    "windows_backoff_until",
    "windows_backoff_activated_at",
    "windows_safety_activated_at",
    "windows_safety_cleared_at",
}
_OWNERSHIP_TIMESTAMP_FIELDS = {
    "manual_override_started_at",
    "windows_backoff_activated_at",
}


class RuntimeStore:
    """Persist runtime state."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store[dict[str, Any]](hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry_id}")
        self._ownership_store = Store[dict[str, Any]](
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}_{entry_id}_ownership",
        )

    @staticmethod
    def _fingerprint(data: dict[str, Any]) -> str:
        """Return a stable fingerprint for the primary runtime payload."""
        serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode()).hexdigest()

    async def async_load(self) -> RuntimeState:
        """Load runtime state from storage."""
        data = dict(await self._store.async_load() or {})
        ownership = dict(await self._ownership_store.async_load() or {})
        primary_fingerprint = self._fingerprint(data)
        if ownership.get("primary_fingerprint") == primary_fingerprint:
            for field in _OWNERSHIP_TIMESTAMP_FIELDS:
                data[field] = ownership.get(field)
        for field in _DATETIME_FIELDS:
            value = data.get(field)
            if value:
                try:
                    data[field] = dt_util.parse_datetime(value)
                except (TypeError, ValueError):
                    data[field] = None
        runtime_fields = {item.name for item in fields(RuntimeState)}
        return RuntimeState(
            **{
                field_name: value
                for field_name, value in data.items()
                if field_name in runtime_fields
            }
        )

    async def async_save(self, runtime: RuntimeState) -> None:
        """Save runtime state to storage."""
        data = asdict(runtime)
        ownership_timestamps = {
            field: data.pop(field, None) for field in _OWNERSHIP_TIMESTAMP_FIELDS
        }
        for field in _DATETIME_FIELDS:
            value = data.get(field)
            if isinstance(value, datetime):
                data[field] = value.isoformat()
        await self._store.async_save(data)
        for field, value in ownership_timestamps.items():
            if isinstance(value, datetime):
                ownership_timestamps[field] = value.isoformat()
        await self._ownership_store.async_save(
            {
                **ownership_timestamps,
                "primary_fingerprint": self._fingerprint(data),
            }
        )
