"""Sensor platform for Climate Manager."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DATA_MANAGER, DOMAIN
from .manager import ClimateManager


@dataclass(frozen=True, kw_only=True)
class ClimateManagerSensorDescription(SensorEntityDescription):
    value_fn: Any


SENSORS: tuple[ClimateManagerSensorDescription, ...] = (
    ClimateManagerSensorDescription(
        key="active_profile",
        translation_key="active_profile",
        value_fn=lambda manager: manager.runtime.active_profile,
    ),
    ClimateManagerSensorDescription(
        key="desired_hvac_mode",
        translation_key="desired_hvac_mode",
        value_fn=lambda manager: manager.runtime.desired_hvac_mode,
    ),
    ClimateManagerSensorDescription(
        key="target_heat",
        translation_key="target_heat",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        value_fn=lambda manager: manager.runtime.target_heat,
    ),
    ClimateManagerSensorDescription(
        key="target_cool",
        translation_key="target_cool",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        value_fn=lambda manager: manager.runtime.target_cool,
    ),
    ClimateManagerSensorDescription(
        key="comfort_offset",
        translation_key="comfort_offset",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        value_fn=lambda manager: manager.runtime.comfort_offset,
    ),
    ClimateManagerSensorDescription(
        key="status",
        translation_key="status",
        value_fn=lambda manager: manager.runtime.status,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    manager: ClimateManager = hass.data[DOMAIN][entry.entry_id][DATA_MANAGER]
    async_add_entities([ClimateManagerSensor(entry, manager, description) for description in SENSORS])


class ClimateManagerSensor(SensorEntity):
    """Climate Manager sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        entry: ConfigEntry,
        manager: ClimateManager,
        description: ClimateManagerSensorDescription,
    ) -> None:
        self.entity_description = description
        self._entry = entry
        self._manager = manager
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self):
        return self.entity_description.value_fn(self._manager)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._manager.async_subscribe(self.async_write_ha_state))
