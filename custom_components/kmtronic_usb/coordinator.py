"""Data update coordinator for the KMTronic USB relay integration."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_RELAY_COUNT, DOMAIN, SCAN_INTERVAL, RelayConfig
from .kmtronic import KMTronicError, KMTronicUSB

_LOGGER = logging.getLogger(__name__)

type KMTronicConfigEntry = ConfigEntry[KMTronicCoordinator]


class KMTronicCoordinator(DataUpdateCoordinator[list[bool]]):
    """Poll the relay states and send commands to the board."""

    config_entry: KMTronicConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: KMTronicConfigEntry, board: KMTronicUSB
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.board = board
        self.relay_count: int = entry.data[CONF_RELAY_COUNT]

    async def _async_update_data(self) -> list[bool]:
        try:
            return await self.hass.async_add_executor_job(self.board.get_states)
        except KMTronicError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
            ) from err

    async def async_set_relay(self, relay: int, on: bool) -> None:
        """Switch a relay (physical state) and refresh all states from the board."""
        try:
            states = await self.hass.async_add_executor_job(
                self.board.set_relay, relay, on
            )
        except KMTronicError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"relay": str(relay), "error": str(err)},
            ) from err
        self.async_set_updated_data(states)

    async def async_pulse(self, config: RelayConfig) -> None:
        """Activate a relay for a while, then release it."""
        active = not config.inverted
        await self.async_set_relay(config.relay, active)
        try:
            await asyncio.sleep(config.pulse_duration)
        finally:
            await self.async_set_relay(config.relay, not active)
