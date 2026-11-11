#!/usr/bin/env python3
"""Rings calibration (firmware: rings/ui.cc HandleFactoryTestingRequest)."""

from enum import IntEnum

import cli
from cli import Step
from mi_module import MIModule


class Command(IntEnum):
    READ_POT = 0
    READ_CV = 1
    READ_GATE = 2
    SET_BYPASS = 3
    CALIBRATE = 4
    READ_NORMALIZATION = 5


class Rings(MIModule):
    NAME = "Rings"
    Command = Command


STEPS = cli.pitch_steps("V/OCT", 0, "every CV input") + [
    # V/OCT normalization-probe threshold: probe forced low, then high.
    Step(3, "Unpatch V/OCT (leave everything unpatched).", settle=False),
    Step(4),
    Step(5),
]


def calibrate(m: Rings):
    print("\n== Rings V/OCT and normalization calibration ==")
    if cli.run_calibration_steps(m, STEPS):
        print("Done. If the LEDs show the error pattern, a reading was out "
              "of range: check the reference and reflash.")


if __name__ == "__main__":
    cli.main(Rings, [("c", "calibrate V/OCT input and normalization", calibrate)])
