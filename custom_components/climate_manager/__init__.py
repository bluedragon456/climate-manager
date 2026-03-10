"""The Climate Manager integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    DATA_MANAGER,
    DOMAIN,
    PLATFORMS,
    SERVICE_CLEAR_OVERRIDE,
    SERVICE_PAUSE,
    SERVICE_RECALCULATE,
    SERVICE_RESUME,
    SERVICE_SET_TEMPORARY_OVERRIDE,
)
from .manager import ClimateManager
from .models import ManagerConfig
from .const import DEFAULT_OPTIONS

_LOGGER = logging.getLogger(__name__)

SERVICE_TEMPORARY_OVERRIDE_SCHEMA = vol.Schema(
    {
        vol.Required("entry_id"): cv.string,
        vol.Optional("duration_minutes", default=120): vol.Coerce(int),
        vol.Optional("target_temp"): vol.Coerce(float),
        vol.Optional("hvac_mode"): cv.string,
    }
)

ENTRY_ID_SCHEMA = vol.Schema({vol.Required("entry_id"): cv.string})


def _build_manager_config(entry: ConfigEntry) -> ManagerConfig:
    raw: dict[str, Any] = {**DEFAULT_OPTIONS, **entry.data, **entry.options}
    return ManagerConfig(
        thermostat_entity=raw["thermostat_entity"],
        outdoor_temp_entity=raw.get("outdoor_temp_entity"),
        sleep_schedule_entity=raw.get("sleep_schedule_entity"),
        away_entity=raw.get("away_entity"),
        guest_entity=raw.get("guest_entity"),
        override_entity=raw.get("override_entity"),
        windows_entity=raw.get("windows_entity"),
        season_entity=raw.get("season_entity"),
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
    )


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up services for Climate Manager."""
    hass.data.setdefault(DOMAIN, {})

    async def _get_manager(call: ServiceCall) -> ClimateManager | None:
        entry_id = call.data["entry_id"]
        manager = hass.data[DOMAIN].get(entry_id, {}).get(DATA_MANAGER)
        if manager is None:
            _LOGGER.warning("No climate manager found for entry_id=%s", entry_id)
        return manager

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
            await manager.async_set_temporary_override(
                duration_minutes=call.data["duration_minutes"],
                target_temp=call.data.get("target_temp"),
                hvac_mode=call.data.get("hvac_mode"),
            )

    hass.services.async_register(DOMAIN, SERVICE_RECALCULATE, handle_recalculate, schema=ENTRY_ID_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_OVERRIDE, handle_clear_override, schema=ENTRY_ID_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_PAUSE, handle_pause, schema=ENTRY_ID_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_RESUME, handle_resume, schema=ENTRY_ID_SCHEMA)
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TEMPORARY_OVERRIDE,
        handle_set_temporary_override,
        schema=SERVICE_TEMPORARY_OVERRIDE_SCHEMA,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Climate Manager from a config entry."""
    manager = ClimateManager(hass, entry.entry_id, _build_manager_config(entry))
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
