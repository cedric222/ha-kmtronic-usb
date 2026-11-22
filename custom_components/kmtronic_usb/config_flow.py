"""Config flow for the KMTronic USB relay integration."""

from __future__ import annotations

import logging
import os
import re
from typing import Any

import serial.tools.list_ports
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.helpers.service_info.usb import UsbServiceInfo

from .const import (
    CONF_INVERTED,
    CONF_PORT,
    CONF_PULSE_DURATION,
    CONF_RELAY_COUNT,
    CONF_TYPE,
    DEFAULT_RELAY_COUNT,
    DOMAIN,
    RELAY_TYPES,
    RelayConfig,
    relay_section,
)
from .kmtronic import SUPPORTED_RELAY_COUNTS, KMTronicError, KMTronicUSB

_LOGGER = logging.getLogger(__name__)

SERIAL_BY_ID = "/dev/serial/by-id"


def _serial_by_id(device: str) -> str:
    """Return the stable /dev/serial/by-id path of a device, if there is one."""
    if not os.path.isdir(SERIAL_BY_ID):
        return device
    real = os.path.realpath(device)
    for name in sorted(os.listdir(SERIAL_BY_ID)):
        path = os.path.join(SERIAL_BY_ID, name)
        if os.path.realpath(path) == real:
            return path
    return device


def _list_ports() -> dict[str, str]:
    """Return the available serial ports as {path: label}."""
    ports = {}
    for port in serial.tools.list_ports.comports():
        label = port.device
        if port.manufacturer or port.product:
            label += f" - {port.manufacturer or ''} {port.product or ''}".rstrip()
        ports[_serial_by_id(port.device)] = label
    return ports


def _relay_count_from_description(description: str | None) -> int:
    """Guess the relay count from a USB product string such as 'USB 8 Relays'."""
    if description and (match := re.search(r"(\d+)\s*relay", description, re.I)):
        count = int(match.group(1))
        if count in SUPPORTED_RELAY_COUNTS:
            return count
    return DEFAULT_RELAY_COUNT


async def _async_validate(hass: HomeAssistant, port: str, relay_count: int) -> None:
    """Check that a KMTronic board answers on the port."""
    board = KMTronicUSB(port, relay_count)
    try:
        await hass.async_add_executor_job(board.get_states)
    finally:
        await hass.async_add_executor_job(board.close)


def _title(relay_count: int) -> str:
    return f"KMTronic USB {relay_count} relays"


RELAY_COUNT_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[str(count) for count in SUPPORTED_RELAY_COUNTS],
        mode=SelectSelectorMode.DROPDOWN,
    )
)


class KMTronicUSBConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for KMTronic USB relay boards."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._port: str | None = None
        self._relay_count = DEFAULT_RELAY_COUNT

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> KMTronicOptionsFlow:
        """Return the options flow."""
        return KMTronicOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick the serial port."""
        errors: dict[str, str] = {}

        if user_input is not None:
            port = await self.hass.async_add_executor_job(
                _serial_by_id, user_input[CONF_PORT]
            )
            relay_count = int(user_input[CONF_RELAY_COUNT])
            await self.async_set_unique_id(port)
            self._abort_if_unique_id_configured()
            try:
                await _async_validate(self.hass, port, relay_count)
            except KMTronicError as err:
                _LOGGER.debug("Validation of %s failed: %s", port, err)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=_title(relay_count),
                    data={CONF_PORT: port, CONF_RELAY_COUNT: relay_count},
                )

        ports = await self.hass.async_add_executor_job(_list_ports)
        schema = vol.Schema(
            {
                vol.Required(CONF_PORT): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"value": path, "label": label}
                            for path, label in ports.items()
                        ],
                        custom_value=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_RELAY_COUNT, default=str(DEFAULT_RELAY_COUNT)
                ): RELAY_COUNT_SELECTOR,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    async def async_step_usb(self, discovery_info: UsbServiceInfo) -> ConfigFlowResult:
        """Handle a board discovered on USB."""
        port = await self.hass.async_add_executor_job(
            _serial_by_id, discovery_info.device
        )
        await self.async_set_unique_id(port)
        self._abort_if_unique_id_configured(updates={CONF_PORT: port})

        self._port = port
        self._relay_count = _relay_count_from_description(discovery_info.description)
        self.context["title_placeholders"] = {"name": _title(self._relay_count)}
        return await self.async_step_usb_confirm()

    async def async_step_usb_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm the setup of a discovered board."""
        assert self._port is not None
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _async_validate(self.hass, self._port, self._relay_count)
            except KMTronicError as err:
                _LOGGER.debug("Validation of %s failed: %s", self._port, err)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=_title(self._relay_count),
                    data={CONF_PORT: self._port, CONF_RELAY_COUNT: self._relay_count},
                )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="usb_confirm",
            description_placeholders={
                "name": _title(self._relay_count),
                "port": self._port,
            },
            errors=errors,
        )


class KMTronicOptionsFlow(OptionsFlowWithReload):
    """Configure how each relay is exposed in Home Assistant."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show one collapsible section per relay."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        schema: dict[vol.Marker, Any] = {}
        for relay in range(1, self.config_entry.data[CONF_RELAY_COUNT] + 1):
            config = RelayConfig.from_options(self.config_entry.options, relay)
            schema[vol.Required(relay_section(relay))] = section(
                vol.Schema(
                    {
                        vol.Required(CONF_TYPE, default=config.type): SelectSelector(
                            SelectSelectorConfig(
                                options=RELAY_TYPES,
                                translation_key="relay_type",
                                mode=SelectSelectorMode.DROPDOWN,
                            )
                        ),
                        vol.Required(
                            CONF_INVERTED, default=config.inverted
                        ): BooleanSelector(),
                        vol.Required(
                            CONF_PULSE_DURATION, default=config.pulse_duration
                        ): NumberSelector(
                            NumberSelectorConfig(
                                min=0.1,
                                max=60,
                                step=0.1,
                                unit_of_measurement="s",
                                mode=NumberSelectorMode.BOX,
                            )
                        ),
                    }
                ),
                {"collapsed": True},
            )

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))
