"""Regression tests for the opt-in window temperature safety control layer."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from homeassistant_stubs import install_homeassistant_stubs, install_package_stub


install_homeassistant_stubs()
install_package_stub()

from custom_components.climate_manager.const import (  # noqa: E402
    HVAC_PREF_AUTO,
    HVAC_PREF_COOL,
    HVAC_PREF_HEAT,
    HVAC_PREF_OFF,
    PROFILE_AWAY,
    PROFILE_GUEST,
    PROFILE_HOME,
    PROFILE_MANUAL_OVERRIDE,
    PROFILE_OVERRIDE_LOCK,
    PROFILE_PRE_ARRIVAL,
    PROFILE_SENSORS_OPEN,
    PROFILE_SLEEP,
    STATUS_UNAVAILABLE,
    STATUS_WINDOW_SAFETY_OVERRIDE,
)
from custom_components.climate_manager.manager import ClimateManager  # noqa: E402
from custom_components.climate_manager.models import ManagerConfig, RuntimeState  # noqa: E402


class FakeStates:
    def __init__(self, states: dict[str, object]) -> None:
        self.states = states

    def get(self, entity_id):
        value = self.states.get(entity_id)
        if value is None:
            return None
        if hasattr(value, "state"):
            return value
        return SimpleNamespace(state=value, attributes={})

    def is_state(self, entity_id, state) -> bool:
        current = self.get(entity_id)
        return current is not None and current.state == state


class FakeServices:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict, bool]] = []

    async def async_call(self, domain, service, data, blocking=True):
        self.calls.append((domain, service, data, blocking))


class Clock:
    def __init__(self) -> None:
        self.current = datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc)

    def advance(self, **kwargs) -> None:
        self.current += timedelta(**kwargs)


class WindowSafetyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.clock = Clock()
        self.now_patch = patch(
            "custom_components.climate_manager.manager.now",
            side_effect=lambda: self.clock.current,
        )
        self.now_patch.start()

    def tearDown(self) -> None:
        self.now_patch.stop()

    def make_manager(
        self,
        *,
        enabled: bool = True,
        indoor: float | None = 70.0,
        thermostat_state: str = "off",
        window_state: str = "on",
        preference: str = HVAC_PREF_AUTO,
        cancel_override_on_windows: bool = False,
        minimum: float = 50.0,
        maximum: float = 80.0,
        hysteresis: float = 2.0,
        maximum_minutes: int = 240,
        supported_modes: list[str] | None = None,
    ) -> ClimateManager:
        attributes = {"temperature": 70.0}
        if indoor is not None:
            attributes["current_temperature"] = indoor
        if supported_modes is not None:
            attributes["hvac_modes"] = supported_modes
        states = {
            "binary_sensor.windows": window_state,
            "climate.test": SimpleNamespace(state=thermostat_state, attributes=attributes),
            "sensor.outdoor": "75",
            "sensor.season": "summer",
            "input_boolean.away": "off",
            "input_boolean.guest": "off",
            "input_boolean.override": "off",
            "input_boolean.pre_arrival": "off",
            "schedule.sleep": "off",
        }
        hass = SimpleNamespace(states=FakeStates(states), services=FakeServices())
        config = ManagerConfig(
            "climate.test",
            outdoor_temp_entity="sensor.outdoor",
            away_entity="input_boolean.away",
            guest_entity="input_boolean.guest",
            override_entity="input_boolean.override",
            pre_arrival_entity="input_boolean.pre_arrival",
            sleep_schedule_entity="schedule.sleep",
            windows_entity="binary_sensor.windows",
            season_entity="sensor.season",
            hvac_preference=preference,
            windows_open_delay_minutes=15,
            windows_restore_delay_minutes=15,
            windows_action="off",
            windows_safety_override_enabled=enabled,
            windows_safety_maximum_backoff_minutes=maximum_minutes,
            windows_safety_min_indoor_temperature=minimum,
            windows_safety_max_indoor_temperature=maximum,
            windows_safety_hysteresis=hysteresis,
            cancel_override_on_windows=cancel_override_on_windows,
        )
        manager = ClimateManager(hass, "entry", config)
        manager._schedule_save = lambda: None
        manager._schedule_override_recalc_if_needed = lambda: None
        return manager

    def activate_backoff(self, manager: ClimateManager, *, age_minutes: int = 20) -> None:
        manager.runtime.windows_open_since = self.clock.current - timedelta(minutes=age_minutes + 15)
        manager.runtime.windows_backoff_until = self.clock.current - timedelta(minutes=age_minutes)
        manager.runtime.windows_backoff_active = True

    def set_indoor(self, manager: ClimateManager, value: float) -> None:
        manager.hass.states.states["climate.test"].attributes["current_temperature"] = value

    def set_window(self, manager: ClimateManager, value: str) -> None:
        manager.hass.states.states["binary_sensor.windows"] = value

    async def test_disabled_feature_preserves_indefinite_windows_action_off(self) -> None:
        manager = self.make_manager(enabled=False, indoor=85.0)
        self.activate_backoff(manager, age_minutes=12 * 60)

        await manager.async_recalculate("service")

        self.assertFalse(manager.runtime.windows_safety_override_active)
        self.assertEqual(manager.runtime.active_profile, PROFILE_SENSORS_OPEN)
        self.assertEqual(manager.runtime.desired_hvac_mode, HVAC_PREF_OFF)
        self.assertEqual(manager.window_safety_state, "disabled")

    async def test_high_temperature_triggers_cooling_with_hysteresis_target(self) -> None:
        manager = self.make_manager(indoor=80.0)
        self.activate_backoff(manager)

        await manager.async_recalculate("service")

        self.assertTrue(manager.runtime.windows_safety_override_active)
        self.assertEqual(manager.runtime.windows_safety_activation_reason, "high_indoor_temperature")
        self.assertEqual(manager.runtime.active_profile, PROFILE_SENSORS_OPEN)
        self.assertEqual(manager.runtime.desired_hvac_mode, HVAC_PREF_COOL)
        self.assertEqual(manager.runtime.target_cool, 78.0)
        self.assertEqual(manager.runtime.status, STATUS_WINDOW_SAFETY_OVERRIDE)

    async def test_window_open_twelve_hours_and_hot_house_activates_safety(self) -> None:
        manager = self.make_manager(indoor=85.0)
        self.activate_backoff(manager, age_minutes=12 * 60)

        await manager.async_recalculate("service")

        self.assertTrue(manager.runtime.windows_safety_override_active)
        self.assertEqual(manager.runtime.windows_safety_activation_reason, "high_indoor_temperature")
        self.assertEqual(manager.runtime.desired_hvac_mode, HVAC_PREF_COOL)
        self.assertEqual(manager.runtime.target_cool, 78.0)

    async def test_low_temperature_triggers_heating_with_hysteresis_target(self) -> None:
        manager = self.make_manager(indoor=50.0)
        self.activate_backoff(manager)

        await manager.async_recalculate("service")

        self.assertEqual(manager.runtime.windows_safety_activation_reason, "low_indoor_temperature")
        self.assertEqual(manager.runtime.desired_hvac_mode, HVAC_PREF_HEAT)
        self.assertEqual(manager.runtime.target_heat, 52.0)

    async def test_maximum_duration_activates_independent_heat_cool_envelope(self) -> None:
        manager = self.make_manager(indoor=70.0, maximum_minutes=240)
        self.activate_backoff(manager, age_minutes=240)

        await manager.async_recalculate("service")

        self.assertEqual(manager.runtime.windows_safety_activation_reason, "maximum_backoff_duration")
        self.assertEqual(manager.runtime.desired_hvac_mode, "heat_cool")
        self.assertEqual((manager.runtime.target_heat, manager.runtime.target_cool), (52.0, 78.0))
        temperature_calls = [call for call in manager.hass.services.calls if call[1] == "set_temperature"]
        self.assertEqual(temperature_calls[-1][2]["target_temp_low"], 52.0)
        self.assertEqual(temperature_calls[-1][2]["target_temp_high"], 78.0)

    async def test_maximum_duration_uses_single_mode_fallback_without_heat_cool(self) -> None:
        manager = self.make_manager(
            indoor=70.0,
            maximum_minutes=240,
            supported_modes=["off", "heat", "cool"],
        )
        self.activate_backoff(manager, age_minutes=240)

        await manager.async_recalculate("service")

        self.assertEqual(manager.runtime.desired_hvac_mode, HVAC_PREF_COOL)
        self.assertEqual(manager.runtime.target_cool, 78.0)
        self.assertEqual(
            manager.window_safety_capability_issue,
            "heat_cool_not_supported_using_single_mode_fallback",
        )

    async def test_maximum_duration_works_with_heat_only_thermostat(self) -> None:
        manager = self.make_manager(
            indoor=70.0,
            maximum_minutes=240,
            supported_modes=["off", "heat"],
        )
        self.activate_backoff(manager, age_minutes=240)

        await manager.async_recalculate("service")

        self.assertEqual(manager.runtime.desired_hvac_mode, HVAC_PREF_HEAT)
        self.assertEqual(manager.runtime.target_heat, 52.0)
        self.assertEqual(manager.window_safety_capability_issue, "cooling_not_supported")

    async def test_high_temperature_can_use_heat_cool_when_cool_is_not_separate(self) -> None:
        manager = self.make_manager(
            indoor=82.0,
            supported_modes=["off", "heat_cool"],
        )
        self.activate_backoff(manager)

        await manager.async_recalculate("service")

        self.assertEqual(manager.runtime.desired_hvac_mode, "heat_cool")
        self.assertEqual((manager.runtime.target_heat, manager.runtime.target_cool), (52.0, 78.0))

    async def test_missing_required_thermostat_mode_is_blocked_and_diagnosed(self) -> None:
        manager = self.make_manager(
            indoor=82.0,
            supported_modes=["off", "heat"],
        )
        self.activate_backoff(manager)

        await manager.async_recalculate("service")

        self.assertEqual(manager.runtime.desired_hvac_mode, HVAC_PREF_COOL)
        self.assertEqual(manager.window_safety_blocked_reason, "unsupported_hvac_mode:cool")
        self.assertEqual(manager.window_safety_state, "active_blocked")
        self.assertEqual(manager.hass.services.calls, [])

    def test_safety_deadline_is_scheduled_exactly_when_within_next_recheck(self) -> None:
        manager = self.make_manager(maximum_minutes=240)
        manager.runtime.windows_open_since = self.clock.current - timedelta(minutes=254, seconds=30)
        manager.runtime.windows_backoff_until = self.clock.current - timedelta(minutes=239, seconds=30)
        manager.runtime.windows_backoff_active = True

        manager._schedule_window_recalc_if_needed()

        self.assertEqual(manager.window_timer_kind, "safety_deadline")
        self.assertEqual(manager.window_timer_expected_at, self.clock.current + timedelta(seconds=30))

    async def test_safety_latches_until_valid_close_and_restore_delay(self) -> None:
        manager = self.make_manager(indoor=82.0)
        self.activate_backoff(manager)
        await manager.async_recalculate("service")
        self.set_indoor(manager, 70.0)
        self.set_window(manager, "off")

        await manager.async_recalculate("state_change:binary_sensor.windows")
        self.assertTrue(manager.runtime.windows_safety_override_active)
        self.assertEqual(manager.windows_protection_state, "restoring")

        self.clock.advance(seconds=15)
        await manager.async_recalculate("window_timer")
        self.assertFalse(manager.runtime.windows_safety_override_active)
        self.assertFalse(manager.runtime.windows_backoff_active)
        self.assertEqual(manager.runtime.windows_safety_activation_reason, "high_indoor_temperature")
        self.assertEqual(manager.runtime.windows_safety_cleared_at, self.clock.current)
        self.assertEqual(manager.runtime.windows_safety_clear_reason, "window_restore_completed")
        self.assertEqual(manager.runtime.active_profile, PROFILE_HOME)

    async def test_unavailable_window_sensor_cannot_clear_active_safety(self) -> None:
        manager = self.make_manager(indoor=82.0)
        self.activate_backoff(manager)
        await manager.async_recalculate("service")
        self.set_window(manager, "unavailable")
        self.set_indoor(manager, 70.0)

        await manager.async_recalculate("state_change:binary_sensor.windows")

        self.assertTrue(manager.runtime.windows_backoff_active)
        self.assertTrue(manager.runtime.windows_safety_override_active)
        self.assertIsNone(manager.runtime.windows_closed_since)

    async def test_sensor_recovery_to_closed_clears_safety_after_restore_delay(self) -> None:
        manager = self.make_manager(indoor=82.0)
        self.activate_backoff(manager)
        await manager.async_recalculate("service")
        self.set_window(manager, "unavailable")
        await manager.async_recalculate("state_change:binary_sensor.windows")
        self.clock.advance(hours=2)
        self.set_window(manager, "off")

        await manager.async_recalculate("state_change:binary_sensor.windows")
        self.assertTrue(manager.runtime.windows_safety_override_active)
        self.assertEqual(manager.runtime.windows_closed_since, self.clock.current)
        self.clock.advance(seconds=15)
        await manager.async_recalculate("window_timer")
        self.assertFalse(manager.runtime.windows_safety_override_active)

    async def test_active_recheck_recovers_missed_close_and_clears_safety(self) -> None:
        manager = self.make_manager(indoor=82.0)
        self.activate_backoff(manager)
        await manager.async_recalculate("service")
        self.set_window(manager, "off")  # No state-change event is delivered.

        self.clock.advance(seconds=60)
        await manager.async_recalculate("window_timer")

        self.assertTrue(manager.runtime.windows_safety_override_active)
        self.assertEqual(manager.windows_protection_state, "restoring")
        self.clock.advance(seconds=15)
        await manager.async_recalculate("window_timer")
        self.assertFalse(manager.runtime.windows_safety_override_active)

    async def test_restart_or_reload_preserves_latched_safety_state(self) -> None:
        manager = self.make_manager(indoor=70.0)
        manager.runtime = RuntimeState(
            windows_open_since=self.clock.current - timedelta(hours=8),
            windows_backoff_until=self.clock.current - timedelta(hours=7, minutes=45),
            windows_backoff_active=True,
            windows_safety_override_active=True,
            windows_safety_activated_at=self.clock.current - timedelta(hours=3),
            windows_safety_activation_reason="maximum_backoff_duration",
        )

        await manager.async_recalculate("startup")

        self.assertTrue(manager.runtime.windows_safety_override_active)
        self.assertEqual(manager.runtime.desired_hvac_mode, "heat_cool")
        self.assertEqual(manager.runtime.windows_safety_activated_at, self.clock.current - timedelta(hours=3))

    async def test_thermostat_unavailable_outranks_but_does_not_drop_due_safety(self) -> None:
        manager = self.make_manager(indoor=None, thermostat_state="unavailable")
        self.activate_backoff(manager, age_minutes=240)

        await manager.async_recalculate("service")

        self.assertTrue(manager.runtime.windows_safety_override_active)
        self.assertEqual(manager.runtime.status, STATUS_UNAVAILABLE)
        self.assertEqual(manager.window_safety_blocked_reason, "thermostat_unavailable")
        self.assertEqual(manager.hass.services.calls, [])

    async def test_override_lock_outranks_safety(self) -> None:
        manager = self.make_manager(indoor=82.0)
        self.activate_backoff(manager)
        manager.hass.states.states["input_boolean.override"] = "on"

        await manager.async_recalculate("service")

        self.assertTrue(manager.runtime.windows_safety_override_active)
        self.assertEqual(manager.runtime.active_profile, PROFILE_OVERRIDE_LOCK)
        self.assertEqual(manager.window_safety_blocked_reason, "override_lock")
        self.assertEqual(manager.hass.services.calls, [])

    async def test_paused_control_outranks_safety(self) -> None:
        manager = self.make_manager(indoor=82.0)
        self.activate_backoff(manager)
        manager.runtime.paused = True

        await manager.async_recalculate("service")

        self.assertTrue(manager.runtime.windows_safety_override_active)
        self.assertEqual(manager.window_safety_blocked_reason, "paused")
        self.assertEqual(manager.hass.services.calls, [])

    async def test_paused_control_outranks_thermostat_unavailable(self) -> None:
        manager = self.make_manager(indoor=None, thermostat_state="unavailable")
        self.activate_backoff(manager, age_minutes=240)
        manager.runtime.paused = True

        await manager.async_recalculate("service")

        self.assertTrue(manager.runtime.windows_safety_override_active)
        self.assertEqual(manager.runtime.active_profile, "paused")
        self.assertEqual(manager.runtime.status, "paused")
        self.assertEqual(manager.window_safety_blocked_reason, "paused")

    async def test_safety_suspends_manual_override_then_restores_it(self) -> None:
        manager = self.make_manager(indoor=82.0, cancel_override_on_windows=False)
        self.activate_backoff(manager)
        manager.runtime.manual_override_active = True
        manager.runtime.manual_hold = True

        await manager.async_recalculate("service")
        self.assertEqual(manager.runtime.active_profile, PROFILE_SENSORS_OPEN)
        self.assertTrue(manager.runtime.manual_override_active)

        self.set_window(manager, "off")
        await manager.async_recalculate("state_change:binary_sensor.windows")
        self.clock.advance(seconds=15)
        await manager.async_recalculate("window_timer")

        self.assertEqual(manager.runtime.active_profile, PROFILE_MANUAL_OVERRIDE)
        self.assertTrue(manager.runtime.manual_override_active)

    async def test_each_occupancy_profile_is_recalculated_after_safety_ends(self) -> None:
        scenarios = (
            ({}, PROFILE_HOME),
            ({"input_boolean.away": "on"}, PROFILE_AWAY),
            ({"input_boolean.guest": "on"}, PROFILE_GUEST),
            ({"schedule.sleep": "on"}, PROFILE_SLEEP),
            (
                {"input_boolean.away": "on", "input_boolean.pre_arrival": "on"},
                PROFILE_PRE_ARRIVAL,
            ),
        )
        for states, expected in scenarios:
            with self.subTest(profile=expected):
                manager = self.make_manager(indoor=82.0)
                self.activate_backoff(manager)
                manager.hass.states.states.update(states)
                await manager.async_recalculate("service")
                self.assertEqual(manager.underlying_occupancy_profile, expected)
                self.set_window(manager, "off")
                await manager.async_recalculate("state_change:binary_sensor.windows")
                self.clock.advance(seconds=15)
                await manager.async_recalculate("window_timer")
                self.assertEqual(manager.runtime.active_profile, expected)
                self.clock.advance(seconds=-15)

    async def test_safety_temporarily_overrides_every_stored_hvac_preference(self) -> None:
        for preference in (HVAC_PREF_AUTO, HVAC_PREF_HEAT, HVAC_PREF_COOL, HVAC_PREF_OFF):
            with self.subTest(preference=preference):
                manager = self.make_manager(indoor=82.0, preference=preference)
                self.activate_backoff(manager)
                await manager.async_recalculate("service")
                self.assertEqual(manager.runtime.desired_hvac_mode, HVAC_PREF_COOL)
                self.assertEqual(manager.config.hvac_preference, preference)

    async def test_delayed_thermostat_echo_does_not_create_manual_override(self) -> None:
        manager = self.make_manager(indoor=70.0, maximum_minutes=240)
        self.activate_backoff(manager, age_minutes=240)
        await manager.async_recalculate("service")
        thermostat = manager.hass.states.states["climate.test"]
        thermostat.state = "heat_cool"
        thermostat.attributes.update(
            {"temperature": None, "target_temp_low": 52.0, "target_temp_high": 78.0}
        )
        self.clock.advance(seconds=5)

        await manager.async_recalculate("state_change:climate.test")

        self.assertFalse(manager.runtime.manual_override_active)
        self.assertEqual(manager.runtime.active_profile, PROFILE_SENSORS_OPEN)

    async def test_manual_change_during_safety_cannot_displace_safety(self) -> None:
        manager = self.make_manager(indoor=82.0, cancel_override_on_windows=False)
        self.activate_backoff(manager)
        await manager.async_recalculate("service")
        manager.runtime.manual_override_active = True
        manager.runtime.manual_hold = True

        await manager.async_recalculate("service")

        self.assertTrue(manager.runtime.manual_override_active)
        self.assertTrue(manager.runtime.windows_safety_override_active)
        self.assertEqual(manager.runtime.active_profile, PROFILE_SENSORS_OPEN)

    async def test_invalid_envelope_never_activates(self) -> None:
        manager = self.make_manager(indoor=90.0, minimum=70.0, maximum=72.0, hysteresis=2.0)
        self.activate_backoff(manager, age_minutes=300)

        await manager.async_recalculate("service")

        self.assertFalse(manager.window_safety_configuration_valid)
        self.assertFalse(manager.runtime.windows_safety_override_active)
        self.assertEqual(manager.window_safety_state, "misconfigured")
        self.assertEqual(manager.runtime.desired_hvac_mode, HVAC_PREF_OFF)


if __name__ == "__main__":
    unittest.main()
