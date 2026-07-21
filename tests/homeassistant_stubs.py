"""Small Home Assistant stubs for the repository's standalone unit tests."""
from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "custom_components" / "climate_manager"


def install_homeassistant_stubs() -> None:
    """Install enough Home Assistant modules to import integration logic."""
    homeassistant = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    config_entries = sys.modules.setdefault(
        "homeassistant.config_entries",
        types.ModuleType("homeassistant.config_entries"),
    )
    const = sys.modules.setdefault("homeassistant.const", types.ModuleType("homeassistant.const"))
    core = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))
    helpers = sys.modules.setdefault("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
    config_validation = sys.modules.setdefault(
        "homeassistant.helpers.config_validation",
        types.ModuleType("homeassistant.helpers.config_validation"),
    )
    event = sys.modules.setdefault(
        "homeassistant.helpers.event",
        types.ModuleType("homeassistant.helpers.event"),
    )
    selector = sys.modules.setdefault(
        "homeassistant.helpers.selector",
        types.ModuleType("homeassistant.helpers.selector"),
    )
    storage = sys.modules.setdefault(
        "homeassistant.helpers.storage",
        types.ModuleType("homeassistant.helpers.storage"),
    )
    util = sys.modules.setdefault("homeassistant.util", types.ModuleType("homeassistant.util"))
    dt = sys.modules.setdefault("homeassistant.util.dt", types.ModuleType("homeassistant.util.dt"))

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

    class ConfigFlow:
        def __init_subclass__(cls, **_kwargs) -> None:
            return super().__init_subclass__()

        async def async_set_unique_id(self, _unique_id) -> None:
            self.test_unique_id = _unique_id
            return None

        def _abort_if_unique_id_configured(self) -> None:
            self.test_duplicate_check_called = True
            return None

        def async_create_entry(self, *, title, data):
            return {"type": "create_entry", "title": title, "data": data}

        def async_show_form(self, *, step_id, data_schema, errors=None):
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors or {},
            }

        def async_show_menu(self, *, step_id, menu_options):
            return {"type": "menu", "step_id": step_id, "menu_options": menu_options}

    class OptionsFlow(ConfigFlow):
        pass

    class EntitySelectorConfig:
        def __init__(self, **kwargs) -> None:
            self.__dict__.update(kwargs)

    class EntitySelector:
        def __init__(self, config) -> None:
            self.config = config

    class NumberSelectorConfig(EntitySelectorConfig):
        pass

    class NumberSelector(EntitySelector):
        pass

    class SelectSelectorConfig(EntitySelectorConfig):
        pass

    class SelectSelector(EntitySelector):
        pass

    class BooleanSelector:
        pass

    config_entries.ConfigEntry = object
    config_entries.ConfigFlow = ConfigFlow
    config_entries.OptionsFlow = OptionsFlow
    const.ATTR_ENTITY_ID = "entity_id"
    const.STATE_OFF = "off"
    const.STATE_ON = "on"
    const.UnitOfTemperature = UnitOfTemperature
    core.CALLBACK_TYPE = object
    core.HomeAssistant = object
    core.ServiceCall = object
    core.callback = lambda func: func
    config_validation.string = str
    event.async_call_later = lambda *_args, **_kwargs: None
    event.async_track_state_change_event = lambda *_args, **_kwargs: None
    selector.EntitySelector = EntitySelector
    selector.EntitySelectorConfig = EntitySelectorConfig
    selector.NumberSelector = NumberSelector
    selector.NumberSelectorConfig = NumberSelectorConfig
    selector.NumberSelectorMode = SimpleNamespace(BOX="box")
    selector.SelectSelector = SelectSelector
    selector.SelectSelectorConfig = SelectSelectorConfig
    selector.SelectSelectorMode = SimpleNamespace(DROPDOWN="dropdown")
    selector.BooleanSelector = BooleanSelector
    storage.Store = Store
    dt.utcnow = lambda: datetime(2026, 1, 1, tzinfo=timezone.utc)
    dt.parse_datetime = lambda value: value

    homeassistant.config_entries = config_entries
    helpers.config_validation = config_validation
    helpers.event = event
    helpers.selector = selector
    helpers.storage = storage
    util.dt = dt


def install_voluptuous_stub() -> None:
    """Install the small voluptuous surface used by config_flow."""
    if "voluptuous" in sys.modules:
        return

    voluptuous = types.ModuleType("voluptuous")

    class Marker:
        def __init__(self, schema, default=None) -> None:
            self.schema = schema
            self.default = default

    class Required(Marker):
        pass

    class Optional(Marker):
        pass

    class Schema:
        def __init__(self, schema, **_kwargs) -> None:
            self.schema = schema

        def __call__(self, value):
            return value

    voluptuous.ALLOW_EXTRA = object()
    voluptuous.Coerce = lambda target: target
    voluptuous.Optional = Optional
    voluptuous.Required = Required
    voluptuous.Schema = Schema
    sys.modules["voluptuous"] = voluptuous


def install_package_stub() -> None:
    """Expose the custom component package without executing its __init__."""
    custom_components = sys.modules.setdefault("custom_components", types.ModuleType("custom_components"))
    package = sys.modules.setdefault(
        "custom_components.climate_manager",
        types.ModuleType("custom_components.climate_manager"),
    )
    custom_components.climate_manager = package
    package.__path__ = [str(PACKAGE_ROOT)]
