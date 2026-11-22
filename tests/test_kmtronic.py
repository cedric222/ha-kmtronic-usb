"""Tests for the Home Assistant independent KMTronic driver."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest
import serial

_PATH = Path(__file__).parents[1] / "custom_components/kmtronic_usb/kmtronic.py"
_SPEC = importlib.util.spec_from_file_location("kmtronic", _PATH)
kmtronic = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(kmtronic)


class FakeBoard:
    """Emulates the serial protocol of a KMTronic board."""

    def __init__(self, relay_count: int = 8, mute: bool = False) -> None:
        self.relays = [False] * relay_count
        self.mute = mute
        self.written: list[bytes] = []
        self.opened = 0
        self.closed = 0
        self.is_open = False
        self._pending = b""

    def __call__(self, *args, **kwargs) -> FakeBoard:  # acts as serial.Serial
        self.opened += 1
        self.is_open = True
        return self

    def write(self, data: bytes) -> int:
        self.written.append(data)
        header, relay, cmd = data
        assert header == 0xFF
        if self.mute:
            return 3
        if relay == 0x09:
            self._pending = bytes(int(state) for state in self.relays)
        elif cmd == 0x03:
            self._pending = bytes([0xFF, relay, int(self.relays[relay - 1])])
        else:
            self.relays[relay - 1] = cmd == 0x01
        return 3

    def read(self, size: int) -> bytes:
        data, self._pending = self._pending[:size], self._pending[size:]
        return data

    def flush(self) -> None:
        pass

    def reset_input_buffer(self) -> None:
        self._pending = b""

    def close(self) -> None:
        self.closed += 1
        self.is_open = False


@pytest.fixture
def board8():
    fake = FakeBoard(8)
    with patch.object(kmtronic.serial, "Serial", fake):
        yield fake, kmtronic.KMTronicUSB("/dev/fake", 8)


def test_set_and_read_states(board8) -> None:
    fake, board = board8
    assert board.get_states() == [False] * 8
    states = board.set_relay(3, True)
    assert fake.written[-2] == bytes([0xFF, 0x03, 0x01])
    assert states == [False, False, True, False, False, False, False, False]
    assert board.set_relay(3, False) == [False] * 8
    assert fake.opened == 1  # port stays open between commands


def test_relay_out_of_range(board8) -> None:
    _, board = board8
    with pytest.raises(ValueError):
        board.set_relay(0, True)
    with pytest.raises(ValueError):
        board.set_relay(9, True)


def test_single_relay_board_uses_per_relay_status() -> None:
    fake = FakeBoard(2)
    with patch.object(kmtronic.serial, "Serial", fake):
        board = kmtronic.KMTronicUSB("/dev/fake", 2)
        assert board.set_relay(2, True) == [False, True]
    assert bytes([0xFF, 0x02, 0x03]) in fake.written


def test_no_answer_closes_port() -> None:
    fake = FakeBoard(8, mute=True)
    with patch.object(kmtronic.serial, "Serial", fake):
        board = kmtronic.KMTronicUSB("/dev/fake", 8)
        with pytest.raises(kmtronic.KMTronicError):
            board.get_states()
        assert fake.closed == 1
        fake.mute = False
        assert board.get_states() == [False] * 8
        assert fake.opened == 2  # reopened after the failure


def test_open_failure() -> None:
    def fail(*args, **kwargs):
        raise serial.SerialException("no such device")

    with (
        patch.object(kmtronic.serial, "Serial", fail),
        pytest.raises(kmtronic.KMTronicError),
    ):
        kmtronic.KMTronicUSB("/dev/missing", 8).get_states()


def test_unsupported_relay_count() -> None:
    with pytest.raises(ValueError):
        kmtronic.KMTronicUSB("/dev/fake", 3)
