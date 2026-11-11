#!/usr/bin/env python3
"""Warps calibration (firmware: warps/ui.cc HandleFactoryTestingRequest).

The LEVEL 1 CV input doubles as the internal oscillator's V/OCT input, so
that is the jack being calibrated.
"""

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


class Warps(MIModule):
    NAME = "Warps"
    Command = Command


STEPS = cli.pitch_steps("the LEVEL 1 CV input", 0, "every CV input") + [
    # LEVEL 1/2 CV normalization-probe thresholds: probe low, then high.
    Step(3, "Unpatch LEVEL 1 CV (leave everything unpatched).", settle=False),
    Step(4),
    Step(5),
]


def calibrate(m: Warps):
    print("\n== Warps LEVEL 1 V/OCT and normalization calibration ==")
    if cli.run_calibration_steps(m, STEPS):
        print("Done. If the LEDs show the calibration error pattern, a "
              "reading was out of range: check the reference and reflash.")


if __name__ == "__main__":
    cli.main(Warps, [("c", "calibrate V/OCT input and normalization", calibrate)])
