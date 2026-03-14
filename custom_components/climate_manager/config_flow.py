"""Config flow for Climate Manager."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import *  # noqa: F403,F401

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


def _normalize_options(defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    data = dict(DEFAULT_OPTIONS)
    if defaults:
        data.update(defaults)

    return {
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
    }


def _float_box(default: float, *, min_value: float, max_value: float, step: float = 0.5):
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=min_value,
            max=max_value,
            step=step,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _int_box(default: int, *, min_value: int, max_value: int):
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=min_value,
            max=max_value,
            step=1,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _build_options_schema(defaults: dict[str, Any]) -> vol.Schema:
    defaults = _normalize_options(defaults)

    return vol.Schema(
        {
            vol.Required(CONF_SMART_CONTROL_ENABLED, default=defaults[CONF_SMART_CONTROL_ENABLED]): selector.BooleanSelector(),
            vol.Required(CONF_HVAC_PREFERENCE, default=defaults[CONF_HVAC_PREFERENCE]): selector.SelectSelector(
                selector.SelectSelectorConfig(options=HVAC_PREFERENCE_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Required(CONF_HEAT_HOME, default=defaults[CONF_HEAT_HOME]): _float_box(defaults[CONF_HEAT_HOME], min_value=30, max_value=100),
            vol.Required(CONF_HEAT_SLEEP, default=defaults[CONF_HEAT_SLEEP]): _float_box(defaults[CONF_HEAT_SLEEP], min_value=30, max_value=100),
            vol.Required(CONF_HEAT_GUEST, default=defaults[CONF_HEAT_GUEST]): _float_box(defaults[CONF_HEAT_GUEST], min_value=30, max_value=100),
            vol.Required(CONF_HEAT_AWAY, default=defaults[CONF_HEAT_AWAY]): _float_box(defaults[CONF_HEAT_AWAY], min_value=30, max_value=100),
            vol.Required(CONF_COOL_HOME, default=defaults[CONF_COOL_HOME]): _float_box(defaults[CONF_COOL_HOME], min_value=30, max_value=100),
            vol.Required(CONF_COOL_SLEEP, default=defaults[CONF_COOL_SLEEP]): _float_box(defaults[CONF_COOL_SLEEP], min_value=30, max_value=100),
            vol.Required(CONF_COOL_GUEST, default=defaults[CONF_COOL_GUEST]): _float_box(defaults[CONF_COOL_GUEST], min_value=30, max_value=100),
            vol.Required(CONF_COOL_AWAY, default=defaults[CONF_COOL_AWAY]): _float_box(defaults[CONF_COOL_AWAY], min_value=30, max_value=100),
            vol.Required(CONF_CURVE_BAND_1_MAX, default=defaults[CONF_CURVE_BAND_1_MAX]): _float_box(defaults[CONF_CURVE_BAND_1_MAX], min_value=-50, max_value=150),
            vol.Required(CONF_CURVE_BAND_1_OFFSET, default=defaults[CONF_CURVE_BAND_1_OFFSET]): _float_box(defaults[CONF_CURVE_BAND_1_OFFSET], min_value=-20, max_value=20),
            vol.Required(CONF_CURVE_BAND_2_MAX, default=defaults[CONF_CURVE_BAND_2_MAX]): _float_box(defaults[CONF_CURVE_BAND_2_MAX], min_value=-50, max_value=150),
            vol.Required(CONF_CURVE_BAND_2_OFFSET, default=defaults[CONF_CURVE_BAND_2_OFFSET]): _float_box(defaults[CONF_CURVE_BAND_2_OFFSET], min_value=-20, max_value=20),
            vol.Required(CONF_CURVE_BAND_3_MAX, default=defaults[CONF_CURVE_BAND_3_MAX]): _float_box(defaults[CONF_CURVE_BAND_3_MAX], min_value=-50, max_value=150),
            vol.Required(CONF_CURVE_BAND_3_OFFSET, default=defaults[CONF_CURVE_BAND_3_OFFSET]): _float_box(defaults[CONF_CURVE_BAND_3_OFFSET], min_value=-20, max_value=20),
            vol.Required(CONF_CURVE_BAND_4_MAX, default=defaults[CONF_CURVE_BAND_4_MAX]): _float_box(defaults[CONF_CURVE_BAND_4_MAX], min_value=-50, max_value=150),
            vol.Required(CONF_CURVE_BAND_4_OFFSET, default=defaults[CONF_CURVE_BAND_4_OFFSET]): _float_box(defaults[CONF_CURVE_BAND_4_OFFSET], min_value=-20, max_value=20),
            vol.Required(CONF_CURVE_WEIGHT_HOME, default=defaults[CONF_CURVE_WEIGHT_HOME]): _float_box(defaults[CONF_CURVE_WEIGHT_HOME], min_value=0, max_value=5, step=0.1),
            vol.Required(CONF_CURVE_WEIGHT_SLEEP, default=defaults[CONF_CURVE_WEIGHT_SLEEP]): _float_box(defaults[CONF_CURVE_WEIGHT_SLEEP], min_value=0, max_value=5, step=0.1),
            vol.Required(CONF_CURVE_WEIGHT_GUEST, default=defaults[CONF_CURVE_WEIGHT_GUEST]): _float_box(defaults[CONF_CURVE_WEIGHT_GUEST], min_value=0, max_value=5, step=0.1),
            vol.Required(CONF_CURVE_WEIGHT_AWAY, default=defaults[CONF_CURVE_WEIGHT_AWAY]): _float_box(defaults[CONF_CURVE_WEIGHT_AWAY], min_value=0, max_value=5, step=0.1),
            vol.Required(CONF_MANUAL_TEMP_BEHAVIOR, default=defaults[CONF_MANUAL_TEMP_BEHAVIOR]): selector.SelectSelector(
                selector.SelectSelectorConfig(options=MANUAL_BEHAVIOR_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Required(CONF_MANUAL_MODE_BEHAVIOR, default=defaults[CONF_MANUAL_MODE_BEHAVIOR]): selector.SelectSelector(
                selector.SelectSelectorConfig(options=MANUAL_BEHAVIOR_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Required(CONF_OVERRIDE_DURATION_MINUTES, default=defaults[CONF_OVERRIDE_DURATION_MINUTES]): _int_box(defaults[CONF_OVERRIDE_DURATION_MINUTES], min_value=1, max_value=1440),
            vol.Required(CONF_MANUAL_GRACE_SECONDS, default=defaults[CONF_MANUAL_GRACE_SECONDS]): _int_box(defaults[CONF_MANUAL_GRACE_SECONDS], min_value=0, max_value=600),
            vol.Required(CONF_WINDOWS_OPEN_DELAY_MINUTES, default=defaults[CONF_WINDOWS_OPEN_DELAY_MINUTES]): _int_box(defaults[CONF_WINDOWS_OPEN_DELAY_MINUTES], min_value=0, max_value=1440),
            vol.Required(CONF_WINDOWS_RESTORE_DELAY_MINUTES, default=defaults[CONF_WINDOWS_RESTORE_DELAY_MINUTES]): _int_box(defaults[CONF_WINDOWS_RESTORE_DELAY_MINUTES], min_value=0, max_value=1440),
            vol.Required(CONF_WINDOWS_ACTION, default=defaults[CONF_WINDOWS_ACTION]): selector.SelectSelector(
                selector.SelectSelectorConfig(options=WINDOWS_ACTION_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Required(CONF_MIN_HEAT_TARGET, default=defaults[CONF_MIN_HEAT_TARGET]): _float_box(defaults[CONF_MIN_HEAT_TARGET], min_value=30, max_value=100),
            vol.Required(CONF_MAX_HEAT_TARGET, default=defaults[CONF_MAX_HEAT_TARGET]): _float_box(defaults[CONF_MAX_HEAT_TARGET], min_value=30, max_value=100),
            vol.Required(CONF_MIN_COOL_TARGET, default=defaults[CONF_MIN_COOL_TARGET]): _float_box(defaults[CONF_MIN_COOL_TARGET], min_value=30, max_value=100),
            vol.Required(CONF_MAX_COOL_TARGET, default=defaults[CONF_MAX_COOL_TARGET]): _float_box(defaults[CONF_MAX_COOL_TARGET], min_value=30, max_value=100),
            vol.Required(CONF_TEMP_CHANGE_THRESHOLD, default=defaults[CONF_TEMP_CHANGE_THRESHOLD]): _float_box(defaults[CONF_TEMP_CHANGE_THRESHOLD], min_value=0, max_value=10, step=0.1),
            vol.Required(CONF_CANCEL_OVERRIDE_ON_AWAY, default=defaults[CONF_CANCEL_OVERRIDE_ON_AWAY]): selector.BooleanSelector(),
            vol.Required(CONF_CANCEL_OVERRIDE_ON_WINDOWS, default=defaults[CONF_CANCEL_OVERRIDE_ON_WINDOWS]): selector.BooleanSelector(),
            vol.Required(CONF_CANCEL_OVERRIDE_ON_SLEEP, default=defaults[CONF_CANCEL_OVERRIDE_ON_SLEEP]): selector.BooleanSelector(),
        }
    )


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
            await self.async_set_unique_id(user_input[CONF_THERMOSTAT_ENTITY])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Climate Manager", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_THERMOSTAT_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="climate")
                ),
                vol.Required(CONF_OUTDOOR_TEMP_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_SLEEP_SCHEDULE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="schedule")
                ),
                vol.Optional(CONF_AWAY_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="input_boolean")
                ),
                vol.Optional(CONF_GUEST_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="input_boolean")
                ),
                vol.Optional(CONF_OVERRIDE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="input_boolean")
                ),
                vol.Optional(CONF_WINDOWS_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),
                vol.Optional(CONF_SEASON_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["input_text", "sensor", "select"])
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)


class ClimateManagerOptionsFlow(config_entries.OptionsFlow):
    """Handle Climate Manager options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = _normalize_options({**self._config_entry.data, **self._config_entry.options})
        return self.async_show_form(step_id="init", data_schema=_build_options_schema(defaults))

