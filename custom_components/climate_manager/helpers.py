"""Helper functions for Climate Manager."""
from __future__ import annotations

from math import isfinite
from typing import Any

from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    PROFILE_AWAY,
    PROFILE_GUEST,
    PROFILE_HOME,
    PROFILE_SLEEP,
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


# Temperature unit conversion
#
# Climate Manager's internal logic operates entirely in Fahrenheit. These helpers
# convert at the Home Assistant I/O boundary when the user configures Celsius.
# Absolute temperatures use the full F<->C formula; deltas/offsets/spans convert
# by scale only (no +/-32). Values are passed through untouched for Fahrenheit so
# existing installs see no behavior change.


def is_celsius(unit: str | None) -> bool:
    """Return True if the configured unit is Celsius."""
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
    return value * 9.0 / 5.0 + 32.0


def f_to_c_delta(value: float | None) -> float | None:
    """Convert a Fahrenheit delta/span to Celsius (scale only)."""
    if value is None:
        return None
    return value * 5.0 / 9.0


def c_to_f_delta(value: float | None) -> float | None:
    """Convert a Celsius delta/span to Fahrenheit (scale only)."""
    if value is None:
        return None
    return value * 9.0 / 5.0


def from_ha_temp(value: float | None, unit: str | None) -> float | None:
    """Convert an absolute temperature read from Home Assistant to internal Fahrenheit."""
    if is_celsius(unit):
        return c_to_f_abs(value)
    return value


def to_ha_temp(value: float | None, unit: str | None) -> float | None:
    """Convert an internal Fahrenheit temperature to the Home Assistant unit."""
    if is_celsius(unit):
        return f_to_c_abs(value)
    return value


def from_ha_temp_delta(value: float | None, unit: str | None) -> float | None:
    """Convert a temperature delta read from Home Assistant to an internal Fahrenheit delta."""
    if is_celsius(unit):
        return c_to_f_delta(value)
    return value


def to_ha_temp_delta(value: float | None, unit: str | None) -> float | None:
    """Convert an internal Fahrenheit delta to the Home Assistant unit."""
    if is_celsius(unit):
        return f_to_c_delta(value)
    return value
