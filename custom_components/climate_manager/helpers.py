"""Helper functions for Climate Manager."""
from __future__ import annotations

from math import isfinite
from typing import Any

from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_TEMPERATURE_UNIT,
    PROFILE_AWAY,
    PROFILE_GUEST,
    PROFILE_HOME,
    PROFILE_SLEEP,
    TEMPERATURE_UNIT_MODE_CELSIUS,
    TEMPERATURE_UNIT_MODE_FAHRENHEIT,
    TEMPERATURE_UNIT_MODE_SYSTEM,
)
from .models import ManagerConfig


def state_is_on(hass: HomeAssistant, entity_id: str | None) -> bool:
    """Return True if entity state is on."""
    if not entity_id:
        return False
    return hass.states.is_state(entity_id, "on")


def state_text(hass: HomeAssistant, entity_id: str | None) -> str | None:
    """Return raw state string or None."""
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if state is None or state.state in {"unknown", "unavailable"}:
        return None
    return state.state


def state_float(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Return float state if valid."""
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if state is None:
        return None
    try:
        value = float(state.state)
    except (TypeError, ValueError):
        return None
    return value if isfinite(value) else None


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp value between minimum and maximum."""
    return max(minimum, min(maximum, value))


def round_to_half(value: float) -> float:
    """Round to the nearest 0.5 degree for thermostat-friendly targets."""
    sign = -1 if value < 0 else 1
    rounded = sign * (int(abs(value) * 2 + 0.5) / 2)
    return round(rounded, 1)


def resolve_temperature_unit(hass: HomeAssistant, unit_mode: str | None) -> str:
    """Resolve a unit mode to the active Home Assistant temperature unit."""
    if unit_mode == TEMPERATURE_UNIT_MODE_CELSIUS:
        return UnitOfTemperature.CELSIUS
    if unit_mode == TEMPERATURE_UNIT_MODE_FAHRENHEIT:
        return UnitOfTemperature.FAHRENHEIT
    if unit_mode == TEMPERATURE_UNIT_MODE_SYSTEM:
        units = getattr(getattr(hass, "config", None), "units", None)
        system_unit = getattr(units, "temperature_unit", None)
        if system_unit in {UnitOfTemperature.CELSIUS, UnitOfTemperature.FAHRENHEIT}:
            return system_unit
    return DEFAULT_TEMPERATURE_UNIT


def is_celsius_unit(unit: str | None) -> bool:
    """Return True when the unit is Celsius."""
    return unit == UnitOfTemperature.CELSIUS


def f_to_c_abs(value: float | None) -> float | None:
    """Convert an absolute Fahrenheit temperature to Celsius."""
    if value is None:
        return None
    return (value - 32.0) * 5.0 / 9.0


def c_to_f_abs(value: float | None) -> float | None:
    """Convert an absolute Celsius temperature to Fahrenheit."""
    if value is None:
        return None
    return (value * 9.0 / 5.0) + 32.0


def f_to_c_delta(value: float | None) -> float | None:
    """Convert a Fahrenheit temperature difference to Celsius scale."""
    if value is None:
        return None
    return value * 5.0 / 9.0


def c_to_f_delta(value: float | None) -> float | None:
    """Convert a Celsius temperature difference to Fahrenheit scale."""
    if value is None:
        return None
    return value * 9.0 / 5.0


def from_ha_temp(value: float | None, unit: str | None) -> float | None:
    """Convert an HA absolute temperature to internal Fahrenheit."""
    if is_celsius_unit(unit):
        return c_to_f_abs(value)
    return value


def to_ha_temp(value: float | None, unit: str | None) -> float | None:
    """Convert an internal Fahrenheit absolute temperature to HA units."""
    if is_celsius_unit(unit):
        return f_to_c_abs(value)
    return value


def from_ha_temp_delta(value: float | None, unit: str | None) -> float | None:
    """Convert an HA temperature difference to internal Fahrenheit scale."""
    if is_celsius_unit(unit):
        return c_to_f_delta(value)
    return value


def to_ha_temp_delta(value: float | None, unit: str | None) -> float | None:
    """Convert an internal Fahrenheit temperature difference to HA units."""
    if is_celsius_unit(unit):
        return f_to_c_delta(value)
    return value


def round_temperature_for_unit(value: float | None, unit: str | None) -> float | None:
    """Round a temperature value in its native unit for thermostat-friendly commands."""
    if value is None:
        return None
    return round_to_half(value)


def nearly_equal(left: float | None, right: float | None, threshold: float) -> bool:
    """Compare floats with threshold."""
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    return abs(left - right) < threshold


def curve_weight_for_profile(config: ManagerConfig, profile: str, *, cooling: bool = False) -> float:
    """Get curve weight for a profile."""
    if profile == PROFILE_HOME:
        return config.cool_curve_weight_home if cooling else config.curve_weight_home
    if profile == PROFILE_SLEEP:
        return config.cool_curve_weight_sleep if cooling else config.curve_weight_sleep
    if profile == PROFILE_GUEST:
        return config.cool_curve_weight_guest if cooling else config.curve_weight_guest
    if profile == PROFILE_AWAY:
        return config.cool_curve_weight_away if cooling else config.curve_weight_away
    return 0.0


def now() -> Any:
    """Timezone-aware now helper."""
    return dt_util.utcnow()
