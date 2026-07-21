"""Sensor platform for Climate Manager."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DATA_MANAGER, DOMAIN
from .entity import ClimateManagerEntity
from .helpers import round_temperature_for_unit, to_ha_temp, to_ha_temp_delta
from .manager import ClimateManager


@dataclass(frozen=True, kw_only=True)
class ClimateManagerSensorDescription(SensorEntityDescription):
    value_fn: Any
    temperature_kind: str | None = None


def _humanize_token(value: str) -> str:
    return value.replace("_", " ").replace(":", " ").strip().title()


def _humanize_hvac_mode(manager: ClimateManager) -> str:
    value = manager.runtime.desired_hvac_mode
    if value is not None:
        labels = {
            "heat": "Heat",
            "cool": "Cool",
            "off": "Off",
            "heat_cool": "Auto",
        }
        return labels.get(value, _humanize_token(value))

    profile_labels = {
        "manual_override": "User override",
        "override_lock": "Override lock",
        "paused": "Paused",
    }
    return profile_labels.get(manager.runtime.active_profile, "Unknown")


def _humanize_last_action(manager: ClimateManager) -> str | None:
    value = manager.last_action
    if value is None:
        return None
    if value == "clear_override":
        return "Cleared override"
    if value == "set_temporary_override":
        return "Started temporary override"
    if value == "pause":
        return "Paused smart control"
    if value == "resume":
        return "Resumed smart control"
    if value.startswith("set_hvac_mode:"):
        mode = value.split(":", 1)[1]
        return f"Set HVAC mode to {_humanize_token(mode)}"
    if value.startswith("set_temperature:"):
        return "Adjusted thermostat setpoint"
    return _humanize_token(value)


SENSORS: tuple[ClimateManagerSensorDescription, ...] = (
    ClimateManagerSensorDescription(
        key="active_profile",
        translation_key="active_profile",
        value_fn=lambda manager: manager.runtime.active_profile,
    ),
    ClimateManagerSensorDescription(
        key="desired_hvac_mode",
        translation_key="desired_hvac_mode",
        value_fn=_humanize_hvac_mode,
    ),
    ClimateManagerSensorDescription(
        key="current_set_temp",
        translation_key="current_set_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        temperature_kind="absolute",
        value_fn=lambda manager: manager.current_set_temperature,
    ),
    ClimateManagerSensorDescription(
        key="target_heat",
        translation_key="target_heat",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        temperature_kind="absolute",
        value_fn=lambda manager: manager.runtime.target_heat,
    ),
    ClimateManagerSensorDescription(
        key="target_cool",
        translation_key="target_cool",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        temperature_kind="absolute",
        value_fn=lambda manager: manager.runtime.target_cool,
    ),
    ClimateManagerSensorDescription(
        key="comfort_offset",
        translation_key="comfort_offset",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        temperature_kind="delta",
        value_fn=lambda manager: manager.runtime.comfort_offset,
    ),
    ClimateManagerSensorDescription(
        key="comfort_target",
        translation_key="comfort_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        temperature_kind="absolute",
        value_fn=lambda manager: manager.runtime.active_comfort_target
        if manager.runtime.active_comfort_target is not None
        else manager.config.comfort_target,
    ),
    ClimateManagerSensorDescription(
        key="transition_heat_target",
        translation_key="transition_heat_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        temperature_kind="absolute",
        value_fn=lambda manager: manager.runtime.transition_heat_target,
    ),
    ClimateManagerSensorDescription(
        key="transition_cool_target",
        translation_key="transition_cool_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        temperature_kind="absolute",
        value_fn=lambda manager: manager.runtime.transition_cool_target,
    ),
    ClimateManagerSensorDescription(
        key="outdoor_boost_state",
        translation_key="outdoor_boost_state",
        value_fn=lambda manager: manager.runtime.outdoor_boost_state,
    ),
    ClimateManagerSensorDescription(
        key="active_control_reason",
        translation_key="active_control_reason",
        value_fn=lambda manager: manager.runtime.active_control_reason,
    ),
    ClimateManagerSensorDescription(
        key="status",
        translation_key="status",
        value_fn=lambda manager: manager.runtime.status,
    ),
    ClimateManagerSensorDescription(
        key="override_until",
        translation_key="override_until",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda manager: manager.runtime.manual_override_until,
    ),
    ClimateManagerSensorDescription(
        key="windows_backoff_until",
        translation_key="windows_backoff_until",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda manager: manager.runtime.windows_backoff_until,
    ),
    ClimateManagerSensorDescription(
        key="windows_open_since",
        translation_key="windows_open_since",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda manager: manager.runtime.windows_open_since,
    ),
    ClimateManagerSensorDescription(
        key="windows_closed_since",
        translation_key="windows_closed_since",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda manager: manager.runtime.windows_closed_since,
    ),
    ClimateManagerSensorDescription(
        key="window_timer_expected_at",
        translation_key="window_timer_expected_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda manager: manager.window_timer_expected_at,
    ),
    ClimateManagerSensorDescription(
        key="windows_raw_state",
        translation_key="windows_raw_state",
        value_fn=lambda manager: manager.windows_raw_state,
    ),
    ClimateManagerSensorDescription(
        key="windows_protection_state",
        translation_key="windows_protection_state",
        value_fn=lambda manager: manager.windows_protection_state,
    ),
    ClimateManagerSensorDescription(
        key="window_timer_kind",
        translation_key="window_timer_kind",
        value_fn=lambda manager: manager.window_timer_kind,
    ),
    ClimateManagerSensorDescription(
        key="last_window_timer_reason",
        translation_key="last_window_timer_reason",
        value_fn=lambda manager: manager.last_window_timer_reason,
    ),
    ClimateManagerSensorDescription(
        key="windows_action",
        translation_key="windows_action",
        value_fn=lambda manager: manager.config.windows_action,
    ),
    ClimateManagerSensorDescription(
        key="window_safety_state",
        translation_key="window_safety_state",
        value_fn=lambda manager: manager.window_safety_state,
    ),
    ClimateManagerSensorDescription(
        key="window_safety_activation_reason",
        translation_key="window_safety_activation_reason",
        value_fn=lambda manager: manager.runtime.windows_safety_activation_reason,
    ),
    ClimateManagerSensorDescription(
        key="window_safety_activated_at",
        translation_key="window_safety_activated_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda manager: manager.runtime.windows_safety_activated_at,
    ),
    ClimateManagerSensorDescription(
        key="window_safety_cleared_at",
        translation_key="window_safety_cleared_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda manager: manager.runtime.windows_safety_cleared_at,
    ),
    ClimateManagerSensorDescription(
        key="window_safety_clear_reason",
        translation_key="window_safety_clear_reason",
        value_fn=lambda manager: manager.runtime.windows_safety_clear_reason,
    ),
    ClimateManagerSensorDescription(
        key="window_safety_deadline",
        translation_key="window_safety_deadline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda manager: manager.window_safety_deadline,
    ),
    ClimateManagerSensorDescription(
        key="window_safety_min_indoor_temperature",
        translation_key="window_safety_min_indoor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        temperature_kind="absolute",
        value_fn=lambda manager: manager.config.windows_safety_min_indoor_temperature,
    ),
    ClimateManagerSensorDescription(
        key="window_safety_max_indoor_temperature",
        translation_key="window_safety_max_indoor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        temperature_kind="absolute",
        value_fn=lambda manager: manager.config.windows_safety_max_indoor_temperature,
    ),
    ClimateManagerSensorDescription(
        key="window_safety_hysteresis",
        translation_key="window_safety_hysteresis",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        temperature_kind="delta",
        value_fn=lambda manager: manager.config.windows_safety_hysteresis,
    ),
    ClimateManagerSensorDescription(
        key="thermostat_current_temperature",
        translation_key="thermostat_current_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        temperature_kind="absolute",
        value_fn=lambda manager: manager._thermostat_snapshot().current_temperature,
    ),
    ClimateManagerSensorDescription(
        key="thermostat_reported_target",
        translation_key="thermostat_reported_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        temperature_kind="absolute",
        value_fn=lambda manager: manager._thermostat_snapshot().target_temp,
    ),
    ClimateManagerSensorDescription(
        key="thermostat_reported_target_low",
        translation_key="thermostat_reported_target_low",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        temperature_kind="absolute",
        value_fn=lambda manager: manager._thermostat_snapshot().target_temp_low,
    ),
    ClimateManagerSensorDescription(
        key="thermostat_reported_target_high",
        translation_key="thermostat_reported_target_high",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        temperature_kind="absolute",
        value_fn=lambda manager: manager._thermostat_snapshot().target_temp_high,
    ),
    ClimateManagerSensorDescription(
        key="thermostat_hvac_action",
        translation_key="thermostat_hvac_action",
        value_fn=lambda manager: manager.thermostat_hvac_action,
    ),
    ClimateManagerSensorDescription(
        key="last_commanded_target",
        translation_key="last_commanded_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        temperature_kind="absolute",
        value_fn=lambda manager: manager.runtime.last_commanded_temp,
    ),
    ClimateManagerSensorDescription(
        key="last_commanded_target_low",
        translation_key="last_commanded_target_low",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        temperature_kind="absolute",
        value_fn=lambda manager: manager.runtime.last_commanded_low,
    ),
    ClimateManagerSensorDescription(
        key="last_commanded_target_high",
        translation_key="last_commanded_target_high",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        temperature_kind="absolute",
        value_fn=lambda manager: manager.runtime.last_commanded_high,
    ),
    ClimateManagerSensorDescription(
        key="last_command_time",
        translation_key="last_command_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda manager: manager.runtime.last_command_time,
    ),
    ClimateManagerSensorDescription(
        key="pre_arrival_state",
        translation_key="pre_arrival_state",
        value_fn=lambda manager: manager.pre_arrival_raw_state,
    ),
    ClimateManagerSensorDescription(
        key="pre_arrival_blocked_reason",
        translation_key="pre_arrival_blocked_reason",
        value_fn=lambda manager: manager.pre_arrival_blocked_reason,
    ),
    ClimateManagerSensorDescription(
        key="last_reason",
        translation_key="last_reason",
        value_fn=lambda manager: manager.last_reason,
    ),
    ClimateManagerSensorDescription(
        key="last_action",
        translation_key="last_action",
        value_fn=_humanize_last_action,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    manager: ClimateManager = hass.data[DOMAIN][entry.entry_id][DATA_MANAGER]
    async_add_entities([ClimateManagerSensor(entry.entry_id, manager, description) for description in SENSORS])


class ClimateManagerSensor(ClimateManagerEntity, SensorEntity):
    """Climate Manager sensor."""

    def __init__(
        self,
        entry_id: str,
        manager: ClimateManager,
        description: ClimateManagerSensorDescription,
    ) -> None:
        super().__init__(entry_id, manager)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def native_unit_of_measurement(self):
        if self.entity_description.temperature_kind is not None:
            return self._manager.temperature_unit
        return self.entity_description.native_unit_of_measurement

    @property
    def native_value(self):
        value = self.entity_description.value_fn(self._manager)
        unit = self._manager.temperature_unit
        if self.entity_description.temperature_kind == "absolute":
            return round_temperature_for_unit(to_ha_temp(value, unit), unit)
        if self.entity_description.temperature_kind == "delta":
            return round_temperature_for_unit(to_ha_temp_delta(value, unit), unit)
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key == "desired_hvac_mode":
            return {
                "raw_value": self._manager.runtime.desired_hvac_mode,
                "active_profile": self._manager.runtime.active_profile,
            }
        if self.entity_description.key == "last_action":
            return {"raw_value": self._manager.last_action}
        return None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._manager.async_subscribe(self.async_write_ha_state))
