"""Fixtures for the KMTronic USB relay tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kmtronic_usb.const import CONF_PORT, CONF_RELAY_COUNT, DOMAIN
from custom_components.kmtronic_usb.kmtronic import KMTronicError

PORT = "/dev/serial/by-id/usb-KMtronic_Ltd._USB_8_Relays-if00"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations in every test."""


class FakeKMTronicUSB:
    """In-memory replacement of the serial driver."""

    relays: list[bool] = []
    fail = False
    commands: list[tuple[int, bool]] = []

    def __init__(self, port: str, relay_count: int = 8) -> None:
        self.port = port
        self.relay_count = relay_count
        if len(FakeKMTronicUSB.relays) != relay_count:
            FakeKMTronicUSB.relays = [False] * relay_count

    def get_states(self) -> list[bool]:
        if FakeKMTronicUSB.fail:
            raise KMTronicError("no answer")
        return list(FakeKMTronicUSB.relays)

    def set_relay(self, relay: int, on: bool) -> list[bool]:
        if FakeKMTronicUSB.fail:
            raise KMTronicError("no answer")
        FakeKMTronicUSB.commands.append((relay, on))
        FakeKMTronicUSB.relays[relay - 1] = on
        return list(FakeKMTronicUSB.relays)

    def close(self) -> None:
        pass


@pytest.fixture
def board() -> Generator[type[FakeKMTronicUSB]]:
    """Patch the driver everywhere it is used."""
    FakeKMTronicUSB.relays = [False] * 8
    FakeKMTronicUSB.fail = False
    FakeKMTronicUSB.commands = []
    with (
        patch("custom_components.kmtronic_usb.KMTronicUSB", FakeKMTronicUSB),
        patch(
            "custom_components.kmtronic_usb.config_flow.KMTronicUSB", FakeKMTronicUSB
        ),
        patch(
            "custom_components.kmtronic_usb.config_flow._serial_by_id",
            side_effect=lambda device: device,
        ),
    ):
        yield FakeKMTronicUSB


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a config entry for an 8 relay board."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="KMTronic USB 8 relays",
        unique_id=PORT,
        data={CONF_PORT: PORT, CONF_RELAY_COUNT: 8},
    )
