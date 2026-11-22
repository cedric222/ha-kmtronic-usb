"""Tests for the KMTronic USB relay config flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USB, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.usb import UsbServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kmtronic_usb.const import CONF_PORT, CONF_RELAY_COUNT, DOMAIN

from .conftest import PORT

USB_INFO = UsbServiceInfo(
    device=PORT,
    vid="04D8",
    pid="F55E",
    serial_number=None,
    manufacturer="KMtronic Ltd.",
    description="USB 8 Relays",
)


async def test_user_flow(hass: HomeAssistant, board) -> None:
    """Test a successful manual setup."""
    with patch(
        "custom_components.kmtronic_usb.config_flow._list_ports",
        return_value={PORT: "/dev/ttyACM3 - KMtronic Ltd. USB 8 Relays"},
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM

    with patch("custom_components.kmtronic_usb.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PORT: PORT, CONF_RELAY_COUNT: "8"}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "KMTronic USB 8 relays"
    assert result["data"] == {CONF_PORT: PORT, CONF_RELAY_COUNT: 8}
    assert result["result"].unique_id == PORT


async def test_user_flow_cannot_connect(hass: HomeAssistant, board) -> None:
    """Test an error is shown when the board does not answer, then recovery."""
    board.fail = True
    with patch(
        "custom_components.kmtronic_usb.config_flow._list_ports", return_value={}
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PORT: PORT, CONF_RELAY_COUNT: "8"}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    board.fail = False
    with patch("custom_components.kmtronic_usb.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PORT: PORT, CONF_RELAY_COUNT: "8"}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_already_configured(
    hass: HomeAssistant, board, config_entry: MockConfigEntry
) -> None:
    """Test the same board cannot be added twice."""
    config_entry.add_to_hass(hass)
    with patch(
        "custom_components.kmtronic_usb.config_flow._list_ports", return_value={}
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PORT: PORT, CONF_RELAY_COUNT: "8"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_usb_discovery(hass: HomeAssistant, board) -> None:
    """Test setup from USB discovery, relay count guessed from the product."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USB}, data=USB_INFO
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "usb_confirm"

    with patch("custom_components.kmtronic_usb.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_PORT: PORT, CONF_RELAY_COUNT: 8}


async def test_usb_discovery_already_configured(
    hass: HomeAssistant, board, config_entry: MockConfigEntry
) -> None:
    """Test a configured board is not rediscovered."""
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USB}, data=USB_INFO
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
