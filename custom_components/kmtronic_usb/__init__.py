"""The KMTronic USB relay integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import CONF_PORT, CONF_RELAY_COUNT, TYPE_DISABLED, RelayConfig
from .coordinator import KMTronicConfigEntry, KMTronicCoordinator
from .entity import relay_unique_id
from .kmtronic import KMTronicUSB

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.LIGHT, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: KMTronicConfigEntry) -> bool:
    """Set up a KMTronic USB relay board from a config entry."""
    board = KMTronicUSB(entry.data[CONF_PORT], entry.data[CONF_RELAY_COUNT])
    coordinator = KMTronicCoordinator(hass, entry, board)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await hass.async_add_executor_job(board.close)
        raise

    entry.runtime_data = coordinator
    _async_remove_stale_entities(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KMTronicConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await hass.async_add_executor_job(entry.runtime_data.board.close)
    return unloaded


@callback
def _async_remove_stale_entities(
    hass: HomeAssistant, entry: KMTronicConfigEntry
) -> None:
    """Remove entities left behind when a relay changed type or was disabled."""
    expected: dict[str, str] = {}
    for relay in range(1, entry.data[CONF_RELAY_COUNT] + 1):
        config = RelayConfig.from_options(entry.options, relay)
        if config.type != TYPE_DISABLED:
            expected[relay_unique_id(entry, relay)] = config.type

    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if expected.get(entity.unique_id) != entity.domain:
            registry.async_remove(entity.entity_id)
