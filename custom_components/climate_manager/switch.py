"""Switch platform for Climate Manager."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DATA_MANAGER, DOMAIN
from .entity import ClimateManagerEntity
from .manager import ClimateManager


@dataclass(frozen=True, kw_only=True)
class ClimateManagerSwitchDescription(SwitchEntityDescription):
    pass


SWITCHES: tuple[ClimateManagerSwitchDescription, ...] = (
    ClimateManagerSwitchDescription(
        key="enabled",
        translation_key="enabled",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up switch entities."""
    manager: ClimateManager = hass.data[DOMAIN][entry.entry_id][DATA_MANAGER]
    async_add_entities([ClimateManagerEnabledSwitch(entry.entry_id, manager, SWITCHES[0])])


class ClimateManagerEnabledSwitch(ClimateManagerEntity, SwitchEntity):
    """Master enable switch for Climate Manager."""

    def __init__(
        self,
        entry_id: str,
        manager: ClimateManager,
        description: ClimateManagerSwitchDescription,
    ) -> None:
        super().__init__(entry_id, manager)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def is_on(self) -> bool:
        return not self._manager.runtime.paused

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._manager.async_resume()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._manager.async_pause()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._manager.async_subscribe(self.async_write_ha_state))