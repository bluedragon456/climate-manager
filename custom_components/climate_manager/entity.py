"""Shared entity base for Climate Manager."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .manager import ClimateManager


class ClimateManagerEntity(Entity):
    """Base entity for Climate Manager."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry_id: str, manager: ClimateManager) -> None:
        self._entry_id = entry_id
        self._manager = manager

    @property
    def available(self) -> bool:
        return True

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name="Climate Manager",
            manufacturer="Climate Manager",
            model="Climate Manager Controller",
        )