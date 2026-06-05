"""The Climate Manager integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_TEMPERATURE_UNIT_MODE,
    CONF_GUEST_COMFORT_TARGET,
    CONF_GUEST_COMFORT_TARGET_OVERRIDE,
    CONF_HOME_COMFORT_TARGET,
    CONF_HOME_COMFORT_TARGET_OVERRIDE,
    CONF_SLEEP_COMFORT_TARGET,
    CONF_SLEEP_COMFORT_TARGET_OVERRIDE,
    DATA_MANAGER,
    DEFAULT_EXISTING_TEMPERATURE_UNIT_MODE,
    DEFAULT_GUEST_COMFORT_TARGET,
    DEFAULT_HOME_COMFORT_TARGET,
    DEFAULT_OPTIONS,
    DEFAULT_SLEEP_COMFORT_TARGET,
    DEFAULT_TEMPERATURE_UNIT,
    DOMAIN,
    PLATFORMS,
    SERVICE_CLEAR_OVERRIDE,
    SERVICE_PAUSE,
    SERVICE_RECALCULATE,
    SERVICE_RESUME,
    SERVICE_SET_TEMPORARY_OVERRIDE,
    TEMPERATURE_OPTION_KEYS,
    TEMPERATURE_UNIT_MODES,
)
from .helpers import from_ha_temp, resolve_temperature_unit, round_to_half
from .manager import ClimateManager
from .models import ManagerConfig

CONFIG_SCHEMA = vol.Schema({}, extra=vol.ALLOW_EXTRA)

_LOGGER = logging.getLogger(__name__)

SERVICE_TEMPORARY_OVERRIDE_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): cv.string,
        vol.Optional("duration_minutes", default=120): vol.Coerce(int),
        vol.Optional("target_temp"): vol.Coerce(float),
        vol.Optional("hvac_mode"): cv.string,
    }
)

ENTRY_ID_SCHEMA = vol.Schema({vol.Optional("entry_id"): cv.string})


def _profile_comfort_override_enabled(
    stored: dict[str, Any],
    raw: dict[str, Any],
    value_key: str,
    override_key: str,
    default_value: float,
) -> bool:
    """Return whether a profile comfort target should override the global target."""
    if override_key in stored:
        return bool(raw.get(override_key))
    if value_key not in stored:
        return False
    try:
        return round_to_half(float(raw[value_key])) != default_value
    except (TypeError, ValueError):
        return False


def _build_manager_config(hass: HomeAssistant, entry: ConfigEntry) -> ManagerConfig:
    stored: dict[str, Any] = {**entry.data, **entry.options}
    raw: dict[str, Any] = {**DEFAULT_OPTIONS, **entry.data, **entry.options}
    unit_mode = str(raw.get(CONF_TEMPERATURE_UNIT_MODE, DEFAULT_EXISTING_TEMPERATURE_UNIT_MODE))
    if unit_mode not in TEMPERATURE_UNIT_MODES:
        unit_mode = DEFAULT_EXISTING_TEMPERATURE_UNIT_MODE
    unit = resolve_temperature_unit(hass, unit_mode)
    if unit_mode == DEFAULT_EXISTING_TEMPERATURE_UNIT_MODE or unit == DEFAULT_TEMPERATURE_UNIT:
        for key in TEMPERATURE_OPTION_KEYS:
            raw[key] = round_to_half(float(raw[key]))
    return ManagerConfig(
        thermostat_entity=raw["thermostat_entity"],
        outdoor_temp_entity=raw.get("outdoor_temp_entity"),
        sleep_schedule_entity=raw.get("sleep_schedule_entity"),
        away_entity=raw.get("away_entity"),
        guest_entity=raw.get("guest_entity"),
        override_entity=raw.get("override_entity"),
        windows_entity=raw.get("windows_entity"),
        season_entity=raw.get("season_entity"),
        temperature_unit_mode=unit_mode,
        smart_control_enabled=raw["smart_control_enabled"],
        hvac_preference=raw["hvac_preference"],
        heat_home=raw["heat_home"],
        heat_sleep=raw["heat_sleep"],
        heat_guest=raw["heat_guest"],
        heat_away=raw["heat_away"],
        cool_home=raw["cool_home"],
        cool_sleep=raw["cool_sleep"],
        cool_guest=raw["cool_guest"],
        cool_away=raw["cool_away"],
        curve_band_1_max=raw["curve_band_1_max"],
        curve_band_1_offset=raw["curve_band_1_offset"],
        curve_band_2_max=raw["curve_band_2_max"],
        curve_band_2_offset=raw["curve_band_2_offset"],
        curve_band_3_max=raw["curve_band_3_max"],
        curve_band_3_offset=raw["curve_band_3_offset"],
        curve_band_4_max=raw["curve_band_4_max"],
        curve_band_4_offset=raw["curve_band_4_offset"],
        curve_weight_home=raw["curve_weight_home"],
        curve_weight_sleep=raw["curve_weight_sleep"],
        curve_weight_guest=raw["curve_weight_guest"],
        curve_weight_away=raw["curve_weight_away"],
        cool_curve_band_1_min=raw["cool_curve_band_1_min"],
        cool_curve_band_1_offset=raw["cool_curve_band_1_offset"],
        cool_curve_band_2_min=raw["cool_curve_band_2_min"],
        cool_curve_band_2_offset=raw["cool_curve_band_2_offset"],
        cool_curve_band_3_min=raw["cool_curve_band_3_min"],
        cool_curve_band_3_offset=raw["cool_curve_band_3_offset"],
        cool_curve_band_4_min=raw["cool_curve_band_4_min"],
        cool_curve_band_4_offset=raw["cool_curve_band_4_offset"],
        cool_curve_weight_home=raw["cool_curve_weight_home"],
        cool_curve_weight_sleep=raw["cool_curve_weight_sleep"],
        cool_curve_weight_guest=raw["cool_curve_weight_guest"],
        cool_curve_weight_away=raw["cool_curve_weight_away"],
        comfort_target=raw["comfort_target"],
        home_comfort_target=raw["home_comfort_target"],
        sleep_comfort_target=raw["sleep_comfort_target"],
        guest_comfort_target=raw["guest_comfort_target"],
        home_comfort_target_override=_profile_comfort_override_enabled(
            stored,
            raw,
            CONF_HOME_COMFORT_TARGET,
            CONF_HOME_COMFORT_TARGET_OVERRIDE,
            DEFAULT_HOME_COMFORT_TARGET,
        ),
        sleep_comfort_target_override=_profile_comfort_override_enabled(
            stored,
            raw,
            CONF_SLEEP_COMFORT_TARGET,
            CONF_SLEEP_COMFORT_TARGET_OVERRIDE,
            DEFAULT_SLEEP_COMFORT_TARGET,
        ),
        guest_comfort_target_override=_profile_comfort_override_enabled(
            stored,
            raw,
            CONF_GUEST_COMFORT_TARGET,
            CONF_GUEST_COMFORT_TARGET_OVERRIDE,
            DEFAULT_GUEST_COMFORT_TARGET,
        ),
        transition_band=raw["transition_band"],
        minimum_auto_gap=raw["minimum_auto_gap"],
        outdoor_cool_override_temp=raw["outdoor_cool_override_temp"],
        outdoor_heat_override_temp=raw["outdoor_heat_override_temp"],
        outdoor_override_deadband=raw["outdoor_override_deadband"],
        manual_temp_behavior=raw["manual_temp_behavior"],
        manual_mode_behavior=raw["manual_mode_behavior"],
        override_duration_minutes=raw["override_duration_minutes"],
        manual_grace_seconds=raw["manual_grace_seconds"],
        windows_open_delay_minutes=raw["windows_open_delay_minutes"],
        windows_restore_delay_minutes=raw["windows_restore_delay_minutes"],
        windows_action=raw["windows_action"],
        min_heat_target=raw["min_heat_target"],
        max_heat_target=raw["max_heat_target"],
        min_cool_target=raw["min_cool_target"],
        max_cool_target=raw["max_cool_target"],
        temp_change_threshold=raw["temp_change_threshold"],
        cancel_override_on_away=raw["cancel_override_on_away"],
        cancel_override_on_windows=raw["cancel_override_on_windows"],
        cancel_override_on_sleep=raw["cancel_override_on_sleep"],
        debug_manual_detection=raw["debug_manual_detection"],
    )


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up Climate Manager services."""
    hass.data.setdefault(DOMAIN, {})

    async def _get_manager(call: ServiceCall) -> ClimateManager | None:
        entry_id = call.data.get("entry_id")

        if entry_id:
            manager = hass.data[DOMAIN].get(entry_id, {}).get(DATA_MANAGER)
            if manager is None:
                _LOGGER.warning("No climate manager found for entry_id=%s", entry_id)
            return manager

        managers = [
            entry_data.get(DATA_MANAGER)
            for entry_data in hass.data[DOMAIN].values()
            if isinstance(entry_data, dict) and DATA_MANAGER in entry_data
        ]

        if len(managers) == 1:
            return managers[0]

        if not managers:
            _LOGGER.warning("No climate manager instances are loaded")
        else:
            _LOGGER.warning("Multiple climate manager instances found; entry_id is required")

        return None

    async def handle_recalculate(call: ServiceCall) -> None:
        if manager := await _get_manager(call):
            await manager.async_recalculate("service")

    async def handle_clear_override(call: ServiceCall) -> None:
        if manager := await _get_manager(call):
            await manager.async_clear_override()

    async def handle_pause(call: ServiceCall) -> None:
        if manager := await _get_manager(call):
            await manager.async_pause()

    async def handle_resume(call: ServiceCall) -> None:
        if manager := await _get_manager(call):
            await manager.async_resume()

    async def handle_set_temporary_override(call: ServiceCall) -> None:
        if manager := await _get_manager(call):
            target_temp = from_ha_temp(call.data.get("target_temp"), manager.temperature_unit)
            await manager.async_set_temporary_override(
                duration_minutes=call.data["duration_minutes"],
                target_temp=target_temp,
                hvac_mode=call.data.get("hvac_mode"),
            )

    if not hass.services.has_service(DOMAIN, SERVICE_RECALCULATE):
        hass.services.async_register(DOMAIN, SERVICE_RECALCULATE, handle_recalculate, schema=ENTRY_ID_SCHEMA)
    if not hass.services.has_service(DOMAIN, SERVICE_CLEAR_OVERRIDE):
        hass.services.async_register(DOMAIN, SERVICE_CLEAR_OVERRIDE, handle_clear_override, schema=ENTRY_ID_SCHEMA)
    if not hass.services.has_service(DOMAIN, SERVICE_PAUSE):
        hass.services.async_register(DOMAIN, SERVICE_PAUSE, handle_pause, schema=ENTRY_ID_SCHEMA)
    if not hass.services.has_service(DOMAIN, SERVICE_RESUME):
        hass.services.async_register(DOMAIN, SERVICE_RESUME, handle_resume, schema=ENTRY_ID_SCHEMA)
    if not hass.services.has_service(DOMAIN, SERVICE_SET_TEMPORARY_OVERRIDE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_TEMPORARY_OVERRIDE,
            handle_set_temporary_override,
            schema=SERVICE_TEMPORARY_OVERRIDE_SCHEMA,
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Climate Manager from a config entry."""
    manager = ClimateManager(hass, entry.entry_id, _build_manager_config(hass, entry))
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {DATA_MANAGER: manager}
    await manager.async_initialize()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        manager: ClimateManager = hass.data[DOMAIN][entry.entry_id][DATA_MANAGER]
        await manager.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
