"""Fall floor regression tests using the audited live configuration."""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from homeassistant_stubs import install_homeassistant_stubs, install_package_stub, install_voluptuous_stub

install_homeassistant_stubs()
install_package_stub()
install_voluptuous_stub()

from custom_components.climate_manager.manager import ClimateManager
from custom_components.climate_manager.models import ManagerConfig
from custom_components.climate_manager.config_flow import _normalize_options


class FallFloorTests(unittest.TestCase):
    def make_manager(self, **options):
        config = ManagerConfig(
            "climate.test", comfort_target=71, sleep_comfort_target=68,
            sleep_comfort_target_override=True, minimum_auto_gap=5,
            max_cool_target=75, occupied_cooling_ceiling_enabled=True,
            fall_comfort_floor_enabled=True, **options,
        )
        hass = SimpleNamespace(states=SimpleNamespace(get=lambda _: None))
        manager = ClimateManager(hass, "test", config)
        manager._current_season = lambda: "fall"
        manager._outdoor_temperature_f = lambda: 46.22
        manager.runtime.outdoor_boost_state = "cold"
        return manager

    def targets(self, manager, profile="home"):
        manager.runtime.active_profile = profile
        return manager._resolve_comfort_auto_targets(profile, "heat_cool")

    def test_live_home_configuration_preserves_71_floor_and_gap(self):
        manager = self.make_manager()
        self.assertEqual(self.targets(manager), (71.5, 76.5))
        self.assertEqual(manager.effective_cooling_limit, 76.5)
        self.assertEqual(manager.normalize_heat_cool_range(71.5, 76.5), (71.5, 76.5))

    def test_sleep_68_is_a_floor(self):
        manager = self.make_manager()
        low, high = self.targets(manager, "sleep")
        self.assertEqual(low, 68)
        self.assertGreaterEqual(high - low, 5)

    def test_targets_can_rise_above_both_floors(self):
        manager = self.make_manager(curve_weight_home=2, curve_weight_sleep=2)
        manager._outdoor_temperature_f = lambda: 0
        for profile, floor in (("home", 71), ("sleep", 68)):
            with self.subTest(profile=profile):
                low, high = self.targets(manager, profile)
                self.assertGreater(low, floor)
                self.assertGreaterEqual(high - low, 5)
                self.assertEqual(manager.normalize_heat_cool_range(low, high), (low, high))

    def test_warm_fall_does_not_lower_floor(self):
        manager = self.make_manager()
        manager._outdoor_temperature_f = lambda: 100
        manager.runtime.outdoor_boost_state = "hot"
        self.assertEqual(self.targets(manager), (71, 76))

    def test_disabled_and_other_seasons_preserve_legacy_ceiling(self):
        manager = self.make_manager()
        manager.config.fall_comfort_floor_enabled = False
        self.assertEqual(self.targets(manager), (67, 72))
        manager.config.fall_comfort_floor_enabled = True
        for season in ("spring", "summer", "winter", "unknown"):
            manager._current_season = lambda: season
            self.assertEqual(self.targets(manager), (67, 72))

    def test_excluded_profiles_and_explicit_preferences(self):
        manager = self.make_manager()
        for profile in ("away", "manual_override", "paused", "override_lock", "sensors_open"):
            self.assertEqual(manager._fall_comfort_limits(profile), (None, 75))
        for preference in ("heat", "cool", "off"):
            manager.config.hvac_preference = preference
            self.assertEqual(manager._fall_comfort_limits("home"), (None, 75))

    def test_away_and_window_safety_targets_unchanged(self):
        manager = self.make_manager()
        self.assertEqual(self.targets(manager, "away"), (62, 75))
        manager.config.smart_control_enabled = False
        self.assertEqual(manager._fall_comfort_limits("home"), (None, 75))

    def test_thermostat_maximum_wins_and_reports_limited_floor(self):
        manager = self.make_manager()
        manager.hass.states.get = lambda _: SimpleNamespace(attributes={"max_temp": 75})
        self.assertEqual(self.targets(manager), (70, 75))
        self.assertIn("fall_comfort_floor_safety_limited", manager.runtime.active_control_reason)

    def test_policy_sensor_survives_manual_and_door_blocking(self):
        manager = self.make_manager()
        manager.runtime.active_profile = "sensors_open"
        self.assertEqual(manager.effective_cooling_limit, 76.5)
        manager.runtime.active_profile = "manual_override"
        self.assertEqual(manager.effective_cooling_limit, 76.5)

    def test_existing_installations_stay_opt_in(self):
        self.assertFalse(_normalize_options({})["fall_comfort_floor_enabled"])
        self.assertTrue(_normalize_options({"fall_comfort_floor_enabled": True})["fall_comfort_floor_enabled"])


if __name__ == "__main__":
    unittest.main()
