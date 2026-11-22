"""Switch platform for the KMTronic USB relay integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import TYPE_SWITCH
from .coordinator import KMTronicConfigEntry
from .entity import KMTronicRelayEntity, relay_configs

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KMTronicConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the relays configured as switches."""
    async_add_entities(
        KMTronicSwitch(entry.runtime_data, config)
        for config in relay_configs(entry, TYPE_SWITCH)
    )


class KMTronicSwitch(KMTronicRelayEntity, SwitchEntity):
    """A relay exposed as a switch."""

    @property
    def is_on(self) -> bool:
        """Return True if the switch is on."""
        return self._active

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._async_set_active(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._async_set_active(False)
