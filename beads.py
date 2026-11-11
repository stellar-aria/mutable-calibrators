#!/usr/bin/env python3
"""Beads calibration (firmware: beads/factory_test.cc).

CALIBRATE arguments 0-2 are addressed to the CV generator of the factory
test bench and ignored by the module; 3-7 run the calibration below. Unlike
the other modules, Beads replies 1/0 to report whether each step succeeded.
"""

from enum import IntEnum

import cli
from cli import Step, reference_voltage_prompt
from mi_module import MIModule


class Command(IntEnum):
    READ_POT = 0
    READ_CV = 1
    READ_GATE = 2
    GENERATE_TEST_SIGNALS = 3
    CALIBRATE = 4
    READ_NORMALIZATION = 5


class Beads(MIModule):
    NAME = "Beads"
    Command = Command


STEPS = [
    Step(3, "Unpatch every input.", settle=False, reports_success=True),
    # Step 4 also captures the zero of every other CV input.
    Step(4, reference_voltage_prompt(1.0, "the V/OCT input"),
         reports_success=True),
    Step(5, reference_voltage_prompt(3.0, "the V/OCT input"),
         reports_success=True),
    Step(6, "Unpatch V/OCT. " + reference_voltage_prompt(1.0, "DENSITY CV"),
         reports_success=True),
    Step(7, reference_voltage_prompt(3.0, "DENSITY CV"),
         reports_success=True),  # saves on success
]


def calibrate(m: Beads):
    print("\n== Beads V/OCT and DENSITY calibration ==")
    if cli.run_calibration_steps(m, STEPS):
        print("Done. Calibration saved.")


if __name__ == "__main__":
    cli.main(Beads, [("c", "calibrate V/OCT and DENSITY inputs", calibrate)])
