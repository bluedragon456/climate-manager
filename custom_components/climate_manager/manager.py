"""Climate manager brain."""
from __future__ import annotations
import asyncio
import logging
from collections.abc import Callable
from datetime import timedelta
from typing import Any
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from .const import (
    HVAC_PREF_COOL,
    HVAC_PREF_HEAT,
    HVAC_PREF_OFF,
    MANUAL_BEHAVIOR_HOLD,
    MANUAL_BEHAVIOR_IGNORE,
    MANUAL_BEHAVIOR_TEMPORARY,
    PROFILE_AWAY,
    PROFILE_GUEST,
    PROFILE_HOME,
    PROFILE_MANUAL_OVERRIDE,
    PROFILE_OVERRIDE_LOCK,
    PROFILE_PAUSED,
    PROFILE_SENSORS_OPEN,
    PROFILE_SLEEP,
    STATUS_CONTROLLING,
    STATUS_IDLE,
    STATUS_MANUAL_OVERRIDE,
    STATUS_PAUSED,
    STATUS_UNAVAILABLE,
    STATUS_WINDOWS_BACKOFF,
    WINDOWS_ACTION_COOL_SETBACK,
    WINDOWS_ACTION_HEAT_SETBACK,
    WINDOWS_ACTION_OFF,
)
from .helpers import clamp, curve_weight_for_profile, nearly_equal, now, state_float, state_is_on, state_text
from .models import ManagerConfig, RuntimeState, ThermostatSnapshot
from .restore import RuntimeStore
_LOGGER = logging.getLogger(__name__)
class ClimateManager:
    """Main runtime manager."""
    def __init__(self, hass: HomeAssistant, entry_id: str, config: ManagerConfig) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.config = config
        self.runtime = RuntimeState()
        self._runtime_store = RuntimeStore(hass, entry_id)
        self._listeners: list[CALLBACK_TYPE] = []
        self._subscribers: list[Callable[[], None]] = []
        self._save_handle: CALLBACK_TYPE | None = None
        self._window_timer_handle: CALLBACK_TYPE | None = None
        self._override_timer_handle: CALLBACK_TYPE | None = None
        self._lock = asyncio.Lock()
        self.last_reason: str | None = None
        self.last_action: str | None = None
    async def async_initialize(self) -> None:
        """Initialize manager and listeners."""
        self.runtime = await self._runtime_store.async_load()
        _LOGGER.debug("Loaded runtime state for %s: %s", self.entry_id, self.runtime)
        tracked = [
            self.config.thermostat_entity,
            self.config.outdoor_temp_entity,
            self.config.sleep_schedule_entity,
            self.config.away_entity,
            self.config.guest_entity,
            self.config.override_entity,
            self.config.windows_entity,
            self.config.season_entity,
        ]
        tracked_entities = [entity_id for entity_id in tracked if entity_id]
        if tracked_entities:
            self._listeners.append(
                async_track_state_change_event(
                    self.hass,
                    tracked_entities,
                    self._handle_state_change,
                )
            )
        self._schedule_window_recalc_if_needed()
        self._schedule_override_recalc_if_needed()
        await self.async_recalculate("startup")
    async def async_shutdown(self) -> None:
        """Shutdown manager."""
        for remove in self._listeners:
            remove()
        self._listeners.clear()
        if self._save_handle:
            self._save_handle()
            self._save_handle = None
        if self._window_timer_handle:
            self._window_timer_handle()
            self._window_timer_handle = None
        if self._override_timer_handle:
            self._override_timer_handle()
            self._override_timer_handle = None
        await self._runtime_store.async_save(self.runtime)
    @callback
    def async_subscribe(self, update_callback: Callable[[], None]) -> CALLBACK_TYPE:
        """Subscribe entity updates."""
        self._subscribers.append(update_callback)
        @callback
        def unsubscribe() -> None:
            if update_callback in self._subscribers:
                self._subscribers.remove(update_callback)
        return unsubscribe
    @callback
    def _notify_subscribers(self) -> None:
        for subscriber in list(self._subscribers):
            subscriber()
    @callback
    def _handle_state_change(self, event: Any) -> None:
        entity_id = event.data.get("entity_id")
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        _LOGGER.debug(
            "State change for %s: %s -> %s",
            entity_id,
            None if old_state is None else old_state.state,
            None if new_state is None else new_state.state,
        )
        if entity_id == self.config.windows_entity:
            self._schedule_window_recalc_if_needed()
        self.hass.async_create_task(self.async_recalculate(f"state_change:{entity_id}"))
    @callback
    def _schedule_window_recalc_if_needed(self) -> None:
        """Schedule a recalc for window open/close timers."""
        if self._window_timer_handle:
            self._window_timer_handle()
            self._window_timer_handle = None
        if not self.config.windows_entity:
            return
        entity_state = self.hass.states.get(self.config.windows_entity)
        current = now()
        if entity_state is not None and entity_state.state == STATE_ON:
            if self.runtime.windows_open_since is not None and self.runtime.windows_backoff_until is not None:
                fire_in = (self.runtime.windows_backoff_until - current).total_seconds()
                if fire_in > 0:
                    self._window_timer_handle = async_call_later(
                        self.hass,
                        fire_in,
                        self._async_window_timer_recalc,
                    )
            return
        if self.runtime.windows_closed_since is not None:
            fire_in = (
                self.runtime.windows_closed_since
                + timedelta(seconds=self.config.windows_restore_delay_minutes)
                - current
            ).total_seconds()
            if fire_in > 0:
                self._window_timer_handle = async_call_later(
                    self.hass,
                    fire_in,
                    self._async_window_timer_recalc,
                )
    async def _async_window_timer_recalc(self, *_: Any) -> None:
        """Recalculate when a window timer expires."""
        self._window_timer_handle = None
        await self.async_recalculate("window_timer")
    @callback
    def _schedule_override_recalc_if_needed(self) -> None:
        """Schedule a recalc when a temporary override should expire."""
        if self._override_timer_handle:
            self._override_timer_handle()
            self._override_timer_handle = None
        if not self.runtime.manual_override_active or self.runtime.manual_hold:
            return
        expires = self.runtime.manual_override_until
        if expires is None:
            return
        fire_in = (expires - now()).total_seconds()
        if fire_in > 0:
            self._override_timer_handle = async_call_later(
                self.hass,
                fire_in,
                self._async_override_timer_recalc,
            )
    async def _async_override_timer_recalc(self, *_: Any) -> None:
        """Recalculate when an override timer expires."""
        self._override_timer_handle = None
        await self.async_recalculate("override_timer")
    async def async_recalculate(self, reason: str) -> None:
        """Main control loop."""
        async with self._lock:
            self.last_reason = reason
            _LOGGER.debug("Recalculating climate manager because %s", reason)
            self._refresh_override_state()
            thermostat = self._thermostat_snapshot()
            if not thermostat.available:
                self.runtime.status = STATUS_UNAVAILABLE
                self._schedule_save()
                self._notify_subscribers()
                return
            if reason == "startup" or reason.startswith(f"state_change:{self.config.thermostat_entity}"):
                self._detect_manual_change(thermostat)
            profile = self._resolve_profile()
            desired_mode = self._resolve_desired_hvac_mode(profile)
            target_heat, target_cool = self._resolve_targets(profile, desired_mode)
            self.runtime.active_profile = profile
            self.runtime.desired_hvac_mode = desired_mode
            self.runtime.target_heat = target_heat
            self.runtime.target_cool = target_cool
            await self._apply_if_needed(thermostat)
            self._update_status()
            self._schedule_window_recalc_if_needed()
            self._schedule_override_recalc_if_needed()
            self._schedule_save()
            self._notify_subscribers()
    def _refresh_override_state(self) -> None:
        current = now()
        if self.runtime.manual_override_active and not self.runtime.manual_hold:
            expires = self.runtime.manual_override_until
            if expires and current >= expires:
                _LOGGER.info("Manual override expired for %s at %s", self.entry_id, expires.isoformat())
                self.runtime.manual_override_active = False
                self.runtime.manual_override_until = None
        if self.runtime.manual_override_active:
            if self.config.cancel_override_on_away and state_is_on(self.hass, self.config.away_entity):
                _LOGGER.debug("Canceling override because away mode is on")
                self._clear_manual_override()
            elif self.config.cancel_override_on_windows and self._windows_backoff_active():
                _LOGGER.debug("Canceling override because windows backoff activated")
                self._clear_manual_override()
            elif self.config.cancel_override_on_sleep and state_is_on(self.hass, self.config.sleep_schedule_entity):
                _LOGGER.debug("Canceling override because sleep mode is on")
                self._clear_manual_override()
    def _resolve_profile(self) -> str:
        if not self.config.smart_control_enabled or self.runtime.paused:
            return PROFILE_PAUSED
        if state_is_on(self.hass, self.config.override_entity):
            return PROFILE_OVERRIDE_LOCK
        if self.runtime.manual_override_active:
            return PROFILE_MANUAL_OVERRIDE
        if self._windows_backoff_active():
            self.runtime.windows_backoff_active = True
            return PROFILE_SENSORS_OPEN
        self.runtime.windows_backoff_active = False
        if state_is_on(self.hass, self.config.away_entity):
            return PROFILE_AWAY
        if state_is_on(self.hass, self.config.guest_entity):
            return PROFILE_GUEST
        if state_is_on(self.hass, self.config.sleep_schedule_entity):
            return PROFILE_SLEEP
        return PROFILE_HOME
    def _resolve_desired_hvac_mode(self, profile: str) -> str | None:
        if profile in {PROFILE_PAUSED, PROFILE_OVERRIDE_LOCK, PROFILE_MANUAL_OVERRIDE}:
            return None
        if profile == PROFILE_SENSORS_OPEN:
            if self.config.windows_action == WINDOWS_ACTION_OFF:
                return HVAC_PREF_OFF
            if self.config.windows_action == WINDOWS_ACTION_HEAT_SETBACK:
                return HVAC_PREF_HEAT
            if self.config.windows_action == WINDOWS_ACTION_COOL_SETBACK:
                return HVAC_PREF_COOL
        preference = self.config.hvac_preference
        if preference in {HVAC_PREF_HEAT, HVAC_PREF_COOL, HVAC_PREF_OFF}:
            return preference
        season = (state_text(self.hass, self.config.season_entity) or "").lower()
        if season == "winter":
            return HVAC_PREF_HEAT
        if season == "summer":
            return HVAC_PREF_COOL
        return "heat_cool"
    def _resolve_targets(self, profile: str, desired_mode: str | None) -> tuple[float | None, float | None]:
        base_heat = None
        base_cool = None
        if profile not in {PROFILE_PAUSED, PROFILE_OVERRIDE_LOCK, PROFILE_MANUAL_OVERRIDE}:
            if profile == PROFILE_SENSORS_OPEN:
                base_heat = self.config.min_heat_target
                base_cool = self.config.max_cool_target
            elif profile == PROFILE_AWAY:
                base_heat = self.config.heat_away
                base_cool = self.config.cool_away
            elif profile == PROFILE_GUEST:
                base_heat = self.config.heat_guest
                base_cool = self.config.cool_guest
            elif profile == PROFILE_SLEEP:
                base_heat = self.config.heat_sleep
                base_cool = self.config.cool_sleep
            else:
                base_heat = self.config.heat_home
                base_cool = self.config.cool_home
        heat_offset = self._resolve_heat_curve_offset(profile)
        self.runtime.comfort_offset = heat_offset
        if desired_mode in {HVAC_PREF_HEAT, "heat_cool"} and base_heat is not None:
            base_heat = clamp(base_heat + heat_offset, self.config.min_heat_target, self.config.max_heat_target)
        if desired_mode in {HVAC_PREF_COOL, "heat_cool"} and base_cool is not None:
            base_cool = clamp(base_cool, self.config.min_cool_target, self.config.max_cool_target)
        if desired_mode == HVAC_PREF_HEAT:
            return base_heat, None
        if desired_mode == HVAC_PREF_COOL:
            return None, base_cool
        if desired_mode == "heat_cool":
            if base_heat is not None and base_cool is not None and base_heat >= base_cool:
                base_cool = base_heat + 2.0
            return base_heat, base_cool
        return None, None
    def _resolve_heat_curve_offset(self, profile: str) -> float:
        outdoor = state_float(self.hass, self.config.outdoor_temp_entity)
        if outdoor is None:
            return 0.0
        if outdoor <= self.config.curve_band_1_max:
            band_offset = self.config.curve_band_1_offset
        elif outdoor <= self.config.curve_band_2_max:
            band_offset = self.config.curve_band_2_offset
        elif outdoor <= self.config.curve_band_3_max:
            band_offset = self.config.curve_band_3_offset
        elif outdoor <= self.config.curve_band_4_max:
            band_offset = self.config.curve_band_4_offset
        else:
            band_offset = 0.0
        weighted = round(band_offset * curve_weight_for_profile(self.config, profile), 1)
        _LOGGER.debug(
            "Outdoor temp %s selected heat curve offset %s weighted to %s for profile %s",
            outdoor,
            band_offset,
            weighted,
            profile,
        )
        return weighted
    @property
    def current_set_temperature(self) -> float | None:
        """Return the thermostat current primary set temperature."""
        thermostat = self._thermostat_snapshot()
        if not thermostat.available:
            return None
        if thermostat.target_temp is not None:
            return thermostat.target_temp
        if thermostat.target_temp_low is not None:
            return thermostat.target_temp_low
        return thermostat.target_temp_high
    def _thermostat_snapshot(self) -> ThermostatSnapshot:
        state = self.hass.states.get(self.config.thermostat_entity)
        if state is None or state.state in {"unavailable", "unknown"}:
            return ThermostatSnapshot(None, None, None, None, None, False)
        def attr_float(key: str) -> float | None:
            value = state.attributes.get(key)
            if value is None:
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        return ThermostatSnapshot(
            hvac_mode=state.state,
            target_temp=attr_float("temperature"),
            target_temp_low=attr_float("target_temp_low"),
            target_temp_high=attr_float("target_temp_high"),
            current_temperature=attr_float("current_temperature"),
            available=True,
        )
    def _detect_manual_change(self, thermostat: ThermostatSnapshot) -> None:
        if self.runtime.last_command_time is None:
            return
        grace_window = self.runtime.last_command_time + timedelta(seconds=self.config.manual_grace_seconds)
        if now() <= grace_window:
            return
        mode_changed = (
            self.runtime.last_commanded_hvac_mode is not None
            and thermostat.hvac_mode is not None
            and thermostat.hvac_mode != self.runtime.last_commanded_hvac_mode
        )
        temp_changed = False
        if thermostat.hvac_mode == "heat_cool":
            temp_changed = not (
                nearly_equal(
                    thermostat.target_temp_low,
                    self.runtime.last_commanded_low,
                    self.config.temp_change_threshold,
                )
                and nearly_equal(
                    thermostat.target_temp_high,
                    self.runtime.last_commanded_high,
                    self.config.temp_change_threshold,
                )
            )
        else:
            temp_changed = not nearly_equal(
                thermostat.target_temp,
                self.runtime.last_commanded_temp,
                self.config.temp_change_threshold,
            )
        if mode_changed or temp_changed:
            _LOGGER.info(
                "Manual change candidate for %s: hvac_mode current=%s commanded=%s temp current=%s commanded=%s low current=%s commanded=%s high current=%s commanded=%s",
                self.entry_id,
                thermostat.hvac_mode,
                self.runtime.last_commanded_hvac_mode,
                thermostat.target_temp,
                self.runtime.last_commanded_temp,
                thermostat.target_temp_low,
                self.runtime.last_commanded_low,
                thermostat.target_temp_high,
                self.runtime.last_commanded_high,
            )
        if mode_changed:
            self._apply_manual_behavior(self.config.manual_mode_behavior, "manual hvac mode change detected")
        elif temp_changed:
            self._apply_manual_behavior(self.config.manual_temp_behavior, "manual temperature change detected")
    def _apply_manual_behavior(self, behavior: str, reason: str) -> None:
        if behavior == MANUAL_BEHAVIOR_IGNORE:
            _LOGGER.info("Ignoring manual behavior trigger for %s because behavior is ignore", self.entry_id)
            return
        if behavior == MANUAL_BEHAVIOR_HOLD:
            self.runtime.manual_override_active = True
            self.runtime.manual_hold = True
            self.runtime.manual_override_until = None
        elif behavior == MANUAL_BEHAVIOR_TEMPORARY:
            self.runtime.manual_override_active = True
            self.runtime.manual_hold = False
            self.runtime.manual_override_until = now() + timedelta(minutes=self.config.override_duration_minutes)
        _LOGGER.info(
            "%s; behavior=%s override active=%s until=%s hold=%s",
            reason,
            behavior,
            self.runtime.manual_override_active,
            self.runtime.manual_override_until,
            self.runtime.manual_hold,
        )
    def _clear_manual_override(self) -> None:
        self.runtime.manual_override_active = False
        self.runtime.manual_override_until = None
        self.runtime.manual_hold = False
    def _clear_windows_backoff_state(self) -> None:
        self.runtime.windows_open_since = None
        self.runtime.windows_closed_since = None
        self.runtime.windows_backoff_until = None
        self.runtime.windows_backoff_active = False
    async def async_clear_override(self) -> None:
        """Clear a manual override and re-baseline manual detection."""
        self.last_action = "clear_override"
        self._clear_manual_override()
        thermostat = self._thermostat_snapshot()
        if thermostat.available:
            self.runtime.last_commanded_hvac_mode = thermostat.hvac_mode
            self.runtime.last_commanded_temp = thermostat.target_temp
            self.runtime.last_commanded_low = thermostat.target_temp_low
            self.runtime.last_commanded_high = thermostat.target_temp_high
            self.runtime.last_command_time = now()
        await self.async_recalculate("clear_override")
    async def async_pause(self) -> None:
        """Pause smart control."""
        self.last_action = "pause"
        self.runtime.paused = True
        await self.async_recalculate("pause")
    async def async_resume(self) -> None:
        """Resume smart control."""
        self.last_action = "resume"
        self.runtime.paused = False
        await self.async_recalculate("resume")
    async def async_set_temporary_override(
        self,
        duration_minutes: int,
        target_temp: float | None = None,
        hvac_mode: str | None = None,
    ) -> None:
        """Set a temporary override."""
        self.last_action = "set_temporary_override"
        self.runtime.manual_override_active = True
        self.runtime.manual_hold = False
        self.runtime.manual_override_until = now() + timedelta(minutes=duration_minutes)
        if hvac_mode:
            await self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {ATTR_ENTITY_ID: self.config.thermostat_entity, "hvac_mode": hvac_mode},
                blocking=True,
            )
        if target_temp is not None:
            await self.hass.services.async_call(
                "climate",
                "set_temperature",
                {ATTR_ENTITY_ID: self.config.thermostat_entity, "temperature": target_temp},
                blocking=True,
            )
        await self.async_recalculate("set_temporary_override")
    def _windows_backoff_active(self) -> bool:
        if not self.config.windows_entity:
            self._clear_windows_backoff_state()
            return False
        current = now()
        entity_state = self.hass.states.get(self.config.windows_entity)
        is_open = entity_state is not None and entity_state.state == STATE_ON
        open_delay = timedelta(minutes=self.config.windows_open_delay_minutes)
        close_buffer = timedelta(seconds=self.config.windows_restore_delay_minutes)
        if is_open:
            if self.runtime.windows_open_since is None:
                self.runtime.windows_open_since = current
            self.runtime.windows_closed_since = None
            self.runtime.windows_backoff_until = self.runtime.windows_open_since + open_delay
            return current >= self.runtime.windows_backoff_until
        if self.runtime.windows_open_since is None:
            self.runtime.windows_backoff_until = None
            self.runtime.windows_closed_since = None
            return False
        if self.runtime.windows_closed_since is None:
            self.runtime.windows_closed_since = current
        if current - self.runtime.windows_closed_since < close_buffer:
            return self.runtime.windows_backoff_until is not None and current >= self.runtime.windows_backoff_until
        self._clear_windows_backoff_state()
        return False
    async def _apply_if_needed(self, thermostat: ThermostatSnapshot) -> None:
        if self.runtime.active_profile in {PROFILE_PAUSED, PROFILE_OVERRIDE_LOCK, PROFILE_MANUAL_OVERRIDE}:
            _LOGGER.debug("Skipping apply because profile is %s", self.runtime.active_profile)
            return
        desired_mode = self.runtime.desired_hvac_mode
        target_heat = self.runtime.target_heat
        target_cool = self.runtime.target_cool
        if desired_mode is None:
            return
        if desired_mode == HVAC_PREF_OFF:
            if thermostat.hvac_mode != STATE_OFF:
                await self._async_set_hvac_mode(STATE_OFF)
            return
        if thermostat.hvac_mode != desired_mode:
            await self._async_set_hvac_mode(desired_mode)
        if desired_mode == HVAC_PREF_HEAT and target_heat is not None:
            if not nearly_equal(thermostat.target_temp, target_heat, self.config.temp_change_threshold):
                await self._async_set_temperature(temperature=target_heat)
        elif desired_mode == HVAC_PREF_COOL and target_cool is not None:
            if not nearly_equal(thermostat.target_temp, target_cool, self.config.temp_change_threshold):
                await self._async_set_temperature(temperature=target_cool)
        elif desired_mode == "heat_cool" and target_heat is not None and target_cool is not None:
            if not (
                nearly_equal(thermostat.target_temp_low, target_heat, self.config.temp_change_threshold)
                and nearly_equal(thermostat.target_temp_high, target_cool, self.config.temp_change_threshold)
            ):
                await self._async_set_temperature(target_temp_low=target_heat, target_temp_high=target_cool)
    async def _async_set_hvac_mode(self, hvac_mode: str) -> None:
        self.last_action = f"set_hvac_mode:{hvac_mode}"
        _LOGGER.debug("Applying HVAC mode %s to %s", hvac_mode, self.config.thermostat_entity)
        await self.hass.services.async_call(
            "climate",
            "set_hvac_mode",
            {ATTR_ENTITY_ID: self.config.thermostat_entity, "hvac_mode": hvac_mode},
            blocking=True,
        )
        self.runtime.last_commanded_hvac_mode = hvac_mode
        self.runtime.last_command_time = now()
    async def _async_set_temperature(
        self,
        temperature: float | None = None,
        target_temp_low: float | None = None,
        target_temp_high: float | None = None,
    ) -> None:
        data: dict[str, Any] = {ATTR_ENTITY_ID: self.config.thermostat_entity}
        if temperature is not None:
            data["temperature"] = temperature
        if target_temp_low is not None:
            data["target_temp_low"] = target_temp_low
        if target_temp_high is not None:
            data["target_temp_high"] = target_temp_high
        self.last_action = f"set_temperature:{data}"
        _LOGGER.debug("Applying temperature payload %s to %s", data, self.config.thermostat_entity)
        await self.hass.services.async_call("climate", "set_temperature", data, blocking=True)
        self.runtime.last_commanded_temp = temperature
        self.runtime.last_commanded_low = target_temp_low
        self.runtime.last_commanded_high = target_temp_high
        self.runtime.last_command_time = now()
    def _update_status(self) -> None:
        if self.runtime.active_profile == PROFILE_PAUSED:
            self.runtime.status = STATUS_PAUSED
        elif self.runtime.active_profile == PROFILE_MANUAL_OVERRIDE:
            self.runtime.status = STATUS_MANUAL_OVERRIDE
        elif self.runtime.active_profile == PROFILE_SENSORS_OPEN:
            self.runtime.status = STATUS_WINDOWS_BACKOFF
        elif self.runtime.desired_hvac_mode is None:
            self.runtime.status = STATUS_IDLE
        else:
            self.runtime.status = STATUS_CONTROLLING
    def _schedule_save(self) -> None:
        if self._save_handle:
            self._save_handle()
        self._save_handle = async_call_later(self.hass, 2, self._async_save_runtime)
    async def _async_save_runtime(self, *_: Any) -> None:
        self._save_handle = None
        await self._runtime_store.async_save(self.runtime)





