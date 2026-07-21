"""Diagnostics support for Climate Manager."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DATA_MANAGER, DOMAIN, PROFILE_PRE_ARRIVAL
from .manager import ClimateManager


def _serialize(value: Any) -> Any:
    """Convert diagnostic datetimes and nested values to JSON-friendly data."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return support diagnostics without location or tracker attributes."""
    manager: ClimateManager = hass.data[DOMAIN][entry.entry_id][DATA_MANAGER]
    thermostat = manager._thermostat_snapshot()
    command_age = None
    if manager.runtime.last_command_time is not None:
        from .helpers import now

        command_age = max(0.0, (now() - manager.runtime.last_command_time).total_seconds())
    safety_remaining = None
    safety_deadline = manager.window_safety_deadline
    if safety_deadline is not None:
        from .helpers import now

        safety_remaining = max(0.0, (safety_deadline - now()).total_seconds())
    safety_heat, safety_cool = manager.window_safety_envelope

    return _serialize(
        {
            "config": {**entry.data, **entry.options},
            "runtime": asdict(manager.runtime),
            "hvac": {
                "calculated_target_heat": manager.runtime.target_heat,
                "calculated_target_cool": manager.runtime.target_cool,
                "last_commanded_mode": manager.runtime.last_commanded_hvac_mode,
                "last_commanded_target": manager.runtime.last_commanded_temp,
                "last_commanded_target_low": manager.runtime.last_commanded_low,
                "last_commanded_target_high": manager.runtime.last_commanded_high,
                "thermostat_mode": thermostat.hvac_mode,
                "thermostat_reported_target": thermostat.target_temp,
                "thermostat_reported_target_low": thermostat.target_temp_low,
                "thermostat_reported_target_high": thermostat.target_temp_high,
                "thermostat_current_temperature": thermostat.current_temperature,
                "thermostat_hvac_action": manager.thermostat_hvac_action,
                "active_profile": manager.runtime.active_profile,
                "blocking_reason": manager.runtime.active_control_reason,
                "last_command_time": manager.runtime.last_command_time,
                "seconds_since_last_command": command_age,
                "above_cooling_target_while_idle": manager.above_cooling_target_while_idle,
            },
            "windows": {
                "configured_entity": manager.config.windows_entity,
                "raw_sensor_state": manager.windows_raw_state,
                "open_since": manager.runtime.windows_open_since,
                "closed_since": manager.runtime.windows_closed_since,
                "backoff_until": manager.runtime.windows_backoff_until,
                "backoff_active": manager.runtime.windows_backoff_active,
                "protection_state": manager.windows_protection_state,
                "activation_timer_scheduled": manager.window_timer_kind == "open_delay",
                "restore_timer_scheduled": manager.window_timer_kind == "restore_delay",
                "expected_callback_at": manager.window_timer_expected_at,
                "action": manager.config.windows_action,
                "last_timer_callback_reason": manager.last_window_timer_reason,
                "safety": {
                    "enabled": manager.config.windows_safety_override_enabled,
                    "configuration_valid": manager.window_safety_configuration_valid,
                    "state": manager.window_safety_state,
                    "active": manager.runtime.windows_safety_override_active,
                    "activation_reason": manager.runtime.windows_safety_activation_reason,
                    "activated_at": manager.runtime.windows_safety_activated_at,
                    "cleared_at": manager.runtime.windows_safety_cleared_at,
                    "clear_reason": manager.runtime.windows_safety_clear_reason,
                    "deadline": safety_deadline,
                    "seconds_until_deadline": safety_remaining,
                    "maximum_backoff_minutes": manager.config.windows_safety_maximum_backoff_minutes,
                    "minimum_indoor_temperature": manager.config.windows_safety_min_indoor_temperature,
                    "maximum_indoor_temperature": manager.config.windows_safety_max_indoor_temperature,
                    "hysteresis": manager.config.windows_safety_hysteresis,
                    "protective_heat_target": safety_heat,
                    "protective_cool_target": safety_cool,
                    "current_indoor_temperature": thermostat.current_temperature,
                    "selected_hvac_mode": manager.runtime.desired_hvac_mode,
                    "blocked_reason": manager.window_safety_blocked_reason,
                    "thermostat_supported_hvac_modes": (
                        None
                        if manager.thermostat_supported_hvac_modes is None
                        else sorted(manager.thermostat_supported_hvac_modes)
                    ),
                    "thermostat_capability_issue": manager.window_safety_capability_issue,
                    "underlying_occupancy_profile": manager.underlying_occupancy_profile,
                    "manual_override_suspended": (
                        manager.runtime.windows_safety_override_active
                        and manager.runtime.manual_override_active
                    ),
                },
            },
            "pre_arrival": {
                "configured_entity": manager.config.pre_arrival_entity,
                "raw_entity_state": manager.pre_arrival_raw_state,
                "active": manager.runtime.active_profile == PROFILE_PRE_ARRIVAL,
                "blocked_reason": manager.pre_arrival_blocked_reason,
                "selected_hvac_mode": manager.runtime.desired_hvac_mode,
                "target_heat": manager.runtime.target_heat,
                "target_cool": manager.runtime.target_cool,
                "active_comfort_target": manager.runtime.active_comfort_target,
            },
        }
    )
