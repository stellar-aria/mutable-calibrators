#!/usr/bin/env python3
"""Marbles calibration (firmware: marbles/ui.cc HandleFactoryTestingRequest)."""

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


class Marbles(DacModule):
    NAME = "Marbles"
    Command = Command
    # cv_output index order (marbles.cc remaps the generator: [0] is Y).
    OUTPUTS = ("Y", "X1", "X2", "X3")
    CODE_LOW = 0xAF35   # ~ -2 V
    CODE_HIGH = 0x1D98  # ~ +4 V

    def generate_test_signals(self, enabled: bool = True) -> None:
        """Enter output test mode (required for forced DAC codes to reach the
        outputs) and clear any forced codes."""
        self.request(Command.GENERATE_TEST_SIGNALS, int(enabled))

    def firmware_snippet(self, channel, scale, offset):
        return (f"c.dac_scale[{channel}] = {scale:.4f}f; "
                f"c.dac_offset[{channel}] = {offset:.4f}f;")


# CALIBRATE 0 enters calibration and drives every output to 1 V; each later
# step samples an input and toggles the outputs between 3 V and 1 V.
ADC_STEPS = [
    Step(0, "Unpatch every input, then patch any output to T RATE and "
            "another output to X SPREAD.", settle=False),
    Step(1),  # offsets + T RATE @ 1 V   -> outputs 3 V
    Step(2),  # T RATE @ 3 V             -> outputs 1 V
    Step(3),  # X SPREAD @ 1 V           -> outputs 3 V
    Step(4),  # X SPREAD @ 3 V, validate and save
]


def calibrate_dac(m: Marbles):
    def start():
        m.generate_test_signals(True)
        cli.pause("All outputs should now show orange LEDs.")
    cli.calibrate_dac(m, before=start)


def calibrate_adc(m: Marbles):
    print("\n== Marbles CV input calibration ==")
    print("Uses the module's own outputs as the reference, so run the DAC "
          "calibration first.")
    m.generate_test_signals(True)
    if cli.run_calibration_steps(m, ADC_STEPS):
        print("Done. If the LEDs show the error pattern, a reading was out of "
              "range: check the patching and reflash.")


def calibrate_all(m: Marbles):
    calibrate_dac(m)
    calibrate_adc(m)


if __name__ == "__main__":
    cli.main(Marbles, [
        ("m", "calibrate DAC, then CV inputs", calibrate_all),
        ("d", "calibrate DAC (outputs) only", calibrate_dac),
        ("a", "calibrate CV inputs only", calibrate_adc),
    ])
