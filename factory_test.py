"""Mutable Instruments factory-test UART protocol.

Every request is a single byte: the top 3 bits are the opcode and the bottom
5 bits are the argument. The module answers *every* request with exactly one
byte (polled from SysTick at ~1 kHz), so the host must read that reply before
sending the next request, otherwise stale replies pile up in the receive
buffer and later reads return the answer to an earlier question.

Opcode numbering is NOT shared between modules (e.g. opcode 3 is
GENERATE_TEST_SIGNALS on Marbles but SET_BYPASS on Rings), so each module
defines its own command table; see mi_module.py and the per-module scripts.

All modules talk 8N1 at 9600 baud and only enable the port when "freshly
baked" (first boot after flashing, before any settings were saved).
"""

from __future__ import annotations

import serial

BAUD_RATE = 9600
DEFAULT_TIMEOUT = 1.0

OPCODE_SHIFT = 5
ARGUMENT_MASK = 0x1F
MAX_OPCODE = 0x07


class ProtocolError(IOError):
    """The module did not answer, or answered something unusable."""


def pack_request(opcode: int, argument: int) -> bytes:
    if not 0 <= opcode <= MAX_OPCODE:
        raise ValueError(f"opcode {opcode} does not fit in 3 bits")
    if not 0 <= argument <= ARGUMENT_MASK:
        raise ValueError(f"argument {argument} does not fit in 5 bits")
    return bytes([(opcode << OPCODE_SHIFT) | argument])


def channel_step(channel: int, step: int) -> int:
    """Argument encoding used by FORCE_DAC_CODE (and Stages' CALIBRATE):
    channel in bits 2-4, step in bits 0-1."""
    if not 0 <= step <= 3:
        raise ValueError(f"step {step} does not fit in 2 bits")
    if not 0 <= channel <= 7:
        raise ValueError(f"channel {channel} does not fit in 3 bits")
    return (channel << 2) | step


def calibration_nibbles(scale_magnitude: int, offset: int) -> list[int]:
    """Split a DAC calibration into the 8 nibbles (MSB first) that the
    firmware shifts into its 32-bit `calibration_data_` accumulator.
    High half-word is the (positive) scale magnitude, low half-word the
    offset; the firmware negates the scale when it stores it."""
    for name, value in (("scale", scale_magnitude), ("offset", offset)):
        if not 0 <= value <= 0xFFFF:
            raise ValueError(
                f"DAC {name} {value} is outside 0..65535; check the "
                "voltmeter readings (volts, correct sign)")
    word = (scale_magnitude << 16) | offset
    return [(word >> shift) & 0xF for shift in range(28, -1, -4)]


class DebugPort:
    def __init__(self, port: str | serial.SerialBase,
                 timeout: float = DEFAULT_TIMEOUT) -> None:
        if isinstance(port, str):
            self.serial = serial.Serial(port, BAUD_RATE, timeout=timeout)
        else:
            self.serial = port

    def request(self, opcode: int, argument: int = 0) -> int:
        """Send one request and return the module's one-byte reply."""
        packet = pack_request(int(opcode), argument)
        # Drop anything left over (boot noise, a reply that arrived after a
        # previous timeout) so the reply we read belongs to this request.
        self.serial.reset_input_buffer()
        self.serial.write(packet)
        reply = self.serial.read(1)
        if len(reply) != 1:
            raise ProtocolError(
                "No answer from module. Check power, RX/TX/GND wiring, and "
                "that the module is freshly flashed.")
        return reply[0]

    def close(self) -> None:
        self.serial.close()

    def __enter__(self) -> DebugPort:
        return self

    def __exit__(self, *exc) -> None:
        self.close()
