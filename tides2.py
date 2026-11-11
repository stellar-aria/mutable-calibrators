#!/usr/bin/env python3
"""Tides (2018) calibration (firmware: tides2/factory_test.cc)."""

from enum import IntEnum

import cli
from cli import Step
from mi_module import DacModule


class Command(IntEnum):
    READ_POT = 0
    READ_CV = 1
    READ_GATE = 2
    GENERATE_TEST_SIGNALS = 3
    CALIBRATE = 4
    READ_NORMALIZATION = 5
    FORCE_DAC_CODE = 6
    WRITE_CALIBRATION_DATA_NIBBLE = 7


class Tides2(DacModule):
    NAME = "Tides 2"
    Command = Command
    OUTPUTS = ("OUT 1", "OUT 2", "OUT 3", "OUT 4")
    CODE_LOW = 0x9FF1   # ~ -2 V
    CODE_HIGH = 0x416B  # ~ +4 V

    def clear_forced_outputs(self) -> None:
        """GENERATE_TEST_SIGNALS clears every forced DAC code (the argument is
        ignored); the outputs go back to the factory test waveforms."""
        self.request(Command.GENERATE_TEST_SIGNALS, 0)

    def firmware_snippet(self, channel, scale, offset):
        return (f"persistent_data_.dac_calibration[{channel}].scale = "
                f"{scale:.4f}f; persistent_data_.dac_calibration[{channel}]"
                f".offset = {offset:.4f}f;")


# OUT 1 is driven to -2 V then +4 V and read back on V/OCT. Step 1 also
# captures the zero of every other CV input, so those must be unpatched.
ADC_STEPS = [
    Step(0, "Patch OUT 1 to the V/OCT input and unpatch every other CV "
            "input.", settle=False),
    Step(1),
    Step(2),
]


def calibrate_dac(m: Tides2):
    cli.calibrate_dac(m, before=m.clear_forced_outputs)


def calibrate_adc(m: Tides2):
    print("\n== Tides 2 V/OCT calibration ==")
    print("Uses OUT 1 as the reference, so run the DAC calibration first.")
    if cli.run_calibration_steps(m, ADC_STEPS):
        print("Done.")


def calibrate_all(m: Tides2):
    calibrate_dac(m)
    calibrate_adc(m)


if __name__ == "__main__":
    cli.main(Tides2, [
        ("m", "calibrate DAC, then V/OCT input", calibrate_all),
        ("d", "calibrate DAC (outputs) only", calibrate_dac),
        ("a", "calibrate V/OCT input only", calibrate_adc),
    ])
