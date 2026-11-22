"""Base entity for the KMTronic USB relay integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, RelayConfig
from .coordinator import KMTronicConfigEntry, KMTronicCoordinator


def relay_configs(entry: KMTronicConfigEntry, relay_type: str) -> list[RelayConfig]:
    """Return the settings of every relay configured with the given type."""
    configs = (
        RelayConfig.from_options(entry.options, relay)
        for relay in range(1, entry.runtime_data.relay_count + 1)
    )
    return [config for config in configs if config.type == relay_type]


def relay_unique_id(entry: KMTronicConfigEntry, relay: int) -> str:
    """Return the unique id of the entity bound to a relay."""
    return f"{entry.unique_id or entry.entry_id}_relay_{relay}"


class KMTronicRelayEntity(CoordinatorEntity[KMTronicCoordinator]):
    """An entity driving one relay of the board."""

    _attr_has_entity_name = True
    _attr_translation_key = "relay"

    def __init__(self, coordinator: KMTronicCoordinator, config: RelayConfig) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._config = config
        self._attr_unique_id = relay_unique_id(entry, config.relay)
        self._attr_translation_placeholders = {"relay": str(config.relay)}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            manufacturer="KMtronic",
            model=f"USB {coordinator.relay_count} relays",
            name=entry.title,
        )

    @property
    def available(self) -> bool:
        """Return True if the board answered the last poll."""
        return super().available and self.coordinator.data is not None

    @property
    def _active(self) -> bool:
        """Return the logical state, taking NC wiring into account."""
        return self.coordinator.data[self._config.relay - 1] != self._config.inverted

    async def _async_set_active(self, active: bool) -> None:
        await self.coordinator.async_set_relay(
            self._config.relay, active != self._config.inverted
        )
