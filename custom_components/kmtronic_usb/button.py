"""Button platform for the KMTronic USB relay integration (impulse relays)."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import TYPE_BUTTON
from .coordinator import KMTronicConfigEntry
from .entity import KMTronicRelayEntity, relay_configs

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KMTronicConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the relays configured as buttons."""
    async_add_entities(
        KMTronicButton(entry.runtime_data, config)
        for config in relay_configs(entry, TYPE_BUTTON)
    )


class KMTronicButton(KMTronicRelayEntity, ButtonEntity):
    """A relay pulsed for a configurable duration (gate, garage door...)."""

    async def async_press(self) -> None:
        """Pulse the relay."""
        await self.coordinator.async_pulse(self._config)
