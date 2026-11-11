#!/usr/bin/env python3
"""Plaits calibration (firmware: plaits/ui.cc HandleFactoryTestingRequest)."""

from enum import IntEnum

import cli
from mi_module import MIModule


class Command(IntEnum):
    READ_POT = 0
    READ_CV = 1
    READ_GATE = 2
    GENERATE_TEST_SIGNAL = 3
    CALIBRATE = 4
    READ_NORMALIZATION = 5


class Plaits(MIModule):
    NAME = "Plaits"
    Command = Command

    def set_test_mode(self, enabled: bool) -> None:
        self.request(Command.GENERATE_TEST_SIGNAL, int(enabled))


# Step 0 also selects engine 0 and disables the normalization probe.
STEPS = cli.pitch_steps("V/OCT", 0, "every CV and trigger input")


def calibrate(m: Plaits):
    print("\n== Plaits V/OCT calibration ==")
    m.set_test_mode(False)
    if cli.run_calibration_steps(m, STEPS):
        print("Done. If the LEDs show the error pattern, the 3 V reading was "
              "out of range: check the reference and reflash.")


if __name__ == "__main__":
    cli.main(Plaits, [("c", "calibrate V/OCT input", calibrate)])
