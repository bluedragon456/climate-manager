"""Helper functions for Climate Manager."""
from __future__ import annotations

from math import isfinite
from typing import Any

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


def curve_weight_for_profile(config: ManagerConfig, profile: str) -> float:
    """Get curve weight for a profile."""
    if profile == PROFILE_HOME:
        return config.curve_weight_home
    if profile == PROFILE_SLEEP:
        return config.curve_weight_sleep
    if profile == PROFILE_GUEST:
        return config.curve_weight_guest
    if profile == PROFILE_AWAY:
        return config.curve_weight_away
    return 0.0


def now() -> Any:
    """Timezone-aware now helper."""
    return dt_util.utcnow()
