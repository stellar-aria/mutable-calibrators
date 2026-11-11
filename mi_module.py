"""Base classes for modules that speak the factory-test protocol."""

from __future__ import annotations

from enum import IntEnum
from time import sleep

from factory_test import DebugPort, calibration_nibbles, channel_step

# Pause before a measurement step so the module's low-pass filtered ADC
# readings settle on the newly applied voltage.
SETTLE_TIME = 1.0


class MIModule:
    NAME = "Module"
    # Each subclass sets this to its firmware's FactoryTestCommand table.
    Command: type[IntEnum]

    def __init__(self, port: str | DebugPort) -> None:
        self.port = port if isinstance(port, DebugPort) else DebugPort(port)

    def request(self, command: IntEnum, argument: int = 0) -> int:
        if not isinstance(command, self.Command):
            raise TypeError(
                f"{command!r} is not a {self.NAME} factory-test command")
        return self.port.request(command, argument)

    def _command(self, name: str) -> IntEnum:
        try:
            return self.Command[name]
        except KeyError:
            raise NotImplementedError(
                f"{self.NAME} firmware has no {name} command") from None

    def read_pot(self, index: int) -> int:
        return self.request(self._command("READ_POT"), index)

    def read_cv(self, index: int) -> int:
        return self.request(self._command("READ_CV"), index)

    def read_gate(self, index: int) -> bool:
        return bool(self.request(self._command("READ_GATE"), index))

    def read_normalization(self, index: int) -> bool:
        return bool(self.request(self._command("READ_NORMALIZATION"), index))

    def calibrate(self, argument: int) -> int:
        return self.request(self._command("CALIBRATE"), argument)

    def close(self) -> None:
        self.port.close()


def compute_dac_calibration(code_a: int, volts_a: float,
                            code_b: int, volts_b: float) -> tuple[float, float]:
    """Fit dac_code = volts * scale + offset through two measured points.
    Returns (scale in codes per volt, offset in codes)."""
    if volts_a == volts_b:
        raise ValueError("The two readings are identical; cannot fit a line")
    scale = (code_b - code_a) / (volts_b - volts_a)
    offset = code_a - volts_a * scale
    return scale, offset


class DacModule(MIModule):
    """Module whose CV outputs are calibrated by forcing two known DAC codes,
    measuring them with a voltmeter, and sending back scale/offset.

    Marbles, Stages and Tides 2 share the same firmware convention: the
    stored per-volt scale is -(high half-word) / 8 and the offset is the low
    half-word. After the store step the output is driven to CHECK_VOLTS."""

    OUTPUTS: tuple[str, ...] = ()
    # DAC codes forced by FORCE_DAC_CODE steps 0 and 1, with the voltage
    # each should roughly produce.
    CODE_LOW = 0x9FF1
    CODE_HIGH = 0x416B
    NOMINAL_LOW_VOLTS = -2.0
    NOMINAL_HIGH_VOLTS = 4.0
    CHECK_VOLTS = 1.0
    STORE_STEP = 2

    def force_dac_code(self, channel: int, step: int) -> int:
        return self.request(self._command("FORCE_DAC_CODE"),
                            channel_step(channel, step))

    def write_dac_calibration(self, channel: int, scale: float,
                              offset: float) -> None:
        """Send scale (codes/volt) and offset for one channel and make the
        module store them."""
        nibble_command = self._command("WRITE_CALIBRATION_DATA_NIBBLE")
        for nibble in calibration_nibbles(round(-8.0 * scale), round(offset)):
            self.request(nibble_command, nibble)
        self.force_dac_code(channel, self.STORE_STEP)

    def firmware_snippet(self, channel: int, scale: float,
                         offset: float) -> str:
        raise NotImplementedError


def settle() -> None:
    sleep(SETTLE_TIME)
