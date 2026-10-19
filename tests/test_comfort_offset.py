"""Regression tests for comfort offset target resolution."""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from homeassistant_stubs import install_homeassistant_stubs, install_package_stub


install_homeassistant_stubs()
install_package_stub()

from custom_components.climate_manager.const import (  # noqa: E402
    HVAC_PREF_COOL,
    HVAC_PREF_HEAT,
    PROFILE_HOME,
    PROFILE_MANUAL_OVERRIDE,
    PROFILE_SLEEP,
    SEASON_SUMMER,
    SEASON_WINTER,
)
from custom_components.climate_manager.manager import (  # noqa: E402
    OUTDOOR_BOOST_COLD,
    OUTDOOR_BOOST_HOT,
    OUTDOOR_BOOST_NONE,
    ClimateManager,
)
from custom_components.climate_manager.models import ManagerConfig, ThermostatSnapshot  # noqa: E402


class FakeServices:
    def __init__(self) -> None:
        self.calls = []

    async def async_call(self, domain, service, data, blocking=True):
        self.calls.append((domain, service, data, blocking))


class ComfortOffsetTests(unittest.IsolatedAsyncioTestCase):
    def make_manager(self, *, outdoor: float, config: ManagerConfig | None = None) -> ClimateManager:
        manager = ClimateManager(SimpleNamespace(), "entry", config or ManagerConfig("climate.test"))
        manager._outdoor_temperature_f = lambda: outdoor
        return manager

    def test_zero_offset_keeps_base_transition_targets(self) -> None:
        manager = self.make_manager(outdoor=70.0)

        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, "heat_cool")

        self.assertEqual(manager.runtime.comfort_offset, 0.0)
        self.assertEqual(manager.runtime.active_comfort_target, 70.0)
        self.assertEqual((target_heat, target_cool), (67.0, 73.0))

    def test_positive_offset_updates_effective_transition_target(self) -> None:
        manager = self.make_manager(outdoor=60.0)

        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, "heat_cool")

        self.assertEqual(manager.runtime.comfort_offset, 1.0)
        self.assertEqual(manager.runtime.active_comfort_target, 71.0)
        self.assertEqual((target_heat, target_cool), (68.0, 74.0))

    def test_negative_offset_updates_effective_transition_target(self) -> None:
        manager = self.make_manager(outdoor=80.0)

        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, "heat_cool")

        self.assertEqual(manager.runtime.comfort_offset, -1.0)
        self.assertEqual(manager.runtime.active_comfort_target, 69.0)
        self.assertEqual((target_heat, target_cool), (66.0, 72.0))

    def test_cold_boost_only_increases_effective_comfort_target(self) -> None:
        manager = self.make_manager(outdoor=70.0)
        manager.runtime.outdoor_boost_state = OUTDOOR_BOOST_COLD

        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, "heat_cool")

        self.assertEqual(manager.runtime.comfort_offset, 1.0)
        self.assertEqual(manager.runtime.active_comfort_target, 71.0)
        self.assertEqual((target_heat, target_cool), (68.0, 74.0))

    def test_hot_boost_only_decreases_effective_comfort_target(self) -> None:
        manager = self.make_manager(outdoor=70.0)
        manager.runtime.outdoor_boost_state = OUTDOOR_BOOST_HOT

        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, "heat_cool")

        self.assertEqual(manager.runtime.comfort_offset, -1.0)
        self.assertEqual(manager.runtime.active_comfort_target, 69.0)
        self.assertEqual((target_heat, target_cool), (66.0, 72.0))

    def test_outdoor_curve_and_cold_boost_stack_before_transition_range(self) -> None:
        manager = self.make_manager(outdoor=55.0)
        manager.runtime.outdoor_boost_state = OUTDOOR_BOOST_COLD

        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, "heat_cool")

        self.assertEqual(manager.runtime.comfort_offset, 2.5)
        self.assertEqual(manager.runtime.active_comfort_target, 72.5)
        self.assertEqual((target_heat, target_cool), (69.5, 75.5))

    def test_outdoor_curve_and_hot_boost_stack_before_transition_range(self) -> None:
        manager = self.make_manager(outdoor=80.0)
        manager.runtime.outdoor_boost_state = OUTDOOR_BOOST_HOT

        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, "heat_cool")

        self.assertEqual(manager.runtime.comfort_offset, -2.0)
        self.assertEqual(manager.runtime.active_comfort_target, 68.0)
        self.assertEqual((target_heat, target_cool), (65.0, 71.0))

    def test_extreme_cold_caps_effective_comfort_before_transition_range(self) -> None:
        manager = self.make_manager(
            outdoor=35.0,
            config=ManagerConfig("climate.test", curve_weight_home=2.0),
        )
        manager.runtime.outdoor_boost_state = OUTDOOR_BOOST_COLD

        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, "heat_cool")

        self.assertEqual(manager.runtime.comfort_offset, 5.0)
        self.assertEqual(manager.runtime.active_comfort_target, 75.0)
        self.assertEqual((target_heat, target_cool), (72.0, 78.0))

    def test_extreme_hot_caps_effective_comfort_before_transition_range(self) -> None:
        manager = self.make_manager(outdoor=120.0)
        manager.runtime.outdoor_boost_state = OUTDOOR_BOOST_HOT

        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, "heat_cool")

        self.assertEqual(manager.runtime.comfort_offset, -2.0)
        self.assertEqual(manager.runtime.active_comfort_target, 68.0)
        self.assertEqual((target_heat, target_cool), (65.0, 71.0))

    def test_default_hot_boost_threshold_is_extreme_heat(self) -> None:
        manager = self.make_manager(outdoor=80.0)

        boost = manager._resolve_outdoor_boost_state()

        self.assertEqual(boost, OUTDOOR_BOOST_NONE)

    def test_default_hot_boost_activates_at_95(self) -> None:
        manager = self.make_manager(outdoor=95.0)

        boost = manager._resolve_outdoor_boost_state()

        self.assertEqual(boost, OUTDOOR_BOOST_HOT)

    def test_heating_uses_effective_target(self) -> None:
        manager = self.make_manager(outdoor=60.0)

        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, HVAC_PREF_HEAT)

        self.assertEqual(manager.runtime.comfort_offset, 1.0)
        self.assertEqual(manager.runtime.active_comfort_target, 71.0)
        self.assertEqual((target_heat, target_cool), (71.0, None))

    def test_heating_uses_positive_half_step_for_cool_outdoor_temperature(self) -> None:
        manager = self.make_manager(
            outdoor=62.0,
            config=ManagerConfig("climate.test", curve_weight_home=0.5),
        )

        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, HVAC_PREF_HEAT)

        self.assertEqual(manager.runtime.comfort_offset, 0.5)
        self.assertEqual(manager.runtime.active_comfort_target, 70.5)
        self.assertEqual((target_heat, target_cool), (70.5, None))

    def test_heating_season_uses_positive_half_step_for_cool_outdoor_temperature(self) -> None:
        manager = self.make_manager(
            outdoor=62.0,
            config=ManagerConfig("climate.test", curve_weight_home=0.5),
        )
        manager._current_season = lambda: SEASON_WINTER

        desired_mode = manager._resolve_desired_hvac_mode(PROFILE_HOME)
        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, desired_mode)

        self.assertEqual(desired_mode, HVAC_PREF_HEAT)
        self.assertEqual(manager.runtime.active_control_reason, "auto_heating_season")
        self.assertEqual(manager.runtime.comfort_offset, 0.5)
        self.assertEqual(manager.runtime.active_comfort_target, 70.5)
        self.assertEqual((target_heat, target_cool), (70.5, None))

    def test_heating_season_warm_outdoor_temperature_keeps_base_comfort_target(self) -> None:
        manager = self.make_manager(outdoor=75.0)
        manager._current_season = lambda: SEASON_WINTER

        desired_mode = manager._resolve_desired_hvac_mode(PROFILE_HOME)
        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, desired_mode)

        self.assertEqual(desired_mode, HVAC_PREF_HEAT)
        self.assertEqual(manager.runtime.outdoor_boost_state, OUTDOOR_BOOST_NONE)
        self.assertEqual(manager.runtime.comfort_offset, 0.0)
        self.assertEqual(manager.runtime.active_comfort_target, 70.0)
        self.assertEqual((target_heat, target_cool), (70.0, None))

    async def test_heating_service_call_uses_adjusted_comfort_target(self) -> None:
        services = FakeServices()
        manager = self.make_manager(
            outdoor=62.0,
            config=ManagerConfig("climate.test", curve_weight_home=0.5),
        )
        manager.hass = SimpleNamespace(services=services)
        manager._thermostat_snapshot = lambda: ThermostatSnapshot("heat", 70.5, None, None, None, True)
        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, HVAC_PREF_HEAT)
        manager.runtime.active_profile = PROFILE_HOME
        manager.runtime.desired_hvac_mode = HVAC_PREF_HEAT
        manager.runtime.target_heat = target_heat
        manager.runtime.target_cool = target_cool

        await manager._apply_if_needed(ThermostatSnapshot("heat", 70.0, None, None, None, True))

        self.assertEqual(len(services.calls), 1)
        domain, service, data, blocking = services.calls[0]
        self.assertEqual((domain, service, blocking), ("climate", "set_temperature", True))
        self.assertEqual(data["entity_id"], "climate.test")
        self.assertEqual(data["temperature"], 70.5)

    def test_cooling_uses_effective_target(self) -> None:
        manager = self.make_manager(outdoor=80.0)

        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, HVAC_PREF_COOL)

        self.assertEqual(manager.runtime.comfort_offset, -1.0)
        self.assertEqual(manager.runtime.active_comfort_target, 69.0)
        self.assertEqual((target_heat, target_cool), (None, 69.0))

    def test_cooling_season_uses_positive_half_step_for_cool_outdoor_temperature(self) -> None:
        manager = self.make_manager(
            outdoor=62.0,
            config=ManagerConfig("climate.test", curve_weight_home=0.5),
        )
        manager._current_season = lambda: SEASON_SUMMER

        desired_mode = manager._resolve_desired_hvac_mode(PROFILE_HOME)
        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, desired_mode)

        self.assertEqual(desired_mode, HVAC_PREF_COOL)
        self.assertEqual(manager.runtime.active_control_reason, "auto_cooling_season")
        self.assertEqual(manager.runtime.comfort_offset, 0.5)
        self.assertEqual(manager.runtime.active_comfort_target, 70.5)
        self.assertEqual((target_heat, target_cool), (None, 70.5))

    def test_heat_and_cool_modes_preserve_valid_comfort_offsets(self) -> None:
        heat_manager = self.make_manager(
            outdoor=62.0,
            config=ManagerConfig("climate.test", curve_weight_home=0.5),
        )
        cool_manager = self.make_manager(
            outdoor=62.0,
            config=ManagerConfig("climate.test", curve_weight_home=0.5),
        )

        target_heat, target_cool = heat_manager._resolve_comfort_auto_targets(PROFILE_HOME, HVAC_PREF_HEAT)
        cool_target_heat, cool_target_cool = cool_manager._resolve_comfort_auto_targets(PROFILE_HOME, HVAC_PREF_COOL)

        self.assertEqual(heat_manager.runtime.comfort_offset, 0.5)
        self.assertEqual((target_heat, target_cool), (70.5, None))
        self.assertEqual(cool_manager.runtime.comfort_offset, 0.5)
        self.assertEqual((cool_target_heat, cool_target_cool), (None, 70.5))

    async def test_cooling_service_call_uses_adjusted_comfort_target(self) -> None:
        services = FakeServices()
        manager = self.make_manager(
            outdoor=62.0,
            config=ManagerConfig("climate.test", curve_weight_home=0.5),
        )
        manager.hass = SimpleNamespace(services=services)
        manager._thermostat_snapshot = lambda: ThermostatSnapshot("cool", 70.5, None, None, None, True)
        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, HVAC_PREF_COOL)
        manager.runtime.active_profile = PROFILE_HOME
        manager.runtime.desired_hvac_mode = HVAC_PREF_COOL
        manager.runtime.target_heat = target_heat
        manager.runtime.target_cool = target_cool

        await manager._apply_if_needed(ThermostatSnapshot("cool", 70.0, None, None, None, True))

        self.assertEqual(len(services.calls), 1)
        domain, service, data, blocking = services.calls[0]
        self.assertEqual((domain, service, blocking), ("climate", "set_temperature", True))
        self.assertEqual(data["entity_id"], "climate.test")
        self.assertEqual(data["temperature"], 70.5)

    def test_manual_override_stays_outside_comfort_auto(self) -> None:
        manager = self.make_manager(outdoor=60.0)

        should_use_comfort = manager._should_use_comfort_auto_targets(PROFILE_MANUAL_OVERRIDE, HVAC_PREF_HEAT)

        self.assertFalse(should_use_comfort)

    def test_profile_comfort_target_switching_still_applies(self) -> None:
        config = ManagerConfig(
            "climate.test",
            sleep_comfort_target_override=True,
            sleep_comfort_target=68.0,
        )
        manager = self.make_manager(outdoor=58.0, config=config)

        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_SLEEP, "heat_cool")

        self.assertEqual(manager.runtime.comfort_offset, 0.5)
        self.assertEqual(manager.runtime.active_comfort_target, 68.5)
        self.assertEqual((target_heat, target_cool), (65.5, 71.5))

    async def test_transition_targets_generate_heat_cool_thermostat_command(self) -> None:
        services = FakeServices()
        manager = self.make_manager(outdoor=60.0)
        manager.hass = SimpleNamespace(services=services)
        manager._thermostat_snapshot = lambda: ThermostatSnapshot("heat_cool", None, 67.0, 73.0, None, True)
        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, "heat_cool")
        manager.runtime.active_profile = PROFILE_HOME
        manager.runtime.desired_hvac_mode = "heat_cool"
        manager.runtime.target_heat = target_heat
        manager.runtime.target_cool = target_cool

        await manager._apply_if_needed(ThermostatSnapshot("heat_cool", None, 67.0, 73.0, None, True))

        self.assertEqual(len(services.calls), 1)
        domain, service, data, blocking = services.calls[0]
        self.assertEqual((domain, service, blocking), ("climate", "set_temperature", True))
        self.assertEqual(data["entity_id"], "climate.test")
        self.assertEqual(data["target_temp_low"], 68.0)
        self.assertEqual(data["target_temp_high"], 74.0)


    def ceiling_manager(self, **options):
        config = ManagerConfig(
            "climate.test", comfort_target=71.0,
            occupied_cooling_ceiling_enabled=True, occupied_cooling_ceiling=72.0,
            minimum_auto_gap=5.0, max_cool_target=75.0, **options,
        )
        manager = self.make_manager(outdoor=53.38, config=config)
        manager.runtime.outdoor_boost_state = OUTDOOR_BOOST_COLD
        return manager

    async def test_live_daytime_regression_sends_67_72_instead_of_70_75(self):
        manager = self.ceiling_manager()
        manager.hass = SimpleNamespace(services=FakeServices())
        snapshot = ThermostatSnapshot("heat_cool", None, 70.0, 75.0, 74.0, True)
        manager._thermostat_snapshot = lambda: snapshot
        low, high = manager._resolve_targets(PROFILE_HOME, "heat_cool")
        self.assertEqual((low, high), (67.0, 72.0))
        self.assertEqual(manager.runtime.transition_cool_target, 72.0)
        self.assertIn("occupied_cooling_ceiling", manager.runtime.active_control_reason)
        manager.runtime.active_profile = PROFILE_HOME
        manager.runtime.desired_hvac_mode = "heat_cool"
        manager.runtime.target_heat, manager.runtime.target_cool = low, high
        await manager._apply_if_needed(snapshot)
        payload = manager.hass.services.calls[-1][2]
        self.assertEqual((payload["target_temp_low"], payload["target_temp_high"]), (67.0, 72.0))

    def test_ceiling_preserves_sleep_and_away_targets(self):
        from custom_components.climate_manager.const import PROFILE_AWAY
        for profile in (PROFILE_SLEEP, PROFILE_AWAY):
            manager = self.ceiling_manager()
            capped = manager._resolve_targets(profile, "heat_cool")
            manager.config.occupied_cooling_ceiling_enabled = False
            self.assertEqual(capped, manager._resolve_targets(profile, "heat_cool"))

    def test_ceiling_applies_to_guest_and_pre_arrival(self):
        from custom_components.climate_manager.const import PROFILE_GUEST, PROFILE_PRE_ARRIVAL
        for profile in (PROFILE_HOME, PROFILE_GUEST, PROFILE_PRE_ARRIVAL):
            manager = self.ceiling_manager()
            self.assertEqual(manager._resolve_targets(profile, "heat_cool"), (67.0, 72.0))

    def test_ceiling_preserves_explicit_preferences_and_heating(self):
        from custom_components.climate_manager.const import HVAC_PREF_OFF
        for preference, mode in ((HVAC_PREF_HEAT, "heat"), (HVAC_PREF_COOL, "cool"), (HVAC_PREF_OFF, None)):
            manager = self.ceiling_manager(hvac_preference=preference)
            capped = manager._resolve_targets(PROFILE_HOME, mode)
            manager.config.occupied_cooling_ceiling_enabled = False
            self.assertEqual(capped, manager._resolve_targets(PROFILE_HOME, mode))
        manager = self.ceiling_manager()
        capped = manager._resolve_targets(PROFILE_HOME, "heat")
        manager.config.occupied_cooling_ceiling_enabled = False
        self.assertEqual(capped, manager._resolve_targets(PROFILE_HOME, "heat"))

    def test_ceiling_applies_to_summer_auto_cooling(self):
        manager = self.ceiling_manager()
        self.assertEqual(manager._resolve_targets(PROFILE_HOME, "cool"), (None, 72.0))

    def test_ceiling_never_warms_existing_cooler_target(self):
        manager = self.ceiling_manager()
        manager._outdoor_temperature_f = lambda: 95.0
        manager.runtime.outdoor_boost_state = OUTDOOR_BOOST_HOT
        capped = manager._resolve_targets(PROFILE_HOME, "heat_cool")
        manager.config.occupied_cooling_ceiling_enabled = False
        self.assertEqual(capped, manager._resolve_targets(PROFILE_HOME, "heat_cool"))

    def test_ceiling_respects_safety_floor_and_gap(self):
        manager = self.ceiling_manager(min_cool_target=73.0)
        low, high = manager._resolve_targets(PROFILE_HOME, "heat_cool")
        self.assertEqual((low, high), (68.0, 73.0))
        self.assertIn("occupied_cooling_ceiling_safety_limited", manager.runtime.active_control_reason)
        manager = self.ceiling_manager(min_heat_target=69.0)
        self.assertEqual(manager._resolve_targets(PROFILE_HOME, "heat_cool"), (69.0, 74.0))

    def test_ceiling_does_not_change_smart_control_disabled_targets(self):
        manager = self.ceiling_manager(smart_control_enabled=False)
        capped = manager._resolve_targets(PROFILE_HOME, "heat_cool")
        manager.config.occupied_cooling_ceiling_enabled = False
        self.assertEqual(capped, manager._resolve_targets(PROFILE_HOME, "heat_cool"))

    def test_ceiling_preserves_blocking_and_window_profiles(self):
        from custom_components.climate_manager.const import (
            PROFILE_PAUSED, PROFILE_OVERRIDE_LOCK, PROFILE_SENSORS_OPEN,
        )
        for profile, mode in ((PROFILE_MANUAL_OVERRIDE, None), (PROFILE_PAUSED, None),
                              (PROFILE_OVERRIDE_LOCK, None), (PROFILE_SENSORS_OPEN, "off")):
            manager = self.ceiling_manager()
            capped = manager._resolve_targets(profile, mode)
            manager.config.occupied_cooling_ceiling_enabled = False
            self.assertEqual(capped, manager._resolve_targets(profile, mode))


if __name__ == "__main__":
    unittest.main()
