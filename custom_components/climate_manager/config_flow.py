"""Config flow for Climate Manager."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import *  # noqa: F403,F401

HVAC_PREFERENCE_OPTIONS = [
    selector.SelectOptionDict(value=HVAC_PREF_AUTO, label="Auto"),
    selector.SelectOptionDict(value=HVAC_PREF_HEAT, label="Heat"),
    selector.SelectOptionDict(value=HVAC_PREF_COOL, label="Cool"),
    selector.SelectOptionDict(value=HVAC_PREF_OFF, label="Off"),
]

MANUAL_BEHAVIOR_OPTIONS = [
    selector.SelectOptionDict(value=MANUAL_BEHAVIOR_IGNORE, label="Ignore"),
    selector.SelectOptionDict(value=MANUAL_BEHAVIOR_TEMPORARY, label="Temporary override"),
    selector.SelectOptionDict(value=MANUAL_BEHAVIOR_HOLD, label="Hold until cleared"),
]

WINDOWS_ACTION_OPTIONS = [
    selector.SelectOptionDict(value=WINDOWS_ACTION_OFF, label="Turn HVAC off"),
    selector.SelectOptionDict(value=WINDOWS_ACTION_HEAT_SETBACK, label="Heat setback"),
    selector.SelectOptionDict(value=WINDOWS_ACTION_COOL_SETBACK, label="Cool setback"),
]


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
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {**DEFAULT_OPTIONS, **self.config_entry.options}
        schema = vol.Schema(
            {
                vol.Required(CONF_SMART_CONTROL_ENABLED, default=options[CONF_SMART_CONTROL_ENABLED]): selector.BooleanSelector(),
                vol.Required(
                    CONF_HVAC_PREFERENCE,
                    default=options[CONF_HVAC_PREFERENCE],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=HVAC_PREFERENCE_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_HEAT_HOME, default=options[CONF_HEAT_HOME]): vol.Coerce(float),
                vol.Required(CONF_HEAT_SLEEP, default=options[CONF_HEAT_SLEEP]): vol.Coerce(float),
                vol.Required(CONF_HEAT_GUEST, default=options[CONF_HEAT_GUEST]): vol.Coerce(float),
                vol.Required(CONF_HEAT_AWAY, default=options[CONF_HEAT_AWAY]): vol.Coerce(float),
                vol.Required(CONF_COOL_HOME, default=options[CONF_COOL_HOME]): vol.Coerce(float),
                vol.Required(CONF_COOL_SLEEP, default=options[CONF_COOL_SLEEP]): vol.Coerce(float),
                vol.Required(CONF_COOL_GUEST, default=options[CONF_COOL_GUEST]): vol.Coerce(float),
                vol.Required(CONF_COOL_AWAY, default=options[CONF_COOL_AWAY]): vol.Coerce(float),
                vol.Required(CONF_CURVE_BAND_1_MAX, default=options[CONF_CURVE_BAND_1_MAX]): vol.Coerce(float),
                vol.Required(CONF_CURVE_BAND_1_OFFSET, default=options[CONF_CURVE_BAND_1_OFFSET]): vol.Coerce(float),
                vol.Required(CONF_CURVE_BAND_2_MAX, default=options[CONF_CURVE_BAND_2_MAX]): vol.Coerce(float),
                vol.Required(CONF_CURVE_BAND_2_OFFSET, default=options[CONF_CURVE_BAND_2_OFFSET]): vol.Coerce(float),
                vol.Required(CONF_CURVE_BAND_3_MAX, default=options[CONF_CURVE_BAND_3_MAX]): vol.Coerce(float),
                vol.Required(CONF_CURVE_BAND_3_OFFSET, default=options[CONF_CURVE_BAND_3_OFFSET]): vol.Coerce(float),
                vol.Required(CONF_CURVE_BAND_4_MAX, default=options[CONF_CURVE_BAND_4_MAX]): vol.Coerce(float),
                vol.Required(CONF_CURVE_BAND_4_OFFSET, default=options[CONF_CURVE_BAND_4_OFFSET]): vol.Coerce(float),
                vol.Required(CONF_CURVE_WEIGHT_HOME, default=options[CONF_CURVE_WEIGHT_HOME]): vol.Coerce(float),
                vol.Required(CONF_CURVE_WEIGHT_SLEEP, default=options[CONF_CURVE_WEIGHT_SLEEP]): vol.Coerce(float),
                vol.Required(CONF_CURVE_WEIGHT_GUEST, default=options[CONF_CURVE_WEIGHT_GUEST]): vol.Coerce(float),
                vol.Required(CONF_CURVE_WEIGHT_AWAY, default=options[CONF_CURVE_WEIGHT_AWAY]): vol.Coerce(float),
                vol.Required(
                    CONF_MANUAL_TEMP_BEHAVIOR,
                    default=options[CONF_MANUAL_TEMP_BEHAVIOR],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=MANUAL_BEHAVIOR_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_MANUAL_MODE_BEHAVIOR,
                    default=options[CONF_MANUAL_MODE_BEHAVIOR],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=MANUAL_BEHAVIOR_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_OVERRIDE_DURATION_MINUTES, default=options[CONF_OVERRIDE_DURATION_MINUTES]): vol.Coerce(int),
                vol.Required(CONF_MANUAL_GRACE_SECONDS, default=options[CONF_MANUAL_GRACE_SECONDS]): vol.Coerce(int),
                vol.Required(CONF_WINDOWS_OPEN_DELAY_MINUTES, default=options[CONF_WINDOWS_OPEN_DELAY_MINUTES]): vol.Coerce(int),
                vol.Required(CONF_WINDOWS_RESTORE_DELAY_MINUTES, default=options[CONF_WINDOWS_RESTORE_DELAY_MINUTES]): vol.Coerce(int),
                vol.Required(
                    CONF_WINDOWS_ACTION,
                    default=options[CONF_WINDOWS_ACTION],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=WINDOWS_ACTION_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_MIN_HEAT_TARGET, default=options[CONF_MIN_HEAT_TARGET]): vol.Coerce(float),
                vol.Required(CONF_MAX_HEAT_TARGET, default=options[CONF_MAX_HEAT_TARGET]): vol.Coerce(float),
                vol.Required(CONF_MIN_COOL_TARGET, default=options[CONF_MIN_COOL_TARGET]): vol.Coerce(float),
                vol.Required(CONF_MAX_COOL_TARGET, default=options[CONF_MAX_COOL_TARGET]): vol.Coerce(float),
                vol.Required(CONF_TEMP_CHANGE_THRESHOLD, default=options[CONF_TEMP_CHANGE_THRESHOLD]): vol.Coerce(float),
                vol.Required(CONF_CANCEL_OVERRIDE_ON_AWAY, default=options[CONF_CANCEL_OVERRIDE_ON_AWAY]): selector.BooleanSelector(),
                vol.Required(CONF_CANCEL_OVERRIDE_ON_WINDOWS, default=options[CONF_CANCEL_OVERRIDE_ON_WINDOWS]): selector.BooleanSelector(),
                vol.Required(CONF_CANCEL_OVERRIDE_ON_SLEEP, default=options[CONF_CANCEL_OVERRIDE_ON_SLEEP]): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
