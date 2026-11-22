"""Tests for the KMTronic USB relay entities and setup."""

from __future__ import annotations

import pytest
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

OPTIONS = {
    "relay_1": {"type": "light", "inverted": False, "pulse_duration": 1.0},
    "relay_3": {"type": "button", "inverted": False, "pulse_duration": 0.1},
    "relay_5": {"type": "switch", "inverted": True, "pulse_duration": 1.0},
    "relay_8": {"type": "disabled", "inverted": False, "pulse_duration": 1.0},
}


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_default_setup(hass: HomeAssistant, board, config_entry) -> None:
    """Test every relay is a switch by default and reflects the board state."""
    board.relays[1] = True  # relay 2 is already on: no reset at startup
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED

    assert len(hass.states.async_entity_ids(SWITCH_DOMAIN)) == 8
    assert hass.states.get("switch.kmtronic_usb_8_relays_relay_1").state == STATE_OFF
    assert hass.states.get("switch.kmtronic_usb_8_relays_relay_2").state == STATE_ON
    assert board.commands == []

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.kmtronic_usb_8_relays_relay_1"},
        blocking=True,
    )
    assert board.commands == [(1, True)]
    assert hass.states.get("switch.kmtronic_usb_8_relays_relay_1").state == STATE_ON

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_relay_types(hass: HomeAssistant, board) -> None:
    """Test lights, buttons, inverted switches and disabled relays."""
    from .conftest import PORT

    entry = MockConfigEntry(
        domain="kmtronic_usb",
        title="KMTronic USB 8 relays",
        unique_id=PORT,
        data={"port": PORT, "relay_count": 8},
        options=OPTIONS,
    )
    await _setup(hass, entry)

    assert hass.states.async_entity_ids(LIGHT_DOMAIN) == [
        "light.kmtronic_usb_8_relays_relay_1"
    ]
    assert hass.states.async_entity_ids(BUTTON_DOMAIN) == [
        "button.kmtronic_usb_8_relays_relay_3"
    ]
    assert len(hass.states.async_entity_ids(SWITCH_DOMAIN)) == 5
    assert hass.states.get("switch.kmtronic_usb_8_relays_relay_8") is None

    # Inverted (NC): relay released means on.
    inverted = "switch.kmtronic_usb_8_relays_relay_5"
    assert hass.states.get(inverted).state == STATE_ON
    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: inverted}, blocking=True
    )
    assert board.commands[-1] == (5, True)
    assert hass.states.get(inverted).state == STATE_OFF

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "light.kmtronic_usb_8_relays_relay_1"},
        blocking=True,
    )
    assert board.commands[-1] == (1, True)

    board.commands.clear()
    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: "button.kmtronic_usb_8_relays_relay_3"},
        blocking=True,
    )
    assert board.commands == [(3, True), (3, False)]


async def test_options_change_type(hass: HomeAssistant, board, config_entry) -> None:
    """Test changing a relay type replaces its entity."""
    await _setup(hass, config_entry)
    registry = er.async_get(hass)
    assert registry.async_get("switch.kmtronic_usb_8_relays_relay_4")

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["step_id"] == "init"
    user_input = {
        f"relay_{n}": {"type": "switch", "inverted": False, "pulse_duration": 1.0}
        for n in range(1, 9)
    }
    user_input["relay_4"]["type"] = "light"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input
    )
    await hass.async_block_till_done()

    assert config_entry.options["relay_4"]["type"] == "light"
    assert registry.async_get("switch.kmtronic_usb_8_relays_relay_4") is None
    assert hass.states.get("light.kmtronic_usb_8_relays_relay_4").state == STATE_OFF


async def test_board_unreachable(hass: HomeAssistant, board, config_entry) -> None:
    """Test entities become unavailable and commands raise when the board is gone."""
    await _setup(hass, config_entry)
    entity_id = "switch.kmtronic_usb_8_relays_relay_1"

    # The board stops answering while a command is sent.
    board.fail = True
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True
        )

    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE

    board.fail = False
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_OFF


async def test_setup_retry_when_board_missing(
    hass: HomeAssistant, board, config_entry
) -> None:
    """Test setup is retried when the board does not answer."""
    board.fail = True
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
