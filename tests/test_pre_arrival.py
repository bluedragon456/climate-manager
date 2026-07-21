"""Tests for optional heading-home preconditioning."""
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
    PROFILE_HOME,
    PROFILE_MANUAL_OVERRIDE,
    PROFILE_OVERRIDE_LOCK,
    PROFILE_PAUSED,
    PROFILE_PRE_ARRIVAL,
    PROFILE_SENSORS_OPEN,
)
from custom_components.climate_manager.manager import ClimateManager  # noqa: E402
from custom_components.climate_manager.models import ManagerConfig  # noqa: E402


class FakeStates:
    def __init__(self, states: dict[str, str]) -> None:
        self.states = states

    def get(self, entity_id):
        value = self.states.get(entity_id)
        if value is None:
            return None
        return SimpleNamespace(state=value, attributes={})

    def is_state(self, entity_id, state) -> bool:
        current = self.get(entity_id)
        return current is not None and current.state == state


class PreArrivalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.current = datetime(2026, 7, 20, 18, 0, tzinfo=timezone.utc)
        self.now_patch = patch(
            "custom_components.climate_manager.manager.now",
            side_effect=lambda: self.current,
        )
        self.now_patch.start()

    def tearDown(self) -> None:
        self.now_patch.stop()

    def make_manager(
        self,
        *,
        away: str = "on",
        pre_arrival: str = "on",
        season: str = "summer",
        configured: bool = True,
    ) -> ClimateManager:
        states = {
            "input_boolean.away": away,
            "input_boolean.pre_arrival": pre_arrival,
            "input_boolean.override": "off",
            "input_boolean.guest": "off",
            "schedule.sleep": "off",
            "sensor.season": season,
            "sensor.outdoor": "80",
        }
        config = ManagerConfig(
            "climate.test",
            outdoor_temp_entity="sensor.outdoor",
            away_entity="input_boolean.away",
            guest_entity="input_boolean.guest",
            sleep_schedule_entity="schedule.sleep",
            override_entity="input_boolean.override",
            season_entity="sensor.season",
            pre_arrival_entity="input_boolean.pre_arrival" if configured else None,
        )
        return ClimateManager(SimpleNamespace(states=FakeStates(states)), "entry", config)

    def test_no_configured_entity_preserves_away_behavior(self) -> None:
        manager = self.make_manager(configured=False)

        self.assertEqual(manager._resolve_profile(), PROFILE_AWAY)
        self.assertEqual(manager.pre_arrival_blocked_reason, "not_configured")

    def test_away_plus_request_selects_pre_arrival_without_changing_away(self) -> None:
        manager = self.make_manager()

        self.assertEqual(manager._resolve_profile(), PROFILE_PRE_ARRIVAL)
        self.assertEqual(manager.hass.states.states["input_boolean.away"], "on")

    def test_summer_winter_and_transition_use_existing_season_logic(self) -> None:
        expectations = {
            "summer": "cool",
            "winter": "heat",
            "spring": "heat_cool",
            "fall": "heat_cool",
        }
        for season, expected in expectations.items():
            with self.subTest(season=season):
                manager = self.make_manager(season=season)
                self.assertEqual(
                    manager._resolve_desired_hvac_mode(PROFILE_PRE_ARRIVAL),
                    expected,
                )

    def test_pre_arrival_uses_home_comfort_target_and_curve_weight(self) -> None:
        manager = self.make_manager(season="spring")
        manager.config.home_comfort_target_override = True
        manager.config.home_comfort_target = 71.0
        manager.config.curve_weight_home = 0.0
        manager.config.cool_curve_weight_home = 0.0
        manager.runtime.outdoor_boost_state = "none"

        targets = manager._resolve_comfort_auto_targets(PROFILE_PRE_ARRIVAL, "heat_cool")

        self.assertEqual(manager.runtime.active_comfort_target, 71.0)
        self.assertEqual(targets, (68.0, 74.0))

    def test_request_turning_off_returns_to_away(self) -> None:
        manager = self.make_manager()
        manager.hass.states.states["input_boolean.pre_arrival"] = "off"

        self.assertEqual(manager._resolve_profile(), PROFILE_AWAY)
        self.assertEqual(manager.pre_arrival_blocked_reason, "inactive")

    def test_arrival_returns_to_home_without_mutating_request(self) -> None:
        manager = self.make_manager()
        manager.hass.states.states["input_boolean.away"] = "off"

        self.assertEqual(manager._resolve_profile(), PROFILE_HOME)
        self.assertEqual(manager.pre_arrival_blocked_reason, "not_away")
        self.assertEqual(manager.hass.states.states["input_boolean.pre_arrival"], "on")

    def test_windows_backoff_overrides_pre_arrival(self) -> None:
        manager = self.make_manager()
        manager.config.windows_entity = "binary_sensor.windows"
        manager.hass.states.states["binary_sensor.windows"] = "on"
        manager.runtime.windows_open_since = self.current - timedelta(minutes=20)
        manager.runtime.windows_backoff_until = self.current - timedelta(minutes=5)

        self.assertEqual(manager._resolve_profile(), PROFILE_SENSORS_OPEN)

    def test_pause_override_lock_and_manual_override_take_precedence(self) -> None:
        paused = self.make_manager()
        paused.runtime.paused = True
        self.assertEqual(paused._resolve_profile(), PROFILE_PAUSED)

        locked = self.make_manager()
        locked.hass.states.states["input_boolean.override"] = "on"
        self.assertEqual(locked._resolve_profile(), PROFILE_OVERRIDE_LOCK)

        manual = self.make_manager()
        manual.runtime.manual_override_active = True
        self.assertEqual(manual._resolve_profile(), PROFILE_MANUAL_OVERRIDE)

    def test_pre_arrival_outranks_guest_and_sleep_only_while_away(self) -> None:
        manager = self.make_manager()
        manager.hass.states.states["input_boolean.guest"] = "on"
        manager.hass.states.states["schedule.sleep"] = "on"

        self.assertEqual(manager._resolve_profile(), PROFILE_PRE_ARRIVAL)

    def test_unknown_and_unavailable_requests_are_inactive_and_diagnosable(self) -> None:
        for raw_state in ("unknown", "unavailable"):
            with self.subTest(raw_state=raw_state):
                manager = self.make_manager(pre_arrival=raw_state)
                self.assertEqual(manager._resolve_profile(), PROFILE_AWAY)
                self.assertEqual(manager.pre_arrival_blocked_reason, "entity_unavailable")


if __name__ == "__main__":
    unittest.main()
