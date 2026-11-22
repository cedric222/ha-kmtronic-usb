"""Light platform for the KMTronic USB relay integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import TYPE_LIGHT
from .coordinator import KMTronicConfigEntry
from .entity import KMTronicRelayEntity, relay_configs

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KMTronicConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the relays configured as lights."""
    async_add_entities(
        KMTronicLight(entry.runtime_data, config)
        for config in relay_configs(entry, TYPE_LIGHT)
    )


class KMTronicLight(KMTronicRelayEntity, LightEntity):
    """A relay exposed as an on/off light."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    @property
    def is_on(self) -> bool:
        """Return True if the light is on."""
        return self._active

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        await self._async_set_active(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self._async_set_active(False)
