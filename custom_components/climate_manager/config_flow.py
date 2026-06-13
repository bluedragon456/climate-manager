"""Config flow for Climate Manager."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import *  # noqa: F403,F401
from .helpers import (
    from_ha_temp,
    from_ha_temp_delta,
    resolve_temperature_unit,
    round_temperature_for_unit,
    round_to_half,
    to_ha_temp,
    to_ha_temp_delta,
)

HVAC_PREFERENCE_OPTIONS = [HVAC_PREF_AUTO, HVAC_PREF_HEAT, HVAC_PREF_COOL, HVAC_PREF_OFF]
MANUAL_BEHAVIOR_OPTIONS = [
    MANUAL_BEHAVIOR_IGNORE,
    MANUAL_BEHAVIOR_TEMPORARY,
    MANUAL_BEHAVIOR_HOLD,
]
WINDOWS_ACTION_OPTIONS = [
    WINDOWS_ACTION_OFF,
    WINDOWS_ACTION_HEAT_SETBACK,
    WINDOWS_ACTION_COOL_SETBACK,
]

OPTIONS_MENU = [
    "entities",
    "simple_comfort",
    "transition_boost",
    "safety_limits",
    "manual_windows",
    "comfort_curve",
    "legacy",
    "diagnostics",
    "temperature_units",
]

ENTITY_CONFIG_KEYS = (
    CONF_THERMOSTAT_ENTITY,
    CONF_OUTDOOR_TEMP_ENTITY,
    CONF_SLEEP_SCHEDULE_ENTITY,
    CONF_AWAY_ENTITY,
    CONF_GUEST_ENTITY,
    CONF_OVERRIDE_ENTITY,
    CONF_WINDOWS_ENTITY,
    CONF_SEASON_ENTITY,
)
EDITABLE_ENTITY_CONFIG_KEYS = tuple(
    key for key in ENTITY_CONFIG_KEYS
    if key != CONF_THERMOSTAT_ENTITY
)
REQUIRED_ENTITY_CONFIG_KEYS = (
    CONF_THERMOSTAT_ENTITY,
    CONF_OUTDOOR_TEMP_ENTITY,
)

SIMPLE_COMFORT_KEYS = (
    CONF_SMART_CONTROL_ENABLED,
    CONF_HVAC_PREFERENCE,
    CONF_COMFORT_TARGET,
    CONF_HOME_COMFORT_TARGET_OVERRIDE,
    CONF_HOME_COMFORT_TARGET,
    CONF_SLEEP_COMFORT_TARGET_OVERRIDE,
    CONF_SLEEP_COMFORT_TARGET,
    CONF_GUEST_COMFORT_TARGET_OVERRIDE,
    CONF_GUEST_COMFORT_TARGET,
)
TRANSITION_BOOST_KEYS = (
    CONF_TRANSITION_BAND,
    CONF_MINIMUM_AUTO_GAP,
    CONF_OUTDOOR_COOL_OVERRIDE_TEMP,
    CONF_OUTDOOR_HEAT_OVERRIDE_TEMP,
    CONF_OUTDOOR_OVERRIDE_DEADBAND,
)
SAFETY_LIMIT_KEYS = (
    CONF_HEAT_AWAY,
    CONF_COOL_AWAY,
    CONF_MIN_HEAT_TARGET,
    CONF_MAX_HEAT_TARGET,
    CONF_MIN_COOL_TARGET,
    CONF_MAX_COOL_TARGET,
)
MANUAL_WINDOWS_KEYS = (
    CONF_MANUAL_TEMP_BEHAVIOR,
    CONF_MANUAL_MODE_BEHAVIOR,
    CONF_OVERRIDE_DURATION_MINUTES,
    CONF_MANUAL_GRACE_SECONDS,
    CONF_CANCEL_OVERRIDE_ON_AWAY,
    CONF_CANCEL_OVERRIDE_ON_WINDOWS,
    CONF_CANCEL_OVERRIDE_ON_SLEEP,
    CONF_WINDOWS_ACTION,
    CONF_WINDOWS_OPEN_DELAY_MINUTES,
    CONF_WINDOWS_RESTORE_DELAY_MINUTES,
)
COMFORT_CURVE_KEYS = (
    CONF_CURVE_WEIGHT_HOME,
    CONF_CURVE_WEIGHT_SLEEP,
    CONF_CURVE_WEIGHT_GUEST,
    CONF_COOL_CURVE_WEIGHT_HOME,
    CONF_COOL_CURVE_WEIGHT_SLEEP,
    CONF_COOL_CURVE_WEIGHT_GUEST,
)
LEGACY_KEYS = (
    CONF_HEAT_HOME,
    CONF_HEAT_SLEEP,
    CONF_HEAT_GUEST,
    CONF_COOL_HOME,
    CONF_COOL_SLEEP,
    CONF_COOL_GUEST,
    CONF_CURVE_BAND_1_MAX,
    CONF_CURVE_BAND_1_OFFSET,
    CONF_CURVE_BAND_2_MAX,
    CONF_CURVE_BAND_2_OFFSET,
    CONF_CURVE_BAND_3_MAX,
    CONF_CURVE_BAND_3_OFFSET,
    CONF_CURVE_BAND_4_MAX,
    CONF_CURVE_BAND_4_OFFSET,
    CONF_CURVE_WEIGHT_AWAY,
    CONF_COOL_CURVE_BAND_1_MIN,
    CONF_COOL_CURVE_BAND_1_OFFSET,
    CONF_COOL_CURVE_BAND_2_MIN,
    CONF_COOL_CURVE_BAND_2_OFFSET,
    CONF_COOL_CURVE_BAND_3_MIN,
    CONF_COOL_CURVE_BAND_3_OFFSET,
    CONF_COOL_CURVE_BAND_4_MIN,
    CONF_COOL_CURVE_BAND_4_OFFSET,
    CONF_COOL_CURVE_WEIGHT_AWAY,
)
DIAGNOSTIC_KEYS = (
    CONF_TEMP_CHANGE_THRESHOLD,
    CONF_DEBUG_MANUAL_DETECTION,
)

ABSOLUTE_TEMP_LIMITS = {
    CONF_HEAT_HOME: (30, 100),
    CONF_HEAT_SLEEP: (30, 100),
    CONF_HEAT_GUEST: (30, 100),
    CONF_HEAT_AWAY: (30, 100),
    CONF_COOL_HOME: (30, 100),
    CONF_COOL_SLEEP: (30, 100),
    CONF_COOL_GUEST: (30, 100),
    CONF_COOL_AWAY: (30, 100),
    CONF_CURVE_BAND_1_MAX: (-50, 150),
    CONF_CURVE_BAND_2_MAX: (-50, 150),
    CONF_CURVE_BAND_3_MAX: (-50, 150),
    CONF_CURVE_BAND_4_MAX: (-50, 150),
    CONF_COOL_CURVE_BAND_1_MIN: (-50, 150),
    CONF_COOL_CURVE_BAND_2_MIN: (-50, 150),
    CONF_COOL_CURVE_BAND_3_MIN: (-50, 150),
    CONF_COOL_CURVE_BAND_4_MIN: (-50, 150),
    CONF_COMFORT_TARGET: (30, 100),
    CONF_HOME_COMFORT_TARGET: (30, 100),
    CONF_SLEEP_COMFORT_TARGET: (30, 100),
    CONF_GUEST_COMFORT_TARGET: (30, 100),
    CONF_OUTDOOR_COOL_OVERRIDE_TEMP: (-50, 150),
    CONF_OUTDOOR_HEAT_OVERRIDE_TEMP: (-50, 150),
    CONF_MIN_HEAT_TARGET: (30, 100),
    CONF_MAX_HEAT_TARGET: (30, 100),
    CONF_MIN_COOL_TARGET: (30, 100),
    CONF_MAX_COOL_TARGET: (30, 100),
}
DELTA_TEMP_LIMITS = {
    CONF_CURVE_BAND_1_OFFSET: (-20, 20),
    CONF_CURVE_BAND_2_OFFSET: (-20, 20),
    CONF_CURVE_BAND_3_OFFSET: (-20, 20),
    CONF_CURVE_BAND_4_OFFSET: (-20, 20),
    CONF_COOL_CURVE_BAND_1_OFFSET: (-20, 20),
    CONF_COOL_CURVE_BAND_2_OFFSET: (-20, 20),
    CONF_COOL_CURVE_BAND_3_OFFSET: (-20, 20),
    CONF_COOL_CURVE_BAND_4_OFFSET: (-20, 20),
    CONF_TRANSITION_BAND: (0, 20),
    CONF_MINIMUM_AUTO_GAP: (0, 20),
    CONF_OUTDOOR_OVERRIDE_DEADBAND: (0, 20),
    CONF_TEMP_CHANGE_THRESHOLD: (0, 10),
}


def _normalize_options(
    defaults: dict[str, Any] | None = None,
    *,
    round_temperatures: bool = True,
) -> dict[str, Any]:
    source = defaults or {}
    data = dict(DEFAULT_OPTIONS)
    if defaults:
        data.update(defaults)

    normalized = {
        CONF_SMART_CONTROL_ENABLED: bool(data.get(CONF_SMART_CONTROL_ENABLED, DEFAULT_SMART_CONTROL_ENABLED)),
        CONF_HVAC_PREFERENCE: str(data.get(CONF_HVAC_PREFERENCE, DEFAULT_HVAC_PREFERENCE)),
        CONF_HEAT_HOME: float(data.get(CONF_HEAT_HOME, DEFAULT_HEAT_HOME)),
        CONF_HEAT_SLEEP: float(data.get(CONF_HEAT_SLEEP, DEFAULT_HEAT_SLEEP)),
        CONF_HEAT_GUEST: float(data.get(CONF_HEAT_GUEST, DEFAULT_HEAT_GUEST)),
        CONF_HEAT_AWAY: float(data.get(CONF_HEAT_AWAY, DEFAULT_HEAT_AWAY)),
        CONF_COOL_HOME: float(data.get(CONF_COOL_HOME, DEFAULT_COOL_HOME)),
        CONF_COOL_SLEEP: float(data.get(CONF_COOL_SLEEP, DEFAULT_COOL_SLEEP)),
        CONF_COOL_GUEST: float(data.get(CONF_COOL_GUEST, DEFAULT_COOL_GUEST)),
        CONF_COOL_AWAY: float(data.get(CONF_COOL_AWAY, DEFAULT_COOL_AWAY)),
        CONF_CURVE_BAND_1_MAX: float(data.get(CONF_CURVE_BAND_1_MAX, DEFAULT_CURVE_BAND_1_MAX)),
        CONF_CURVE_BAND_1_OFFSET: float(data.get(CONF_CURVE_BAND_1_OFFSET, DEFAULT_CURVE_BAND_1_OFFSET)),
        CONF_CURVE_BAND_2_MAX: float(data.get(CONF_CURVE_BAND_2_MAX, DEFAULT_CURVE_BAND_2_MAX)),
        CONF_CURVE_BAND_2_OFFSET: float(data.get(CONF_CURVE_BAND_2_OFFSET, DEFAULT_CURVE_BAND_2_OFFSET)),
        CONF_CURVE_BAND_3_MAX: float(data.get(CONF_CURVE_BAND_3_MAX, DEFAULT_CURVE_BAND_3_MAX)),
        CONF_CURVE_BAND_3_OFFSET: float(data.get(CONF_CURVE_BAND_3_OFFSET, DEFAULT_CURVE_BAND_3_OFFSET)),
        CONF_CURVE_BAND_4_MAX: float(data.get(CONF_CURVE_BAND_4_MAX, DEFAULT_CURVE_BAND_4_MAX)),
        CONF_CURVE_BAND_4_OFFSET: float(data.get(CONF_CURVE_BAND_4_OFFSET, DEFAULT_CURVE_BAND_4_OFFSET)),
        CONF_CURVE_WEIGHT_HOME: float(data.get(CONF_CURVE_WEIGHT_HOME, DEFAULT_CURVE_WEIGHT_HOME)),
        CONF_CURVE_WEIGHT_SLEEP: float(data.get(CONF_CURVE_WEIGHT_SLEEP, DEFAULT_CURVE_WEIGHT_SLEEP)),
        CONF_CURVE_WEIGHT_GUEST: float(data.get(CONF_CURVE_WEIGHT_GUEST, DEFAULT_CURVE_WEIGHT_GUEST)),
        CONF_CURVE_WEIGHT_AWAY: float(data.get(CONF_CURVE_WEIGHT_AWAY, DEFAULT_CURVE_WEIGHT_AWAY)),
        CONF_COOL_CURVE_BAND_1_MIN: float(data.get(CONF_COOL_CURVE_BAND_1_MIN, DEFAULT_COOL_CURVE_BAND_1_MIN)),
        CONF_COOL_CURVE_BAND_1_OFFSET: float(data.get(CONF_COOL_CURVE_BAND_1_OFFSET, DEFAULT_COOL_CURVE_BAND_1_OFFSET)),
        CONF_COOL_CURVE_BAND_2_MIN: float(data.get(CONF_COOL_CURVE_BAND_2_MIN, DEFAULT_COOL_CURVE_BAND_2_MIN)),
        CONF_COOL_CURVE_BAND_2_OFFSET: float(data.get(CONF_COOL_CURVE_BAND_2_OFFSET, DEFAULT_COOL_CURVE_BAND_2_OFFSET)),
        CONF_COOL_CURVE_BAND_3_MIN: float(data.get(CONF_COOL_CURVE_BAND_3_MIN, DEFAULT_COOL_CURVE_BAND_3_MIN)),
        CONF_COOL_CURVE_BAND_3_OFFSET: float(data.get(CONF_COOL_CURVE_BAND_3_OFFSET, DEFAULT_COOL_CURVE_BAND_3_OFFSET)),
        CONF_COOL_CURVE_BAND_4_MIN: float(data.get(CONF_COOL_CURVE_BAND_4_MIN, DEFAULT_COOL_CURVE_BAND_4_MIN)),
        CONF_COOL_CURVE_BAND_4_OFFSET: float(data.get(CONF_COOL_CURVE_BAND_4_OFFSET, DEFAULT_COOL_CURVE_BAND_4_OFFSET)),
        CONF_COOL_CURVE_WEIGHT_HOME: float(data.get(CONF_COOL_CURVE_WEIGHT_HOME, DEFAULT_COOL_CURVE_WEIGHT_HOME)),
        CONF_COOL_CURVE_WEIGHT_SLEEP: float(data.get(CONF_COOL_CURVE_WEIGHT_SLEEP, DEFAULT_COOL_CURVE_WEIGHT_SLEEP)),
        CONF_COOL_CURVE_WEIGHT_GUEST: float(data.get(CONF_COOL_CURVE_WEIGHT_GUEST, DEFAULT_COOL_CURVE_WEIGHT_GUEST)),
        CONF_COOL_CURVE_WEIGHT_AWAY: float(data.get(CONF_COOL_CURVE_WEIGHT_AWAY, DEFAULT_COOL_CURVE_WEIGHT_AWAY)),
        CONF_COMFORT_TARGET: float(data.get(CONF_COMFORT_TARGET, DEFAULT_COMFORT_TARGET)),
        CONF_HOME_COMFORT_TARGET: float(data.get(CONF_HOME_COMFORT_TARGET, DEFAULT_HOME_COMFORT_TARGET)),
        CONF_SLEEP_COMFORT_TARGET: float(data.get(CONF_SLEEP_COMFORT_TARGET, DEFAULT_SLEEP_COMFORT_TARGET)),
        CONF_GUEST_COMFORT_TARGET: float(data.get(CONF_GUEST_COMFORT_TARGET, DEFAULT_GUEST_COMFORT_TARGET)),
        CONF_HOME_COMFORT_TARGET_OVERRIDE: _profile_comfort_override_enabled(
            source,
            data,
            CONF_HOME_COMFORT_TARGET,
            CONF_HOME_COMFORT_TARGET_OVERRIDE,
            DEFAULT_HOME_COMFORT_TARGET,
        ),
        CONF_SLEEP_COMFORT_TARGET_OVERRIDE: _profile_comfort_override_enabled(
            source,
            data,
            CONF_SLEEP_COMFORT_TARGET,
            CONF_SLEEP_COMFORT_TARGET_OVERRIDE,
            DEFAULT_SLEEP_COMFORT_TARGET,
        ),
        CONF_GUEST_COMFORT_TARGET_OVERRIDE: _profile_comfort_override_enabled(
            source,
            data,
            CONF_GUEST_COMFORT_TARGET,
            CONF_GUEST_COMFORT_TARGET_OVERRIDE,
            DEFAULT_GUEST_COMFORT_TARGET,
        ),
        CONF_TRANSITION_BAND: float(data.get(CONF_TRANSITION_BAND, DEFAULT_TRANSITION_BAND)),
        CONF_MINIMUM_AUTO_GAP: float(data.get(CONF_MINIMUM_AUTO_GAP, DEFAULT_MINIMUM_AUTO_GAP)),
        CONF_OUTDOOR_COOL_OVERRIDE_TEMP: float(
            data.get(CONF_OUTDOOR_COOL_OVERRIDE_TEMP, DEFAULT_OUTDOOR_COOL_OVERRIDE_TEMP)
        ),
        CONF_OUTDOOR_HEAT_OVERRIDE_TEMP: float(
            data.get(CONF_OUTDOOR_HEAT_OVERRIDE_TEMP, DEFAULT_OUTDOOR_HEAT_OVERRIDE_TEMP)
        ),
        CONF_OUTDOOR_OVERRIDE_DEADBAND: float(
            data.get(CONF_OUTDOOR_OVERRIDE_DEADBAND, DEFAULT_OUTDOOR_OVERRIDE_DEADBAND)
        ),
        CONF_MANUAL_TEMP_BEHAVIOR: str(data.get(CONF_MANUAL_TEMP_BEHAVIOR, MANUAL_BEHAVIOR_TEMPORARY)),
        CONF_MANUAL_MODE_BEHAVIOR: str(data.get(CONF_MANUAL_MODE_BEHAVIOR, MANUAL_BEHAVIOR_TEMPORARY)),
        CONF_OVERRIDE_DURATION_MINUTES: int(data.get(CONF_OVERRIDE_DURATION_MINUTES, DEFAULT_OVERRIDE_DURATION_MINUTES)),
        CONF_MANUAL_GRACE_SECONDS: int(data.get(CONF_MANUAL_GRACE_SECONDS, DEFAULT_MANUAL_GRACE_SECONDS)),
        CONF_WINDOWS_OPEN_DELAY_MINUTES: int(data.get(CONF_WINDOWS_OPEN_DELAY_MINUTES, DEFAULT_WINDOWS_OPEN_DELAY_MINUTES)),
        CONF_WINDOWS_RESTORE_DELAY_MINUTES: int(data.get(CONF_WINDOWS_RESTORE_DELAY_MINUTES, DEFAULT_WINDOWS_RESTORE_DELAY_MINUTES)),
        CONF_WINDOWS_ACTION: str(data.get(CONF_WINDOWS_ACTION, DEFAULT_WINDOWS_ACTION)),
        CONF_MIN_HEAT_TARGET: float(data.get(CONF_MIN_HEAT_TARGET, DEFAULT_MIN_HEAT_TARGET)),
        CONF_MAX_HEAT_TARGET: float(data.get(CONF_MAX_HEAT_TARGET, DEFAULT_MAX_HEAT_TARGET)),
        CONF_MIN_COOL_TARGET: float(data.get(CONF_MIN_COOL_TARGET, DEFAULT_MIN_COOL_TARGET)),
        CONF_MAX_COOL_TARGET: float(data.get(CONF_MAX_COOL_TARGET, DEFAULT_MAX_COOL_TARGET)),
        CONF_TEMP_CHANGE_THRESHOLD: float(data.get(CONF_TEMP_CHANGE_THRESHOLD, DEFAULT_TEMP_CHANGE_THRESHOLD)),
        CONF_CANCEL_OVERRIDE_ON_AWAY: bool(data.get(CONF_CANCEL_OVERRIDE_ON_AWAY, DEFAULT_CANCEL_OVERRIDE_ON_AWAY)),
        CONF_CANCEL_OVERRIDE_ON_WINDOWS: bool(data.get(CONF_CANCEL_OVERRIDE_ON_WINDOWS, DEFAULT_CANCEL_OVERRIDE_ON_WINDOWS)),
        CONF_CANCEL_OVERRIDE_ON_SLEEP: bool(data.get(CONF_CANCEL_OVERRIDE_ON_SLEEP, DEFAULT_CANCEL_OVERRIDE_ON_SLEEP)),
        CONF_DEBUG_MANUAL_DETECTION: bool(data.get(CONF_DEBUG_MANUAL_DETECTION, DEFAULT_DEBUG_MANUAL_DETECTION)),
    }
    if round_temperatures:
        for key in TEMPERATURE_OPTION_KEYS:
            normalized[key] = round_to_half(float(normalized[key]))
    return normalized


def _profile_comfort_override_enabled(
    source: dict[str, Any],
    data: dict[str, Any],
    value_key: str,
    override_key: str,
    default_value: float,
) -> bool:
    if override_key in source:
        return bool(data.get(override_key))
    if value_key not in source:
        return False
    try:
        return round_to_half(float(data[value_key])) != default_value
    except (TypeError, ValueError):
        return False


def _temperature_unit_mode(data: dict[str, Any]) -> str:
    mode = str(data.get(CONF_TEMPERATURE_UNIT_MODE, DEFAULT_EXISTING_TEMPERATURE_UNIT_MODE))
    if mode in TEMPERATURE_UNIT_MODES:
        return mode
    return DEFAULT_EXISTING_TEMPERATURE_UNIT_MODE


def _storage_should_round(unit: str) -> bool:
    return unit == DEFAULT_TEMPERATURE_UNIT


def _float_box(*, min_value: float, max_value: float, step: float = 0.5):
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=min_value,
            max=max_value,
            step=step,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _int_box(*, min_value: int, max_value: int):
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=min_value,
            max=max_value,
            step=1,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _select_box(options: list[str], translation_key: str):
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            mode=selector.SelectSelectorMode.DROPDOWN,
            translation_key=translation_key,
        )
    )


def _display_number(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 1)


def _options_to_display(options: dict[str, Any], unit: str) -> dict[str, Any]:
    display = dict(options)
    for key in ABSOLUTE_TEMPERATURE_OPTION_KEYS:
        display[key] = _display_number(round_temperature_for_unit(to_ha_temp(options[key], unit), unit))
    for key in DELTA_TEMPERATURE_OPTION_KEYS:
        display[key] = _display_number(round_temperature_for_unit(to_ha_temp_delta(options[key], unit), unit))
    return display


def _options_to_storage(user_input: dict[str, Any], unit: str) -> dict[str, Any]:
    converted = dict(user_input)
    for key in ABSOLUTE_TEMPERATURE_OPTION_KEYS:
        if key in converted:
            converted[key] = from_ha_temp(float(converted[key]), unit)
    for key in DELTA_TEMPERATURE_OPTION_KEYS:
        if key in converted:
            converted[key] = from_ha_temp_delta(float(converted[key]), unit)
    return converted


def _absolute_box(key: str, unit: str):
    min_f, max_f = ABSOLUTE_TEMP_LIMITS[key]
    min_value = _display_number(to_ha_temp(min_f, unit))
    max_value = _display_number(to_ha_temp(max_f, unit))
    return _float_box(min_value=min_value, max_value=max_value)


def _delta_box(key: str, unit: str):
    min_f, max_f = DELTA_TEMP_LIMITS[key]
    min_value = _display_number(to_ha_temp_delta(min_f, unit))
    max_value = _display_number(to_ha_temp_delta(max_f, unit))
    return _float_box(min_value=min_value, max_value=max_value)


def _field_selector(key: str, unit: str):
    if key == CONF_SMART_CONTROL_ENABLED:
        return selector.BooleanSelector()
    if key == CONF_HVAC_PREFERENCE:
        return _select_box(HVAC_PREFERENCE_OPTIONS, "hvac_preference")
    if key in {CONF_MANUAL_TEMP_BEHAVIOR, CONF_MANUAL_MODE_BEHAVIOR}:
        return _select_box(MANUAL_BEHAVIOR_OPTIONS, "manual_behavior")
    if key == CONF_WINDOWS_ACTION:
        return _select_box(WINDOWS_ACTION_OPTIONS, "windows_action")
    if key in {
        CONF_CANCEL_OVERRIDE_ON_AWAY,
        CONF_CANCEL_OVERRIDE_ON_WINDOWS,
        CONF_CANCEL_OVERRIDE_ON_SLEEP,
        CONF_DEBUG_MANUAL_DETECTION,
        CONF_HOME_COMFORT_TARGET_OVERRIDE,
        CONF_SLEEP_COMFORT_TARGET_OVERRIDE,
        CONF_GUEST_COMFORT_TARGET_OVERRIDE,
    }:
        return selector.BooleanSelector()
    if key in {
        CONF_OVERRIDE_DURATION_MINUTES,
        CONF_WINDOWS_OPEN_DELAY_MINUTES,
        CONF_WINDOWS_RESTORE_DELAY_MINUTES,
    }:
        return _int_box(min_value=1 if key == CONF_OVERRIDE_DURATION_MINUTES else 0, max_value=1440)
    if key == CONF_MANUAL_GRACE_SECONDS:
        return _int_box(min_value=0, max_value=600)
    if key in ABSOLUTE_TEMPERATURE_OPTION_KEYS:
        return _absolute_box(key, unit)
    if key in DELTA_TEMPERATURE_OPTION_KEYS:
        return _delta_box(key, unit)
    return _float_box(min_value=0, max_value=5, step=0.1)


def _build_options_schema(defaults: dict[str, Any], keys: Iterable[str], unit: str) -> vol.Schema:
    display_defaults = _options_to_display(defaults, unit)
    return vol.Schema(
        {
            vol.Required(key, default=display_defaults[key]): _field_selector(key, unit)
            for key in keys
        }
    )


def _entity_selector(key: str):
    domains: dict[str, str | list[str]] = {
        CONF_THERMOSTAT_ENTITY: "climate",
        CONF_OUTDOOR_TEMP_ENTITY: "sensor",
        CONF_SLEEP_SCHEDULE_ENTITY: "schedule",
        CONF_AWAY_ENTITY: "input_boolean",
        CONF_GUEST_ENTITY: "input_boolean",
        CONF_OVERRIDE_ENTITY: "input_boolean",
        CONF_WINDOWS_ENTITY: "binary_sensor",
        CONF_SEASON_ENTITY: ["input_text", "sensor", "select"],
    }
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=domains[key]))


def _build_entity_fields(
    defaults: dict[str, Any] | None = None,
    keys: Iterable[str] = ENTITY_CONFIG_KEYS,
) -> dict[Any, Any]:
    fields: dict[Any, Any] = {}
    for key in keys:
        current = defaults.get(key) if defaults else None
        if key in REQUIRED_ENTITY_CONFIG_KEYS:
            marker = vol.Required(key, default=current) if current else vol.Required(key)
        else:
            marker = vol.Optional(key, default=current) if current else vol.Optional(key)
        fields[marker] = _entity_selector(key)
    return fields


class ClimateManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Climate Manager."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Return options flow."""
        return ClimateManagerOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        if user_input is not None:
            # The thermostat is the stable config-entry identity and is not editable later.
            await self.async_set_unique_id(user_input[CONF_THERMOSTAT_ENTITY])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Climate Manager", data=user_input)

        fields = _build_entity_fields()
        fields.update(
            {
                vol.Required(
                    CONF_TEMPERATURE_UNIT_MODE,
                    default=DEFAULT_NEW_TEMPERATURE_UNIT_MODE,
                ): _select_box(TEMPERATURE_UNIT_MODES, "temperature_unit_mode"),
            }
        )
        schema = vol.Schema(fields)
        return self.async_show_form(step_id="user", data_schema=schema)


class ClimateManagerOptionsFlow(config_entries.OptionsFlow):
    """Handle Climate Manager options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    def _raw_options(self) -> dict[str, Any]:
        raw = {**self._config_entry.data, **self._config_entry.options}
        raw[CONF_THERMOSTAT_ENTITY] = self._config_entry.data[CONF_THERMOSTAT_ENTITY]
        return raw

    def _unit_mode(self) -> str:
        return _temperature_unit_mode(self._raw_options())

    def _unit(self) -> str:
        return resolve_temperature_unit(self.hass, self._unit_mode())

    def _defaults(self, unit: str) -> dict[str, Any]:
        return _normalize_options(
            self._raw_options(),
            round_temperatures=_storage_should_round(unit),
        )

    def _save(self, updates: dict[str, Any], unit: str):
        converted = _options_to_storage(updates, unit)
        raw = {**self._raw_options(), **converted}
        return self.async_create_entry(title="", data=self._normalized_settings_options(raw, unit))

    def _normalized_settings_options(self, raw: dict[str, Any], unit: str) -> dict[str, Any]:
        """Normalize settings while preserving entity overrides stored in options."""
        normalized = _normalize_options(raw, round_temperatures=_storage_should_round(unit))
        normalized[CONF_TEMPERATURE_UNIT_MODE] = _temperature_unit_mode(raw)
        for key in EDITABLE_ENTITY_CONFIG_KEYS:
            if key in self._config_entry.options:
                normalized[key] = self._config_entry.options[key]
        return normalized

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Show options menu."""
        return self.async_show_menu(step_id="init", menu_options=OPTIONS_MENU)

    async def async_step_entities(self, user_input: dict[str, Any] | None = None):
        """Manage configurable supporting entities."""
        if user_input is not None:
            entity_updates = {
                key: user_input.get(key)
                for key in EDITABLE_ENTITY_CONFIG_KEYS
            }
            preserved_options = {
                key: value
                for key, value in self._config_entry.options.items()
                if key != CONF_THERMOSTAT_ENTITY
            }
            return self.async_create_entry(
                title="",
                data={**preserved_options, **entity_updates},
            )

        schema = vol.Schema(
            _build_entity_fields(
                self._raw_options(),
                EDITABLE_ENTITY_CONFIG_KEYS,
            )
        )
        return self.async_show_form(step_id="entities", data_schema=schema)

    async def _async_step_options(
        self,
        step_id: str,
        keys: Iterable[str],
        user_input: dict[str, Any] | None,
    ):
        unit = self._unit()
        if user_input is not None:
            return self._save(user_input, unit)
        return self.async_show_form(
            step_id=step_id,
            data_schema=_build_options_schema(self._defaults(unit), keys, unit),
        )

    async def async_step_simple_comfort(self, user_input: dict[str, Any] | None = None):
        """Manage simple comfort options."""
        return await self._async_step_options("simple_comfort", SIMPLE_COMFORT_KEYS, user_input)

    async def async_step_transition_boost(self, user_input: dict[str, Any] | None = None):
        """Manage transition Auto and outdoor boost options."""
        return await self._async_step_options("transition_boost", TRANSITION_BOOST_KEYS, user_input)

    async def async_step_safety_limits(self, user_input: dict[str, Any] | None = None):
        """Manage safety and limit options."""
        return await self._async_step_options("safety_limits", SAFETY_LIMIT_KEYS, user_input)

    async def async_step_manual_windows(self, user_input: dict[str, Any] | None = None):
        """Manage manual override and window/door options."""
        return await self._async_step_options("manual_windows", MANUAL_WINDOWS_KEYS, user_input)

    async def async_step_comfort_curve(self, user_input: dict[str, Any] | None = None):
        """Manage comfort curve weights."""
        return await self._async_step_options("comfort_curve", COMFORT_CURVE_KEYS, user_input)

    async def async_step_legacy(self, user_input: dict[str, Any] | None = None):
        """Manage legacy explicit mode tuning."""
        return await self._async_step_options("legacy", LEGACY_KEYS, user_input)

    async def async_step_diagnostics(self, user_input: dict[str, Any] | None = None):
        """Manage diagnostics."""
        return await self._async_step_options("diagnostics", DIAGNOSTIC_KEYS, user_input)

    async def async_step_temperature_units(self, user_input: dict[str, Any] | None = None):
        """Manage temperature unit options."""
        current = self._unit_mode()
        if user_input is not None:
            raw = {**self._raw_options(), **user_input}
            unit = resolve_temperature_unit(self.hass, _temperature_unit_mode(raw))
            return self.async_create_entry(
                title="",
                data=self._normalized_settings_options(raw, unit),
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_TEMPERATURE_UNIT_MODE, default=current): _select_box(
                    TEMPERATURE_UNIT_MODES,
                    "temperature_unit_mode",
                ),
            }
        )
        return self.async_show_form(step_id="temperature_units", data_schema=schema)
