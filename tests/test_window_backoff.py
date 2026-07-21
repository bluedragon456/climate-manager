"""Regression tests for the window/door protection lifecycle."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from homeassistant_stubs import install_homeassistant_stubs, install_package_stub


install_homeassistant_stubs()
install_package_stub()

from custom_components.climate_manager.const import (  # noqa: E402
    PROFILE_AWAY,
    PROFILE_MANUAL_OVERRIDE,
    PROFILE_SENSORS_OPEN,
    PROFILE_SLEEP,
    STATUS_UNAVAILABLE,
    WINDOWS_ACTION_COOL_SETBACK,
    WINDOWS_ACTION_HEAT_SETBACK,
    WINDOWS_ACTION_OFF,
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


class WindowBackoffTests(unittest.IsolatedAsyncioTestCase):
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
        window_state: str = "off",
        thermostat_state: str = "cool",
        windows_action: str = WINDOWS_ACTION_OFF,
        cancel_override_on_windows: bool = True,
    ) -> ClimateManager:
        states = {
            "binary_sensor.windows": window_state,
            "climate.test": SimpleNamespace(
                state=thermostat_state,
                attributes={"temperature": 70.0, "current_temperature": 70.0},
            ),
            "sensor.outdoor": "80",
            "sensor.season": "summer",
            "input_boolean.away": "off",
            "schedule.sleep": "off",
        }
        hass = SimpleNamespace(states=FakeStates(states), services=FakeServices())
        config = ManagerConfig(
            "climate.test",
            outdoor_temp_entity="sensor.outdoor",
            away_entity="input_boolean.away",
            sleep_schedule_entity="schedule.sleep",
            windows_entity="binary_sensor.windows",
            season_entity="sensor.season",
            windows_open_delay_minutes=15,
            windows_restore_delay_minutes=15,
            windows_action=windows_action,
            cancel_override_on_windows=cancel_override_on_windows,
        )
        manager = ClimateManager(hass, "entry", config)
        manager._schedule_save = lambda: None
        manager._schedule_override_recalc_if_needed = lambda: None
        return manager

    def set_window(self, manager: ClimateManager, state: str) -> None:
        manager.hass.states.states["binary_sensor.windows"] = state

    async def test_open_lifecycle_activates_at_deadline_without_another_event(self) -> None:
        manager = self.make_manager(window_state="on")

        await manager.async_recalculate("state_change:binary_sensor.windows")
        self.assertIsNotNone(manager.runtime.windows_open_since)
        self.assertFalse(manager.runtime.windows_backoff_active)

        self.clock.advance(minutes=15)
        await manager._async_window_timer_recalc()

        self.assertTrue(manager.runtime.windows_backoff_active)
        self.assertEqual(manager.runtime.active_profile, PROFILE_SENSORS_OPEN)
        self.assertEqual(manager.runtime.desired_hvac_mode, "off")

    async def test_thermostat_unavailable_does_not_prevent_open_timer_initialization(self) -> None:
        manager = self.make_manager(window_state="on", thermostat_state="unavailable")

        await manager.async_recalculate("state_change:binary_sensor.windows")

        self.assertEqual(manager.runtime.status, STATUS_UNAVAILABLE)
        self.assertEqual(manager.runtime.windows_open_since, self.clock.current)
        self.assertEqual(
            manager.runtime.windows_backoff_until,
            self.clock.current + timedelta(minutes=15),
        )

    def test_close_before_open_deadline_cannot_activate_stale_backoff(self) -> None:
        manager = self.make_manager(window_state="on")
        self.assertFalse(manager._windows_backoff_active())

        self.clock.advance(minutes=14, seconds=59)
        self.set_window(manager, "off")
        self.assertFalse(manager._windows_backoff_active())

        self.clock.advance(seconds=2)
        self.assertFalse(manager._windows_backoff_active())
        self.assertFalse(manager.runtime.windows_backoff_active)

    def test_repeated_open_updates_do_not_extend_original_deadline(self) -> None:
        manager = self.make_manager(window_state="on")
        self.assertFalse(manager._windows_backoff_active())
        original_open = manager.runtime.windows_open_since
        original_deadline = manager.runtime.windows_backoff_until

        self.clock.advance(minutes=5)
        self.assertFalse(manager._windows_backoff_active())

        self.assertEqual(manager.runtime.windows_open_since, original_open)
        self.assertEqual(manager.runtime.windows_backoff_until, original_deadline)

    def test_reopen_during_restore_cancels_restoration(self) -> None:
        manager = self.make_manager(window_state="on")
        manager._windows_backoff_active()
        self.clock.advance(minutes=15)
        manager.runtime.windows_backoff_active = manager._windows_backoff_active()

        self.set_window(manager, "off")
        self.assertTrue(manager._windows_backoff_active())
        closed_since = manager.runtime.windows_closed_since
        self.clock.advance(seconds=10)
        self.set_window(manager, "on")

        self.assertTrue(manager._windows_backoff_active())
        self.assertIsNone(manager.runtime.windows_closed_since)
        self.assertNotEqual(closed_since, manager.runtime.windows_closed_since)

    def test_unavailable_during_active_backoff_is_not_treated_as_closed(self) -> None:
        manager = self.make_manager(window_state="on")
        manager._windows_backoff_active()
        self.clock.advance(minutes=15)
        manager.runtime.windows_backoff_active = manager._windows_backoff_active()

        self.set_window(manager, "unavailable")
        self.clock.advance(hours=2)

        self.assertTrue(manager._windows_backoff_active())
        self.assertIsNone(manager.runtime.windows_closed_since)
        self.assertEqual(manager.runtime.windows_open_since, datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc))

    def test_unknown_during_pending_delay_preserves_original_open_period(self) -> None:
        manager = self.make_manager(window_state="on")
        manager._windows_backoff_active()
        original_open = manager.runtime.windows_open_since
        self.clock.advance(minutes=5)
        self.set_window(manager, "unknown")
        self.assertFalse(manager._windows_backoff_active())
        self.clock.advance(minutes=20)
        self.assertFalse(manager._windows_backoff_active())
        self.set_window(manager, "on")

        self.assertTrue(manager._windows_backoff_active())
        self.assertEqual(manager.runtime.windows_open_since, original_open)

    def test_reload_while_active_and_sensor_unavailable_keeps_backoff(self) -> None:
        manager = self.make_manager(window_state="unavailable")
        manager.runtime = RuntimeState(
            windows_open_since=self.clock.current - timedelta(hours=7),
            windows_backoff_until=self.clock.current - timedelta(hours=6, minutes=45),
            windows_backoff_active=True,
        )

        self.assertTrue(manager._windows_backoff_active())
        self.assertIsNone(manager.runtime.windows_closed_since)

    def test_restart_while_waiting_keeps_original_deadline(self) -> None:
        manager = self.make_manager(window_state="on")
        original_open = self.clock.current - timedelta(minutes=5)
        manager.runtime = RuntimeState(
            windows_open_since=original_open,
            windows_backoff_until=original_open + timedelta(minutes=15),
        )

        self.assertFalse(manager._windows_backoff_active())
        manager._schedule_window_recalc_if_needed()

        self.assertEqual(manager.runtime.windows_open_since, original_open)
        self.assertEqual(manager.window_timer_expected_at, original_open + timedelta(minutes=15))
        self.assertEqual(manager.window_timer_kind, "open_delay")

    def test_restart_during_restore_keeps_remaining_restore_delay(self) -> None:
        manager = self.make_manager(window_state="off")
        manager.runtime = RuntimeState(
            windows_open_since=self.clock.current - timedelta(hours=1),
            windows_backoff_until=self.clock.current - timedelta(minutes=45),
            windows_backoff_active=True,
            windows_closed_since=self.clock.current - timedelta(seconds=5),
        )

        self.assertTrue(manager._windows_backoff_active())
        manager._schedule_window_recalc_if_needed()
        self.assertEqual(
            manager.window_timer_expected_at,
            self.clock.current + timedelta(seconds=10),
        )
        self.clock.advance(seconds=10)
        self.assertFalse(manager._windows_backoff_active())

    def test_sensor_recovery_to_closed_starts_restore_from_recovery(self) -> None:
        manager = self.make_manager(window_state="on")
        manager._windows_backoff_active()
        self.clock.advance(minutes=15)
        manager.runtime.windows_backoff_active = manager._windows_backoff_active()
        self.set_window(manager, "unavailable")
        self.clock.advance(hours=2)
        self.assertTrue(manager._windows_backoff_active())

        self.set_window(manager, "off")
        self.assertTrue(manager._windows_backoff_active())
        self.assertEqual(manager.runtime.windows_closed_since, self.clock.current)
        self.clock.advance(seconds=15)
        self.assertFalse(manager._windows_backoff_active())

    async def test_stale_timer_callback_is_ignored_after_reschedule(self) -> None:
        manager = self.make_manager(window_state="on")
        await manager.async_recalculate("state_change:binary_sensor.windows")
        stale_generation = manager._window_timer_generation
        manager._schedule_window_recalc_if_needed()

        await manager._async_window_timer_recalc(stale_generation, "open_delay")

        self.assertEqual(manager.last_window_timer_reason, "ignored_stale:open_delay")
        self.assertTrue(manager.window_timer_scheduled)

    async def test_active_recheck_recovers_a_close_whose_event_was_missed(self) -> None:
        manager = self.make_manager(window_state="on", thermostat_state="off")
        manager.runtime.windows_open_since = self.clock.current - timedelta(minutes=20)
        manager.runtime.windows_backoff_until = self.clock.current - timedelta(minutes=5)
        manager.runtime.windows_backoff_active = True
        manager._schedule_window_recalc_if_needed()
        generation = manager._window_timer_generation

        self.assertEqual(manager.window_timer_kind, "active_recheck")
        self.set_window(manager, "off")  # State changed, but no state-change callback arrived.
        self.clock.advance(seconds=60)
        await manager._async_window_timer_recalc(generation, "active_recheck")

        self.assertTrue(manager.runtime.windows_backoff_active)
        self.assertEqual(manager.windows_protection_state, "restoring")
        self.assertEqual(manager.window_timer_kind, "restore_delay")

        restore_generation = manager._window_timer_generation
        self.clock.advance(seconds=15)
        await manager._async_window_timer_recalc(restore_generation, "restore_delay")
        self.assertFalse(manager.runtime.windows_backoff_active)

    async def test_window_diagnostics_expose_pending_active_and_unavailable_phases(self) -> None:
        manager = self.make_manager(window_state="on")
        await manager.async_recalculate("state_change:binary_sensor.windows")

        self.assertEqual(manager.windows_raw_state, "on")
        self.assertEqual(manager.windows_protection_state, "pending")
        self.assertTrue(manager.window_timer_scheduled)
        self.assertEqual(manager.window_timer_kind, "open_delay")

        self.clock.advance(minutes=15)
        await manager._async_window_timer_recalc()
        self.assertEqual(manager.windows_protection_state, "active")

        self.set_window(manager, "unavailable")
        self.assertTrue(manager._windows_backoff_active())
        self.assertEqual(manager.windows_protection_state, "active_sensor_unavailable")

    async def test_window_stays_open_for_twelve_hours_and_hvac_remains_off(self) -> None:
        manager = self.make_manager(window_state="on")
        await manager.async_recalculate("state_change:binary_sensor.windows")
        manager.hass.states.states["climate.test"].state = "off"
        self.clock.advance(hours=12)
        manager.hass.states.states["climate.test"].attributes["current_temperature"] = 80.0

        await manager.async_recalculate("state_change:climate.test")

        self.assertEqual(manager.runtime.active_profile, PROFILE_SENSORS_OPEN)
        self.assertTrue(manager.runtime.windows_backoff_active)
        self.assertEqual(manager.runtime.desired_hvac_mode, "off")
        self.assertEqual(manager._thermostat_snapshot().current_temperature, 80.0)

    def test_window_profile_outranks_away_and_sleep(self) -> None:
        manager = self.make_manager(window_state="on")
        manager.runtime.windows_open_since = self.clock.current - timedelta(minutes=20)
        manager.runtime.windows_backoff_until = self.clock.current - timedelta(minutes=5)
        manager.hass.states.states["input_boolean.away"] = "on"
        manager.hass.states.states["schedule.sleep"] = "on"

        self.assertEqual(manager._resolve_profile(), PROFILE_SENSORS_OPEN)

    async def test_manual_change_is_canceled_immediately_when_window_policy_requires_it(self) -> None:
        manager = self.make_manager(window_state="on")
        manager.runtime.windows_open_since = self.clock.current - timedelta(minutes=20)
        manager.runtime.windows_backoff_until = self.clock.current - timedelta(minutes=5)
        manager.runtime.windows_backoff_active = True
        manager._last_command_snapshot = {
            "hvac_mode": "off",
            "temperature": None,
            "target_temp_low": None,
            "target_temp_high": None,
        }
        manager._last_command_time = self.clock.current - timedelta(minutes=1)
        manager.hass.states.states["climate.test"].state = "cool"

        await manager.async_recalculate("state_change:climate.test")

        self.assertFalse(manager.runtime.manual_override_active)
        self.assertEqual(manager.runtime.active_profile, PROFILE_SENSORS_OPEN)

    async def test_manual_override_can_outrank_windows_when_cancel_option_is_disabled(self) -> None:
        manager = self.make_manager(
            window_state="on",
            cancel_override_on_windows=False,
        )
        manager.runtime.windows_open_since = self.clock.current - timedelta(minutes=20)
        manager.runtime.windows_backoff_until = self.clock.current - timedelta(minutes=5)
        manager.runtime.windows_backoff_active = True
        manager.runtime.manual_override_active = True
        manager.runtime.manual_hold = True

        await manager.async_recalculate("service")

        self.assertEqual(manager.runtime.active_profile, PROFILE_MANUAL_OVERRIDE)

    def test_window_actions_and_freeze_protection_are_explicit(self) -> None:
        heat = self.make_manager(window_state="on", windows_action=WINDOWS_ACTION_HEAT_SETBACK)
        cool = self.make_manager(window_state="on", windows_action=WINDOWS_ACTION_COOL_SETBACK)
        off = self.make_manager(window_state="on", windows_action=WINDOWS_ACTION_OFF)

        self.assertEqual(heat._resolve_desired_hvac_mode(PROFILE_SENSORS_OPEN), "heat")
        self.assertEqual(cool._resolve_desired_hvac_mode(PROFILE_SENSORS_OPEN), "cool")
        self.assertEqual(off._resolve_desired_hvac_mode(PROFILE_SENSORS_OPEN), "off")

        off.hass.states.states["sensor.season"] = "winter"
        off.hass.states.states["sensor.outdoor"] = "40"
        self.assertEqual(off._resolve_desired_hvac_mode(PROFILE_SENSORS_OPEN), "heat")

    def test_restore_delay_legacy_name_is_interpreted_as_seconds(self) -> None:
        manager = self.make_manager(window_state="on")
        manager._windows_backoff_active()
        self.clock.advance(minutes=15)
        manager.runtime.windows_backoff_active = manager._windows_backoff_active()
        self.set_window(manager, "off")

        self.assertTrue(manager._windows_backoff_active())
        self.clock.advance(seconds=14)
        self.assertTrue(manager._windows_backoff_active())
        self.clock.advance(seconds=1)
        self.assertFalse(manager._windows_backoff_active())


if __name__ == "__main__":
    unittest.main()
