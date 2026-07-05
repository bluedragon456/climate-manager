"""Regression tests for reconfiguring Climate Manager dependency entities."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

from homeassistant_stubs import (
    install_homeassistant_stubs,
    install_package_stub,
    install_voluptuous_stub,
)


ROOT = Path(__file__).resolve().parents[1]

install_homeassistant_stubs()
install_voluptuous_stub()
install_package_stub()

from custom_components.climate_manager.config_flow import (  # noqa: E402
    EDITABLE_ENTITY_CONFIG_KEYS,
    ENTITY_CONFIG_KEYS,
    ClimateManagerConfigFlow,
    ClimateManagerOptionsFlow,
)
from custom_components.climate_manager.const import (  # noqa: E402
    CONF_AWAY_ENTITY,
    CONF_COMFORT_TARGET,
    CONF_COOL_CURVE_WEIGHT_HOME,
    CONF_CURVE_WEIGHT_HOME,
    CONF_GUEST_ENTITY,
    CONF_OUTDOOR_TEMP_ENTITY,
    CONF_OVERRIDE_ENTITY,
    CONF_SEASON_ENTITY,
    CONF_SLEEP_SCHEDULE_ENTITY,
    CONF_TEMPERATURE_UNIT_MODE,
    CONF_THERMOSTAT_ENTITY,
    CONF_WINDOWS_ENTITY,
    HVAC_PREF_COOL,
    PROFILE_HOME,
    TEMPERATURE_UNIT_MODE_CELSIUS,
)
from custom_components.climate_manager.manager import ClimateManager  # noqa: E402


ENTITY_ATTRIBUTES = {
    CONF_THERMOSTAT_ENTITY: "thermostat_entity",
    CONF_OUTDOOR_TEMP_ENTITY: "outdoor_temp_entity",
    CONF_SLEEP_SCHEDULE_ENTITY: "sleep_schedule_entity",
    CONF_AWAY_ENTITY: "away_entity",
    CONF_GUEST_ENTITY: "guest_entity",
    CONF_OVERRIDE_ENTITY: "override_entity",
    CONF_WINDOWS_ENTITY: "windows_entity",
    CONF_SEASON_ENTITY: "season_entity",
}
ENTITY_DOMAINS = {
    CONF_THERMOSTAT_ENTITY: "climate",
    CONF_OUTDOOR_TEMP_ENTITY: "sensor",
    CONF_SLEEP_SCHEDULE_ENTITY: "schedule",
    CONF_AWAY_ENTITY: "input_boolean",
    CONF_GUEST_ENTITY: "input_boolean",
    CONF_OVERRIDE_ENTITY: "input_boolean",
    CONF_WINDOWS_ENTITY: "binary_sensor",
    CONF_SEASON_ENTITY: ["input_text", "sensor", "select"],
}
OLD_ENTITIES = {
    CONF_THERMOSTAT_ENTITY: "climate.old",
    CONF_OUTDOOR_TEMP_ENTITY: "sensor.old_outdoor",
    CONF_SLEEP_SCHEDULE_ENTITY: "schedule.old_sleep",
    CONF_AWAY_ENTITY: "input_boolean.old_away",
    CONF_GUEST_ENTITY: "input_boolean.old_guest",
    CONF_OVERRIDE_ENTITY: "input_boolean.old_override",
    CONF_WINDOWS_ENTITY: "binary_sensor.old_windows",
    CONF_SEASON_ENTITY: "sensor.old_season",
}
NEW_ENTITIES = {
    CONF_THERMOSTAT_ENTITY: "climate.new",
    CONF_OUTDOOR_TEMP_ENTITY: "sensor.new_outdoor",
    CONF_SLEEP_SCHEDULE_ENTITY: "schedule.new_sleep",
    CONF_AWAY_ENTITY: "input_boolean.new_away",
    CONF_GUEST_ENTITY: "input_boolean.new_guest",
    CONF_OVERRIDE_ENTITY: "input_boolean.new_override",
    CONF_WINDOWS_ENTITY: "binary_sensor.new_windows",
    CONF_SEASON_ENTITY: "select.new_season",
}
NEW_EDITABLE_ENTITIES = {
    key: value
    for key, value in NEW_ENTITIES.items()
    if key in EDITABLE_ENTITY_CONFIG_KEYS
}


def load_integration_module():
    """Load integration __init__ under an alias so its config builder can be tested."""
    module_name = "custom_components.climate_manager.integration_under_test"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(
        module_name,
        ROOT / "custom_components" / "climate_manager" / "__init__.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


integration = load_integration_module()


class FakeStates:
    def __init__(self, states: dict[str, object]) -> None:
        self._states = states

    def get(self, entity_id):
        value = self._states.get(entity_id)
        if value is None:
            return None
        if hasattr(value, "state"):
            return value
        return SimpleNamespace(state=value, attributes={})

    def is_state(self, entity_id, state) -> bool:
        current = self.get(entity_id)
        return current is not None and current.state == state


def make_hass(states: dict[str, object] | None = None):
    return SimpleNamespace(
        config=SimpleNamespace(units=SimpleNamespace(temperature_unit="F")),
        states=FakeStates(states or {}),
    )


def make_entry(*, data: dict, options: dict | None = None):
    return SimpleNamespace(data=data, options=options or {})


def schema_fields(result) -> dict[str, tuple[object, object]]:
    return {
        marker.schema: (marker, field_selector)
        for marker, field_selector in result["data_schema"].schema.items()
    }


class EntityOptionsTests(unittest.IsolatedAsyncioTestCase):
    async def test_setup_uses_thermostat_as_stable_unique_id(self) -> None:
        flow = ClimateManagerConfigFlow()

        await flow.async_step_user(dict(OLD_ENTITIES))

        self.assertEqual(flow.test_unique_id, OLD_ENTITIES[CONF_THERMOSTAT_ENTITY])
        self.assertTrue(flow.test_duplicate_check_called)

    def test_existing_entry_uses_all_entities_stored_in_data(self) -> None:
        config = integration._build_manager_config(
            make_hass(),
            make_entry(data=OLD_ENTITIES),
        )

        for key, attribute in ENTITY_ATTRIBUTES.items():
            self.assertEqual(getattr(config, attribute), OLD_ENTITIES[key])

    async def test_setup_and_options_show_all_entity_dependencies(self) -> None:
        setup_result = await ClimateManagerConfigFlow().async_step_user()
        options_result = await ClimateManagerOptionsFlow(
            make_entry(data=OLD_ENTITIES)
        ).async_step_entities()

        setup_fields = schema_fields(setup_result)
        options_fields = schema_fields(options_result)
        self.assertTrue(set(ENTITY_CONFIG_KEYS).issubset(setup_fields))
        self.assertEqual(set(options_fields), set(EDITABLE_ENTITY_CONFIG_KEYS))
        self.assertNotIn(CONF_THERMOSTAT_ENTITY, options_fields)

        for key in EDITABLE_ENTITY_CONFIG_KEYS:
            marker, field_selector = options_fields[key]
            self.assertEqual(marker.default, OLD_ENTITIES[key])
            self.assertEqual(field_selector.config.domain, ENTITY_DOMAINS[key])

    async def test_current_option_values_are_preselected(self) -> None:
        current = dict(NEW_EDITABLE_ENTITIES)
        result = await ClimateManagerOptionsFlow(
            make_entry(data=OLD_ENTITIES, options=current)
        ).async_step_entities()

        fields = schema_fields(result)
        for key in EDITABLE_ENTITY_CONFIG_KEYS:
            self.assertEqual(fields[key][0].default, current[key])

    async def test_changing_every_entity_stores_options_and_preserves_settings(self) -> None:
        flow = ClimateManagerOptionsFlow(
            make_entry(
                data=OLD_ENTITIES,
                options={
                    CONF_COMFORT_TARGET: 71.0,
                    CONF_THERMOSTAT_ENTITY: NEW_ENTITIES[CONF_THERMOSTAT_ENTITY],
                },
            )
        )

        result = await flow.async_step_entities(dict(NEW_EDITABLE_ENTITIES))

        for key in EDITABLE_ENTITY_CONFIG_KEYS:
            self.assertEqual(result["data"][key], NEW_EDITABLE_ENTITIES[key])
        self.assertNotIn(CONF_THERMOSTAT_ENTITY, result["data"])
        self.assertEqual(result["data"][CONF_COMFORT_TARGET], 71.0)

    async def test_omitted_optional_entities_are_cleared_in_options(self) -> None:
        required_only = {
            CONF_OUTDOOR_TEMP_ENTITY: NEW_ENTITIES[CONF_OUTDOOR_TEMP_ENTITY],
        }

        result = await ClimateManagerOptionsFlow(
            make_entry(data=OLD_ENTITIES)
        ).async_step_entities(required_only)

        self.assertEqual(result["data"][CONF_OUTDOOR_TEMP_ENTITY], "sensor.new_outdoor")
        self.assertNotIn(CONF_THERMOSTAT_ENTITY, result["data"])
        for key in EDITABLE_ENTITY_CONFIG_KEYS:
            if key not in required_only:
                self.assertIsNone(result["data"][key])

    def test_later_settings_changes_preserve_all_entity_overrides(self) -> None:
        overrides = dict(NEW_EDITABLE_ENTITIES)
        overrides[CONF_GUEST_ENTITY] = None
        overrides[CONF_THERMOSTAT_ENTITY] = NEW_ENTITIES[CONF_THERMOSTAT_ENTITY]
        flow = ClimateManagerOptionsFlow(
            make_entry(data=OLD_ENTITIES, options=overrides)
        )

        result = flow._save({CONF_COMFORT_TARGET: 72.0}, "F")

        for key in EDITABLE_ENTITY_CONFIG_KEYS:
            self.assertEqual(result["data"][key], overrides[key])
        self.assertNotIn(CONF_THERMOSTAT_ENTITY, result["data"])
        self.assertEqual(result["data"][CONF_COMFORT_TARGET], 72.0)

    async def test_temperature_unit_change_preserves_all_entity_overrides(self) -> None:
        flow = ClimateManagerOptionsFlow(
            make_entry(data=OLD_ENTITIES, options=dict(NEW_EDITABLE_ENTITIES))
        )
        flow.hass = make_hass()

        result = await flow.async_step_temperature_units(
            {CONF_TEMPERATURE_UNIT_MODE: TEMPERATURE_UNIT_MODE_CELSIUS}
        )

        for key in EDITABLE_ENTITY_CONFIG_KEYS:
            self.assertEqual(result["data"][key], NEW_EDITABLE_ENTITIES[key])
        self.assertNotIn(CONF_THERMOSTAT_ENTITY, result["data"])
        self.assertEqual(
            result["data"][CONF_TEMPERATURE_UNIT_MODE],
            TEMPERATURE_UNIT_MODE_CELSIUS,
        )

    async def test_comfort_curve_options_write_same_keys_runtime_reads(self) -> None:
        flow = ClimateManagerOptionsFlow(make_entry(data=OLD_ENTITIES))
        flow.hass = make_hass()

        result = await flow.async_step_comfort_curve(
            {
                CONF_CURVE_WEIGHT_HOME: 0.5,
                CONF_COOL_CURVE_WEIGHT_HOME: 0.25,
            }
        )

        self.assertEqual(result["data"][CONF_CURVE_WEIGHT_HOME], 0.5)
        self.assertEqual(result["data"][CONF_COOL_CURVE_WEIGHT_HOME], 0.25)

        config = integration._build_manager_config(
            make_hass(),
            make_entry(data=OLD_ENTITIES, options=result["data"]),
        )

        self.assertEqual(config.curve_weight_home, 0.5)
        self.assertEqual(config.cool_curve_weight_home, 0.25)

    def test_changed_comfort_curve_options_are_reflected_after_reload_build(self) -> None:
        entry = make_entry(
            data=OLD_ENTITIES,
            options={CONF_CURVE_WEIGHT_HOME: 1.0},
        )
        initial = integration._build_manager_config(make_hass(), entry)

        entry.options = {CONF_CURVE_WEIGHT_HOME: 0.5}
        reloaded = integration._build_manager_config(make_hass(), entry)

        self.assertEqual(initial.curve_weight_home, 1.0)
        self.assertEqual(reloaded.curve_weight_home, 0.5)

    async def test_reload_entry_uses_home_assistant_config_entry_reload(self) -> None:
        calls = []

        class FakeConfigEntries:
            async def async_reload(self, entry_id):
                calls.append(entry_id)

        await integration.async_reload_entry(
            SimpleNamespace(config_entries=FakeConfigEntries()),
            SimpleNamespace(entry_id="entry"),
        )

        self.assertEqual(calls, ["entry"])

    def test_runtime_ignores_thermostat_option_and_uses_other_overrides(self) -> None:
        hass = make_hass(
            {
                "climate.old": SimpleNamespace(
                    state="off",
                    attributes={"current_temperature": 40},
                ),
                "climate.new": SimpleNamespace(
                    state="heat",
                    attributes={"current_temperature": 70},
                ),
                "sensor.old_outdoor": "40",
                "sensor.new_outdoor": "72",
            }
        )
        config = integration._build_manager_config(
            hass,
            make_entry(data=OLD_ENTITIES, options=NEW_ENTITIES),
        )
        manager = ClimateManager(hass, "entry", config)

        for key, attribute in ENTITY_ATTRIBUTES.items():
            expected = (
                OLD_ENTITIES[key]
                if key == CONF_THERMOSTAT_ENTITY
                else NEW_ENTITIES[key]
            )
            self.assertEqual(getattr(config, attribute), expected)
        self.assertEqual(manager._outdoor_temperature_f(), 72.0)
        self.assertEqual(manager._thermostat_snapshot().hvac_mode, "off")

    def test_entity_reconfiguration_uses_new_outdoor_sensor_with_curve_options(self) -> None:
        hass = make_hass(
            {
                "sensor.old_outdoor": "70",
                "sensor.new_outdoor": "62",
            }
        )
        options = {
            **NEW_EDITABLE_ENTITIES,
            CONF_CURVE_WEIGHT_HOME: 0.5,
        }
        config = integration._build_manager_config(
            hass,
            make_entry(data=OLD_ENTITIES, options=options),
        )
        manager = ClimateManager(hass, "entry", config)

        target_heat, target_cool = manager._resolve_comfort_auto_targets(PROFILE_HOME, HVAC_PREF_COOL)

        self.assertEqual(config.outdoor_temp_entity, NEW_ENTITIES[CONF_OUTDOOR_TEMP_ENTITY])
        self.assertEqual(manager._outdoor_temperature_f(), 62.0)
        self.assertEqual(manager.runtime.comfort_offset, 0.5)
        self.assertEqual((target_heat, target_cool), (None, 70.5))

    def test_missing_or_unavailable_entities_do_not_crash_runtime(self) -> None:
        config = integration._build_manager_config(
            make_hass(),
            make_entry(data=OLD_ENTITIES, options=NEW_EDITABLE_ENTITIES),
        )
        missing = ClimateManager(make_hass(), "missing", config)
        unavailable = ClimateManager(
            make_hass(
                {
                    "climate.old": SimpleNamespace(
                        state="unavailable",
                        attributes={},
                    ),
                    "sensor.new_outdoor": "unavailable",
                }
            ),
            "unavailable",
            config,
        )

        self.assertFalse(missing._thermostat_snapshot().available)
        self.assertIsNone(missing._outdoor_temperature_f())
        self.assertEqual(missing._resolve_profile(), PROFILE_HOME)
        self.assertFalse(unavailable._thermostat_snapshot().available)
        self.assertIsNone(unavailable._outdoor_temperature_f())


if __name__ == "__main__":
    unittest.main()
