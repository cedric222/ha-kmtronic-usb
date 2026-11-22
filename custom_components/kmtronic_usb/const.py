"""Constants for the KMTronic USB relay integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Final

DOMAIN: Final = "kmtronic_usb"

CONF_PORT: Final = "port"
CONF_RELAY_COUNT: Final = "relay_count"

CONF_TYPE: Final = "type"
CONF_INVERTED: Final = "inverted"
CONF_PULSE_DURATION: Final = "pulse_duration"

TYPE_SWITCH: Final = "switch"
TYPE_LIGHT: Final = "light"
TYPE_BUTTON: Final = "button"
TYPE_DISABLED: Final = "disabled"
RELAY_TYPES: Final = [TYPE_SWITCH, TYPE_LIGHT, TYPE_BUTTON, TYPE_DISABLED]

DEFAULT_RELAY_COUNT: Final = 8
DEFAULT_PULSE_DURATION: Final = 1.0

SCAN_INTERVAL: Final = timedelta(seconds=10)


def relay_section(relay: int) -> str:
    """Return the options key holding the settings of a relay."""
    return f"relay_{relay}"


@dataclass(frozen=True, slots=True)
class RelayConfig:
    """User settings of one relay."""

    relay: int
    type: str = TYPE_SWITCH
    inverted: bool = False
    pulse_duration: float = DEFAULT_PULSE_DURATION

    @classmethod
    def from_options(cls, options: dict[str, Any], relay: int) -> RelayConfig:
        """Build the settings of a relay from the config entry options."""
        raw = options.get(relay_section(relay), {})
        return cls(
            relay=relay,
            type=raw.get(CONF_TYPE, TYPE_SWITCH),
            inverted=raw.get(CONF_INVERTED, False),
            pulse_duration=float(raw.get(CONF_PULSE_DURATION, DEFAULT_PULSE_DURATION)),
        )
