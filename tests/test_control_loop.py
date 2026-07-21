"""Control-loop and Ecobee-facing regression tests."""
from __future__ import annotations

import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant_stubs import install_homeassistant_stubs, install_package_stub


install_homeassistant_stubs()
install_package_stub()

from custom_components.climate_manager.const import (  # noqa: E402
    DATA_MANAGER,
    DOMAIN,
    PROFILE_HOME,
    STATUS_CONTROLLING,
)
from custom_components.climate_manager.diagnostics import (  # noqa: E402
    async_get_config_entry_diagnostics,
)
from custom_components.climate_manager.manager import ClimateManager  # noqa: E402
from custom_components.climate_manager.models import ManagerConfig, ThermostatSnapshot  # noqa: E402


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
        self.calls = []

    async def async_call(self, domain, service, data, blocking=True):
        self.calls.append((domain, service, data, blocking))


class ControlLoopTests(unittest.IsolatedAsyncioTestCase):
    def make_manager(self, thermostat: SimpleNamespace) -> ClimateManager:
        states = FakeStates(
            {
                "climate.test": thermostat,
                "sensor.outdoor": "80",
                "sensor.season": "summer",
            }
        )
        hass = SimpleNamespace(
            states=states,
            services=FakeServices(),
            async_create_task=asyncio.create_task,
        )
        manager = ClimateManager(
            hass,
            "entry",
            ManagerConfig(
                "climate.test",
                outdoor_temp_entity="sensor.outdoor",
                season_entity="sensor.season",
            ),
        )
        manager._schedule_save = lambda: None
        manager._schedule_window_recalc_if_needed = lambda: None
        manager._schedule_override_recalc_if_needed = lambda: None
        return manager

    async def test_current_temperature_attribute_event_triggers_recalculation(self) -> None:
        manager = self.make_manager(
            SimpleNamespace(
                state="cool",
                attributes={"temperature": 69.0, "current_temperature": 79.0},
            )
        )
        manager.async_recalculate = AsyncMock()
        event = SimpleNamespace(
            data={
                "entity_id": "climate.test",
                "old_state": SimpleNamespace(state="cool"),
                "new_state": SimpleNamespace(state="cool"),
            }
        )

        manager._handle_state_change(event)
        await asyncio.sleep(0)

        manager.async_recalculate.assert_awaited_once_with("state_change:climate.test")

    async def test_idle_above_accepted_cooling_target_is_diagnosed_without_write_loop(self) -> None:
        manager = self.make_manager(
            SimpleNamespace(
                state="cool",
                attributes={
                    "temperature": 69.0,
                    "current_temperature": 80.0,
                    "hvac_action": "idle",
                },
            )
        )

        await manager.async_recalculate("service")

        self.assertEqual(manager.runtime.status, STATUS_CONTROLLING)
        self.assertEqual(manager.runtime.target_cool, 69.0)
        self.assertTrue(manager.above_cooling_target_while_idle)
        self.assertEqual(manager.hass.services.calls, [])

    async def test_mode_change_does_not_suppress_temperature_command_from_same_pass(self) -> None:
        manager = self.make_manager(
            SimpleNamespace(
                state="heat",
                attributes={"temperature": 70.0, "current_temperature": 75.0},
            )
        )
        manager.runtime.active_profile = PROFILE_HOME
        manager.runtime.desired_hvac_mode = "cool"
        manager.runtime.target_cool = 69.0

        await manager._apply_if_needed(
            ThermostatSnapshot("heat", 70.0, None, None, 75.0, True)
        )

        self.assertEqual(
            [(call[1], call[2]) for call in manager.hass.services.calls],
            [
                ("set_hvac_mode", {"entity_id": "climate.test", "hvac_mode": "cool"}),
                ("set_temperature", {"entity_id": "climate.test", "temperature": 69.0}),
            ],
        )

    def test_delayed_thermostat_echo_within_grace_does_not_create_manual_override(self) -> None:
        manager = self.make_manager(
            SimpleNamespace(
                state="cool",
                attributes={"temperature": 70.0, "current_temperature": 75.0},
            )
        )
        command_time = datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc)
        manager._last_command_time = command_time
        manager._last_command_snapshot = {
            "hvac_mode": "cool",
            "temperature": 69.0,
            "target_temp_low": None,
            "target_temp_high": None,
        }

        with patch(
            "custom_components.climate_manager.manager.now",
            return_value=command_time + timedelta(seconds=5),
        ):
            manager._detect_manual_change(
                "state_change:climate.test",
                ThermostatSnapshot("cool", 70.0, None, None, 75.0, True),
            )

        self.assertFalse(manager.runtime.manual_override_active)

    def test_real_manual_change_after_grace_still_creates_override(self) -> None:
        manager = self.make_manager(
            SimpleNamespace(
                state="cool",
                attributes={"temperature": 72.0, "current_temperature": 75.0},
            )
        )
        command_time = datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc)
        manager._last_command_time = command_time
        manager._last_command_snapshot = {
            "hvac_mode": "cool",
            "temperature": 69.0,
            "target_temp_low": None,
            "target_temp_high": None,
        }

        with patch(
            "custom_components.climate_manager.manager.now",
            return_value=command_time + timedelta(seconds=30),
        ):
            manager._detect_manual_change(
                "state_change:climate.test",
                ThermostatSnapshot("cool", 72.0, None, None, 75.0, True),
            )

        self.assertTrue(manager.runtime.manual_override_active)

    async def test_support_diagnostics_separate_calculated_commanded_and_reported_state(self) -> None:
        manager = self.make_manager(
            SimpleNamespace(
                state="cool",
                attributes={
                    "temperature": 69.0,
                    "current_temperature": 80.0,
                    "hvac_action": "idle",
                },
            )
        )
        await manager.async_recalculate("service")
        manager.hass.data = {DOMAIN: {"entry": {DATA_MANAGER: manager}}}
        entry = SimpleNamespace(
            entry_id="entry",
            data={"thermostat_entity": "climate.test"},
            options={},
        )

        result = await async_get_config_entry_diagnostics(manager.hass, entry)

        self.assertEqual(result["hvac"]["calculated_target_cool"], 69.0)
        self.assertEqual(result["hvac"]["thermostat_reported_target"], 69.0)
        self.assertEqual(result["hvac"]["thermostat_current_temperature"], 80.0)
        self.assertTrue(result["hvac"]["above_cooling_target_while_idle"])
        self.assertIn("protection_state", result["windows"])
        self.assertIn("safety", result["windows"])
        self.assertFalse(result["windows"]["safety"]["enabled"])
        self.assertEqual(result["windows"]["safety"]["state"], "disabled")
        self.assertIn("underlying_occupancy_profile", result["windows"]["safety"])
        self.assertIn("blocked_reason", result["pre_arrival"])


if __name__ == "__main__":
    unittest.main()
