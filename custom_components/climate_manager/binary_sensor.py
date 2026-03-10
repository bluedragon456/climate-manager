"""Binary sensor platform for Climate Manager."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DATA_MANAGER, DOMAIN, STATUS_UNAVAILABLE
from .entity import ClimateManagerEntity
from .manager import ClimateManager


@dataclass(frozen=True, kw_only=True)
class ClimateManagerBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Any


BINARY_SENSORS: tuple[ClimateManagerBinarySensorDescription, ...] = (
    ClimateManagerBinarySensorDescription(
        key="smart_control_active",
        translation_key="smart_control_active",
        value_fn=lambda manager: manager.config.smart_control_enabled and manager.runtime.status not in {STATUS_UNAVAILABLE, "paused"},
    ),
    ClimateManagerBinarySensorDescription(
        key="manual_override_active",
        translation_key="manual_override_active",
        value_fn=lambda manager: manager.runtime.manual_override_active,
    ),
    ClimateManagerBinarySensorDescription(
        key="windows_backoff_active",
        translation_key="windows_backoff_active",
        value_fn=lambda manager: manager.runtime.windows_backoff_active,
    ),
    ClimateManagerBinarySensorDescription(
        key="fail_safe_active",
        translation_key="fail_safe_active",
        value_fn=lambda manager: manager.runtime.status == STATUS_UNAVAILABLE,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors from a config entry."""
    manager: ClimateManager = hass.data[DOMAIN][entry.entry_id][DATA_MANAGER]
    async_add_entities(
        [ClimateManagerBinarySensor(entry.entry_id, manager, description) for description in BINARY_SENSORS]
    )


class ClimateManagerBinarySensor(ClimateManagerEntity, BinarySensorEntity):
    """Climate Manager binary sensor."""

    def __init__(
        self,
        entry_id: str,
        manager: ClimateManager,
        description: ClimateManagerBinarySensorDescription,
    ) -> None:
        super().__init__(entry_id, manager)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def is_on(self):
        return self.entity_description.value_fn(self._manager)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._manager.async_subscribe(self.async_write_ha_state))