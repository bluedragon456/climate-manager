"""Button platform for Climate Manager."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DATA_MANAGER, DOMAIN
from .manager import ClimateManager


@dataclass(frozen=True, kw_only=True)
class ClimateManagerButtonDescription(ButtonEntityDescription):
    press_fn_name: str


BUTTONS: tuple[ClimateManagerButtonDescription, ...] = (
    ClimateManagerButtonDescription(
        key="recalculate_now",
        translation_key="recalculate_now",
        press_fn_name="async_recalculate",
        entity_category=EntityCategory.CONFIG,
    ),
    ClimateManagerButtonDescription(
        key="clear_override",
        translation_key="clear_override",
        press_fn_name="async_clear_override",
        entity_category=EntityCategory.CONFIG,
    ),
    ClimateManagerButtonDescription(
        key="pause",
        translation_key="pause",
        press_fn_name="async_pause",
        entity_category=EntityCategory.CONFIG,
    ),
    ClimateManagerButtonDescription(
        key="resume",
        translation_key="resume",
        press_fn_name="async_resume",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up button entities."""
    manager: ClimateManager = hass.data[DOMAIN][entry.entry_id][DATA_MANAGER]
    async_add_entities(
        [ClimateManagerButton(entry.entry_id, manager, description) for description in BUTTONS]
    )


class ClimateManagerButton(ButtonEntity):
    """Climate Manager button."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        entry_id: str,
        manager: ClimateManager,
        description: ClimateManagerButtonDescription,
    ) -> None:
        self.entity_description = description
        self._entry_id = entry_id
        self._manager = manager
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name="Climate Manager",
            manufacturer="Climate Manager",
            model="Climate Manager Controller",
        )

    async def async_press(self) -> None:
        method = getattr(self._manager, self.entity_description.press_fn_name)
        if self.entity_description.press_fn_name == "async_recalculate":
            await method("button")
        else:
            await method()
        self.async_write_ha_state()