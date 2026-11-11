#!/usr/bin/env python3
"""Elements calibration (firmware: elements/ui.cc HandleFactoryTestingRequest)."""

from enum import IntEnum

import cli
from mi_module import MIModule


class Command(IntEnum):
    READ_POT = 0
    READ_CV = 1
    READ_GATE = 2
    SET_BYPASS = 3
    CALIBRATE = 4


class Elements(MIModule):
    NAME = "Elements"
    Command = Command


STEPS = cli.pitch_steps("V/OCT", 0, "every CV input")


def calibrate(m: Elements):
    print("\n== Elements V/OCT calibration ==")
    if cli.run_calibration_steps(m, STEPS):
        print("Done. If the LEDs show the error pattern, the 3 V reading was "
              "out of range: check the reference and reflash.")


if __name__ == "__main__":
    cli.main(Elements, [("c", "calibrate V/OCT input", calibrate)])
