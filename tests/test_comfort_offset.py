"""Regression tests for comfort offset target resolution."""
from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "custom_components" / "climate_manager"


def install_homeassistant_stubs() -> None:
    """Install enough Home Assistant modules to import manager pure logic."""
    homeassistant = types.ModuleType("homeassistant")
    const = types.ModuleType("homeassistant.const")
    core = types.ModuleType("homeassistant.core")
    helpers = types.ModuleType("homeassistant.helpers")
    event = types.ModuleType("homeassistant.helpers.event")
    storage = types.ModuleType("homeassistant.helpers.storage")
    util = types.ModuleType("homeassistant.util")
    dt = types.ModuleType("homeassistant.util.dt")

    class UnitOfTemperature:
        FAHRENHEIT = "F"
        CELSIUS = "C"

    class Store:
        def __class_getitem__(cls, _item):
            return cls

        def __init__(self, *_args, **_kwargs) -> None:
            self.data = None

        async def async_load(self):
            return self.data

        async def async_save(self, data):
            self.data = data

    const.ATTR_ENTITY_ID = "entity_id"
    const.STATE_OFF = "off"
    const.STATE_ON = "on"
    const.UnitOfTemperature = UnitOfTemperature
    core.CALLBACK_TYPE = object
    core.HomeAssistant = object
    core.callback = lambda func: func
    event.async_call_later = lambda *_args, **_kwargs: None
    event.async_track_state_change_event = lambda *_args, **_kwargs: None
    storage.Store = Store
    dt.utcnow = lambda: datetime(2026, 1, 1, tzinfo=timezone.utc)
    dt.parse_datetime = lambda value: value
    util.dt = dt
    helpers.event = event
    helpers.storage = storage

    sys.modules.setdefault("homeassistant", homeassistant)
    sys.modules.setdefault("homeassistant.const", const)
    sys.modules.setdefault("homeassistant.core", core)
    sys.modules.setdefault("homeassistant.helpers", helpers)
    sys.modules.setdefault("homeassistant.helpers.event", event)
    sys.modules.setdefault("homeassistant.helpers.storage", storage)
    sys.modules.setdefault("homeassistant.util", util)
    sys.modules.setdefault("homeassistant.util.dt", dt)


def install_package_stub() -> None:
    custom_components = types.ModuleType("custom_components")
    package = types.ModuleType("custom_components.climate_manager")
    package.__path__ = [str(PACKAGE_ROOT)]
    sys.modules.setdefault("custom_components", custom_components)
    sys.modules.setdefault("custom_components.climate_manager", package)


install_homeassistant_stubs()
install_package_stub()

from custom_components.climate_manager.const import (  # noqa: E402
    HVAC_PREF_COOL,
    HVAC_PREF_HEAT,
    PROFILE_HOME,
    PROFILE_MANUAL_OVERRIDE,
    PROFILE_SLEEP,
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

    def test_cooling_uses_effective_target(self) -> None:
        manager = self.make_manager(outdoor=80.0)

        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, HVAC_PREF_COOL)

        self.assertEqual(manager.runtime.comfort_offset, -1.0)
        self.assertEqual(manager.runtime.active_comfort_target, 69.0)
        self.assertEqual((target_heat, target_cool), (None, 69.0))

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


if __name__ == "__main__":
    unittest.main()
