"""Minimal driver for KMTronic USB relay boards.

This module has no Home Assistant dependency so it can be extracted into a
standalone PyPI library later.

Protocol (9600 baud, 8N1), relays are numbered from 1:
    FF 0N 01  -> relay N on
    FF 0N 00  -> relay N off
    FF 09 00  -> status of all relays (4 and 8 relay boards),
                 reply is one byte per relay (01 = on, 00 = off)
    FF 0N 03  -> status of relay N (1 and 2 relay boards),
                 reply is FF 0N xx
"""

from __future__ import annotations

import contextlib
import threading

import serial

BAUDRATE = 9600
HEADER = 0xFF
CMD_OFF = 0x00
CMD_ON = 0x01
CMD_STATUS_SINGLE = 0x03
CMD_STATUS_ALL = 0x09

SUPPORTED_RELAY_COUNTS = (1, 2, 4, 8)


class KMTronicError(Exception):
    """Raised when the relay board cannot be reached or answers garbage."""


class KMTronicUSB:
    """Blocking, thread-safe driver for one KMTronic USB relay board.

    The serial port is opened lazily and kept open. After any I/O error it is
    closed and will be reopened on the next call, so unplug/replug recovers.
    """

    def __init__(self, port: str, relay_count: int = 8, timeout: float = 1.0) -> None:
        if relay_count not in SUPPORTED_RELAY_COUNTS:
            raise ValueError(f"Unsupported relay count: {relay_count}")
        self.port = port
        self.relay_count = relay_count
        self._timeout = timeout
        self._serial: serial.Serial | None = None
        self._lock = threading.Lock()

    def get_states(self) -> list[bool]:
        """Return the state of every relay, index 0 being relay 1."""
        with self._lock:
            return self._get_states()

    def set_relay(self, relay: int, on: bool) -> list[bool]:
        """Switch one relay and return the states read back from the board."""
        self._check_relay(relay)
        with self._lock:
            self._transaction(bytes([HEADER, relay, CMD_ON if on else CMD_OFF]))
            return self._get_states()

    def close(self) -> None:
        """Close the serial port."""
        with self._lock:
            self._close()

    def _check_relay(self, relay: int) -> None:
        if not 1 <= relay <= self.relay_count:
            raise ValueError(f"Relay must be between 1 and {self.relay_count}")

    def _get_states(self) -> list[bool]:
        if self.relay_count >= 4:
            reply = self._transaction(
                bytes([HEADER, CMD_STATUS_ALL, 0x00]), self.relay_count
            )
            return [byte == CMD_ON for byte in reply]

        states = []
        for relay in range(1, self.relay_count + 1):
            reply = self._transaction(bytes([HEADER, relay, CMD_STATUS_SINGLE]), 3)
            if reply[0] != HEADER or reply[1] != relay:
                self._close()
                raise KMTronicError(f"Unexpected status reply: {reply.hex(' ')}")
            states.append(reply[2] == CMD_ON)
        return states

    def _open(self) -> serial.Serial:
        if self._serial is None or not self._serial.is_open:
            try:
                self._serial = serial.Serial(
                    self.port,
                    baudrate=BAUDRATE,
                    timeout=self._timeout,
                    write_timeout=self._timeout,
                    exclusive=True,
                )
            except (serial.SerialException, OSError, ValueError) as err:
                self._serial = None
                raise KMTronicError(f"Cannot open {self.port}: {err}") from err
        return self._serial

    def _close(self) -> None:
        if self._serial is not None:
            with contextlib.suppress(serial.SerialException, OSError):
                self._serial.close()
            self._serial = None

    def _transaction(self, command: bytes, reply_length: int = 0) -> bytes:
        """Send a command and read a fixed-length reply. Lock must be held."""
        ser = self._open()
        try:
            if reply_length:
                ser.reset_input_buffer()
            ser.write(command)
            ser.flush()
            reply = ser.read(reply_length) if reply_length else b""
        except (serial.SerialException, OSError) as err:
            self._close()
            raise KMTronicError(f"Communication error on {self.port}: {err}") from err

        if len(reply) != reply_length:
            # Lost sync or board not answering: start from a clean port next time.
            self._close()
            raise KMTronicError(
                f"Expected {reply_length} bytes from {self.port}, got {len(reply)}"
            )
        return reply
