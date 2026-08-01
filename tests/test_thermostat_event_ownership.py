"""End-to-end regression tests for thermostat event ownership."""
from __future__ import annotations

import asyncio
from dataclasses import asdict
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from homeassistant_stubs import install_homeassistant_stubs, install_package_stub


install_homeassistant_stubs()
install_package_stub()

from custom_components.climate_manager.const import (  # noqa: E402
    PROFILE_MANUAL_OVERRIDE,
    PROFILE_SENSORS_OPEN,
)
from custom_components.climate_manager.manager import ClimateManager  # noqa: E402
from custom_components.climate_manager.models import ManagerConfig, RuntimeState  # noqa: E402
from custom_components.climate_manager.restore import RuntimeStore  # noqa: E402


class FakeStates:
    def __init__(self, states: dict[str, object]) -> None:
        self.states = states

    def get(self, entity_id):
        value = self.states.get(entity_id)
        if value is None or hasattr(value, "state"):
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


class ThermostatEventOwnershipTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.clock = Clock()
        self.now_patch = patch(
            "custom_components.climate_manager.manager.now",
            side_effect=lambda: self.clock.current,
        )
        self.now_patch.start()

    def tearDown(self) -> None:
        self.now_patch.stop()

    def thermostat_state(
        self,
        mode: str,
        temperature: float | None,
        *,
        current_temperature: float = 70.0,
        updated_at: datetime | None = None,
    ) -> SimpleNamespace:
        attributes = {"current_temperature": current_temperature}
        if temperature is not None:
            attributes["temperature"] = temperature
        return SimpleNamespace(
            state=mode,
            attributes=attributes,
            last_updated=updated_at or self.clock.current,
        )

    def make_manager(
        self,
        *,
        mode: str = "cool",
        temperature: float | None = 70.0,
        window_state: str = "off",
        safety_enabled: bool = False,
        indoor: float = 70.0,
    ) -> ClimateManager:
        states = FakeStates(
            {
                "climate.test": self.thermostat_state(
                    mode,
                    temperature,
                    current_temperature=indoor,
                ),
                "binary_sensor.windows": window_state,
                "sensor.outdoor": "80",
                "sensor.season": "summer",
                "input_boolean.away": "off",
                "input_boolean.guest": "off",
                "input_boolean.override": "off",
                "input_boolean.pre_arrival": "off",
                "schedule.sleep": "off",
            }
        )
        tasks: list[asyncio.Task] = []

        def create_task(coro):
            task = asyncio.create_task(coro)
            tasks.append(task)
            return task

        hass = SimpleNamespace(
            states=states,
            services=FakeServices(),
            async_create_task=create_task,
        )
        manager = ClimateManager(
            hass,
            "entry",
            ManagerConfig(
                "climate.test",
                outdoor_temp_entity="sensor.outdoor",
                away_entity="input_boolean.away",
                guest_entity="input_boolean.guest",
                override_entity="input_boolean.override",
                pre_arrival_entity="input_boolean.pre_arrival",
                sleep_schedule_entity="schedule.sleep",
                windows_entity="binary_sensor.windows",
                season_entity="sensor.season",
                windows_open_delay_minutes=15,
                windows_restore_delay_minutes=15,
                windows_action="off",
                windows_safety_override_enabled=safety_enabled,
                windows_safety_maximum_backoff_minutes=240,
                windows_safety_min_indoor_temperature=50.0,
                windows_safety_max_indoor_temperature=80.0,
                windows_safety_hysteresis=2.0,
            ),
        )
        manager._schedule_save = lambda: None
        manager._schedule_window_recalc_if_needed = lambda: None
        manager._schedule_override_recalc_if_needed = lambda: None
        manager._test_tasks = tasks
        return manager

    async def emit_thermostat_event(
        self,
        manager: ClimateManager,
        *,
        old_mode: str,
        old_temperature: float | None,
        new_mode: str,
        new_temperature: float | None,
        event_time: datetime | None = None,
        current_temperature: float = 70.0,
        old_current_temperature: float | None = None,
        new_current_temperature: float | None = None,
    ) -> None:
        fired_at = event_time or self.clock.current
        old_state = self.thermostat_state(
            old_mode,
            old_temperature,
            current_temperature=(
                current_temperature
                if old_current_temperature is None
                else old_current_temperature
            ),
            updated_at=fired_at,
        )
        new_state = self.thermostat_state(
            new_mode,
            new_temperature,
            current_temperature=(
                current_temperature
                if new_current_temperature is None
                else new_current_temperature
            ),
            updated_at=fired_at,
        )
        manager.hass.states.states["climate.test"] = new_state
        event = SimpleNamespace(
            time_fired=fired_at,
            data={
                "entity_id": "climate.test",
                "old_state": old_state,
                "new_state": new_state,
            },
        )
        before = len(manager._test_tasks)
        manager._handle_state_change(event)
        await asyncio.gather(*manager._test_tasks[before:])

    def activate_backoff(
        self,
        manager: ClimateManager,
        *,
        activated_at: datetime | None = None,
    ) -> None:
        activation_time = activated_at or self.clock.current
        manager.runtime.windows_open_since = activation_time - timedelta(minutes=15)
        manager.runtime.windows_backoff_until = activation_time
        manager.runtime.windows_backoff_activated_at = activation_time
        manager.runtime.windows_backoff_active = True

    async def test_exact_live_backoff_off_to_cool_target_68_is_user_owned(self) -> None:
        manager = self.make_manager(mode="off", temperature=None, window_state="on")
        self.activate_backoff(manager, activated_at=self.clock.current - timedelta(minutes=1))
        manager._register_pending_thermostat_command(
            "window_off",
            {"hvac_mode": "off"},
            issued_at=self.clock.current - timedelta(seconds=2),
        )

        await self.emit_thermostat_event(
            manager,
            old_mode="off",
            old_temperature=None,
            new_mode="cool",
            new_temperature=68.0,
        )

        self.assertTrue(manager.runtime.manual_override_active)
        self.assertEqual(manager.runtime.manual_override_started_at, self.clock.current)
        self.assertEqual(manager.runtime.active_profile, PROFILE_MANUAL_OVERRIDE)
        self.assertEqual(manager.hass.services.calls, [])

    async def test_hvac_mode_only_user_change_is_manual(self) -> None:
        manager = self.make_manager(mode="off", temperature=68.0)
        manager._register_pending_thermostat_command(
            "off",
            {"hvac_mode": "off"},
            issued_at=self.clock.current - timedelta(seconds=1),
        )

        await self.emit_thermostat_event(
            manager,
            old_mode="off",
            old_temperature=68.0,
            new_mode="cool",
            new_temperature=68.0,
        )

        self.assertTrue(manager.runtime.manual_override_active)

    async def test_target_only_change_from_none_is_manual(self) -> None:
        manager = self.make_manager(mode="off", temperature=None)
        manager._register_pending_thermostat_command(
            "different_target",
            {"temperature": 68.0},
            issued_at=self.clock.current - timedelta(seconds=1),
        )

        await self.emit_thermostat_event(
            manager,
            old_mode="off",
            old_temperature=None,
            new_mode="off",
            new_temperature=67.0,
        )

        self.assertTrue(manager.runtime.manual_override_active)

    async def test_target_changed_away_from_last_command_is_manual(self) -> None:
        manager = self.make_manager(temperature=68.0)
        await manager._async_set_temperature(temperature=68.0)

        await self.emit_thermostat_event(
            manager,
            old_mode="cool",
            old_temperature=68.0,
            new_mode="cool",
            new_temperature=72.0,
        )

        self.assertTrue(manager.runtime.manual_override_active)

    async def test_target_changed_toward_last_command_is_manual(self) -> None:
        manager = self.make_manager(temperature=75.0)
        await manager._async_set_temperature(temperature=68.0)

        await self.emit_thermostat_event(
            manager,
            old_mode="cool",
            old_temperature=75.0,
            new_mode="cool",
            new_temperature=70.0,
        )

        self.assertTrue(manager.runtime.manual_override_active)

    async def test_near_but_not_exact_pending_target_is_manual(self) -> None:
        manager = self.make_manager(temperature=69.0)
        await manager._async_set_temperature(temperature=68.0)

        await self.emit_thermostat_event(
            manager,
            old_mode="cool",
            old_temperature=69.0,
            new_mode="cool",
            new_temperature=68.4,
        )

        self.assertTrue(manager.runtime.manual_override_active)

    async def test_exact_window_off_mode_echo_is_consumed(self) -> None:
        manager = self.make_manager(
            mode="cool",
            temperature=68.0,
            window_state="on",
        )
        self.activate_backoff(manager, activated_at=self.clock.current - timedelta(minutes=1))
        await manager._async_set_hvac_mode("off")

        await self.emit_thermostat_event(
            manager,
            old_mode="cool",
            old_temperature=68.0,
            new_mode="off",
            new_temperature=68.0,
        )

        self.assertFalse(manager.runtime.manual_override_active)
        self.assertEqual(manager.runtime.active_profile, PROFILE_SENSORS_OPEN)
        self.assertEqual(manager._pending_thermostat_commands, [])

    async def test_window_off_echo_that_clears_target_is_consumed(self) -> None:
        manager = self.make_manager(
            mode="cool",
            temperature=68.0,
            window_state="on",
        )
        self.activate_backoff(
            manager,
            activated_at=self.clock.current - timedelta(minutes=1),
        )
        await manager._async_set_hvac_mode("off")

        await self.emit_thermostat_event(
            manager,
            old_mode="cool",
            old_temperature=68.0,
            new_mode="off",
            new_temperature=None,
        )

        self.assertFalse(manager.runtime.manual_override_active)
        self.assertEqual(manager.runtime.active_profile, PROFILE_SENSORS_OPEN)
        self.assertEqual(manager._pending_thermostat_commands, [])

    async def test_user_off_change_that_clears_target_is_manual(self) -> None:
        manager = self.make_manager(mode="cool", temperature=68.0)

        await self.emit_thermostat_event(
            manager,
            old_mode="cool",
            old_temperature=68.0,
            new_mode="off",
            new_temperature=None,
        )

        self.assertTrue(manager.runtime.manual_override_active)
        self.assertEqual(manager.runtime.active_profile, PROFILE_MANUAL_OVERRIDE)

    async def test_exact_target_echo_is_consumed(self) -> None:
        manager = self.make_manager(mode="cool", temperature=None)
        manager.hass.states.states["input_boolean.override"] = "on"
        await manager._async_set_temperature(temperature=68.0)

        await self.emit_thermostat_event(
            manager,
            old_mode="cool",
            old_temperature=None,
            new_mode="cool",
            new_temperature=68.0,
        )

        self.assertFalse(manager.runtime.manual_override_active)
        self.assertEqual(manager._pending_thermostat_commands, [])

    async def test_combined_mode_and_target_echo_consumes_both_commands(self) -> None:
        manager = self.make_manager(mode="heat", temperature=70.0)
        manager.hass.states.states["input_boolean.override"] = "on"
        await manager._async_set_hvac_mode("cool")
        await manager._async_set_temperature(temperature=68.0)

        await self.emit_thermostat_event(
            manager,
            old_mode="heat",
            old_temperature=70.0,
            new_mode="cool",
            new_temperature=68.0,
        )

        self.assertFalse(manager.runtime.manual_override_active)
        self.assertEqual(manager._pending_thermostat_commands, [])

    async def test_multiple_rapid_user_adjustments_refresh_override(self) -> None:
        manager = self.make_manager(mode="off", temperature=None)
        await self.emit_thermostat_event(
            manager,
            old_mode="off",
            old_temperature=None,
            new_mode="cool",
            new_temperature=68.0,
        )
        first_started_at = manager.runtime.manual_override_started_at
        self.clock.advance(seconds=1)

        await self.emit_thermostat_event(
            manager,
            old_mode="cool",
            old_temperature=68.0,
            new_mode="cool",
            new_temperature=67.0,
        )

        self.assertTrue(manager.runtime.manual_override_active)
        self.assertGreater(manager.runtime.manual_override_started_at, first_started_at)
        self.assertEqual(
            manager.runtime.manual_override_until,
            self.clock.current + timedelta(minutes=120),
        )

    async def test_stale_out_of_order_event_cannot_replace_newer_user_state(self) -> None:
        manager = self.make_manager(mode="cool", temperature=68.0)
        newer_time = self.clock.current
        await self.emit_thermostat_event(
            manager,
            old_mode="cool",
            old_temperature=68.0,
            new_mode="cool",
            new_temperature=67.0,
            event_time=newer_time,
        )
        self.clock.advance(seconds=1)

        await self.emit_thermostat_event(
            manager,
            old_mode="cool",
            old_temperature=70.0,
            new_mode="cool",
            new_temperature=69.0,
            event_time=newer_time - timedelta(seconds=1),
        )

        self.assertEqual(manager.runtime.manual_override_started_at, newer_time)
        self.assertEqual(
            manager._active_manual_override_snapshot["temperature"],
            67.0,
        )

    async def test_event_before_backoff_activation_cannot_override_window_policy(self) -> None:
        manager = self.make_manager(mode="off", temperature=68.0, window_state="on")
        self.activate_backoff(manager)

        await self.emit_thermostat_event(
            manager,
            old_mode="cool",
            old_temperature=68.0,
            new_mode="off",
            new_temperature=68.0,
            event_time=self.clock.current - timedelta(seconds=1),
        )

        self.assertFalse(manager.runtime.manual_override_active)
        self.assertEqual(manager.runtime.active_profile, PROFILE_SENSORS_OPEN)

    async def test_expired_command_cannot_claim_later_matching_event(self) -> None:
        manager = self.make_manager(mode="cool", temperature=None)
        await manager._async_set_temperature(temperature=68.0)
        self.clock.advance(seconds=21)

        await self.emit_thermostat_event(
            manager,
            old_mode="cool",
            old_temperature=None,
            new_mode="cool",
            new_temperature=68.0,
        )

        self.assertTrue(manager.runtime.manual_override_active)
        self.assertEqual(manager._pending_thermostat_commands, [])

    async def test_window_close_retains_user_override(self) -> None:
        manager = self.make_manager(mode="off", temperature=None, window_state="on")
        self.activate_backoff(manager, activated_at=self.clock.current - timedelta(minutes=1))
        await self.emit_thermostat_event(
            manager,
            old_mode="off",
            old_temperature=None,
            new_mode="cool",
            new_temperature=68.0,
        )
        manager.hass.states.states["binary_sensor.windows"] = "off"

        await manager.async_recalculate("state_change:binary_sensor.windows")
        self.clock.advance(seconds=15)
        await manager.async_recalculate("window_timer")

        self.assertFalse(manager.runtime.windows_backoff_active)
        self.assertTrue(manager.runtime.manual_override_active)
        self.assertEqual(manager.runtime.active_profile, PROFILE_MANUAL_OVERRIDE)

    async def test_window_remains_open_for_twelve_hours_without_false_override(self) -> None:
        manager = self.make_manager(
            mode="cool",
            temperature=68.0,
            window_state="on",
            indoor=70.0,
        )
        await manager.async_recalculate("state_change:binary_sensor.windows")
        self.clock.advance(minutes=15)
        await manager.async_recalculate("window_timer")
        await self.emit_thermostat_event(
            manager,
            old_mode="cool",
            old_temperature=68.0,
            new_mode="off",
            new_temperature=68.0,
            current_temperature=70.0,
        )
        self.clock.advance(hours=11, minutes=45)

        await self.emit_thermostat_event(
            manager,
            old_mode="off",
            old_temperature=68.0,
            new_mode="off",
            new_temperature=68.0,
            old_current_temperature=70.0,
            new_current_temperature=80.0,
        )

        self.assertFalse(manager.runtime.manual_override_active)
        self.assertTrue(manager.runtime.windows_backoff_active)
        self.assertEqual(manager.runtime.active_profile, PROFILE_SENSORS_OPEN)
        self.assertEqual(manager.runtime.desired_hvac_mode, "off")

    async def test_save_load_and_restart_preserve_override_ownership(self) -> None:
        manager = self.make_manager(mode="off", temperature=None, window_state="on")
        activation_time = self.clock.current - timedelta(minutes=1)
        self.activate_backoff(manager, activated_at=activation_time)
        await self.emit_thermostat_event(
            manager,
            old_mode="off",
            old_temperature=None,
            new_mode="cool",
            new_temperature=68.0,
        )
        await manager._runtime_store.async_save(manager.runtime)

        restarted = self.make_manager(
            mode="cool",
            temperature=68.0,
            window_state="on",
        )
        restarted._runtime_store._store.data = manager._runtime_store._store.data
        restarted._runtime_store._ownership_store.data = (
            manager._runtime_store._ownership_store.data
        )
        restarted.runtime = await restarted._runtime_store.async_load()
        await restarted.async_recalculate("startup")

        self.assertEqual(
            restarted.runtime.manual_override_started_at,
            self.clock.current,
        )
        self.assertEqual(
            restarted.runtime.windows_backoff_activated_at,
            activation_time,
        )
        self.assertTrue(restarted.runtime.manual_override_active)
        self.assertEqual(restarted.runtime.active_profile, PROFILE_MANUAL_OVERRIDE)

    async def test_older_state_without_override_timestamp_loads(self) -> None:
        store = RuntimeStore(SimpleNamespace(), "older")
        older_state = asdict(
            RuntimeState(
                manual_override_active=True,
                manual_override_until=self.clock.current + timedelta(minutes=30),
            )
        )
        older_state.pop("manual_override_started_at")
        for key, value in list(older_state.items()):
            if isinstance(value, datetime):
                older_state[key] = value.isoformat()
        store._store.data = older_state

        loaded = await store.async_load()

        self.assertTrue(loaded.manual_override_active)
        self.assertIsNone(loaded.manual_override_started_at)

    async def test_primary_runtime_payload_remains_readable_by_older_version(self) -> None:
        store = RuntimeStore(SimpleNamespace(), "downgrade")
        runtime = RuntimeState(
            manual_override_active=True,
            manual_override_started_at=self.clock.current,
            manual_override_until=self.clock.current + timedelta(minutes=30),
        )

        await store.async_save(runtime)

        self.assertNotIn("manual_override_started_at", store._store.data)
        self.assertNotIn("windows_backoff_activated_at", store._store.data)
        self.assertEqual(
            store._ownership_store.data["manual_override_started_at"],
            self.clock.current.isoformat(),
        )

    async def test_stale_auxiliary_ownership_is_ignored_after_older_save(self) -> None:
        store = RuntimeStore(SimpleNamespace(), "round_trip_downgrade")
        runtime = RuntimeState(
            manual_override_active=True,
            manual_override_started_at=self.clock.current,
            manual_override_until=self.clock.current + timedelta(minutes=30),
        )
        await store.async_save(runtime)
        store._store.data["manual_hold"] = True

        loaded = await store.async_load()

        self.assertTrue(loaded.manual_override_active)
        self.assertTrue(loaded.manual_hold)
        self.assertIsNone(loaded.manual_override_started_at)

    async def test_safety_suspends_and_restores_event_created_override(self) -> None:
        manager = self.make_manager(
            mode="off",
            temperature=None,
            window_state="on",
            safety_enabled=True,
            indoor=70.0,
        )
        self.activate_backoff(manager, activated_at=self.clock.current - timedelta(minutes=1))
        await self.emit_thermostat_event(
            manager,
            old_mode="off",
            old_temperature=None,
            new_mode="cool",
            new_temperature=68.0,
            current_temperature=70.0,
        )
        self.assertEqual(manager.runtime.active_profile, PROFILE_MANUAL_OVERRIDE)

        self.clock.advance(seconds=1)
        await self.emit_thermostat_event(
            manager,
            old_mode="cool",
            old_temperature=68.0,
            new_mode="cool",
            new_temperature=68.0,
            old_current_temperature=70.0,
            new_current_temperature=82.0,
        )
        self.assertTrue(manager.runtime.windows_safety_override_active)
        self.assertEqual(manager.runtime.active_profile, PROFILE_SENSORS_OPEN)
        self.assertTrue(manager.runtime.manual_override_active)

        manager.hass.states.states["binary_sensor.windows"] = "off"
        await manager.async_recalculate("state_change:binary_sensor.windows")
        self.clock.advance(seconds=15)
        await manager.async_recalculate("window_timer")

        self.assertFalse(manager.runtime.windows_safety_override_active)
        self.assertTrue(manager.runtime.manual_override_active)
        self.assertEqual(manager.runtime.active_profile, PROFILE_MANUAL_OVERRIDE)


if __name__ == "__main__":
    unittest.main()
