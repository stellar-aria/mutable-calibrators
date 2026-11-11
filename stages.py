#!/usr/bin/env python3
"""Stages calibration (firmware: stages/factory_test.cc).

Stages has no dedicated debug header: the factory-test UART is the *left*
chaining link (SERIAL_LINK_DIRECTION_LEFT), 9600 baud.
"""

import sys
from enum import IntEnum

import cli
from cli import Step
from factory_test import channel_step
from kbhit import KBHit
from mi_module import DacModule

NUM_CHANNELS = 6


class Command(IntEnum):
    READ_POT = 0
    READ_CV = 1
    READ_GATE = 2
    GENERATE_TEST_SIGNALS = 3
    CALIBRATE = 4
    READ_NORMALIZATION = 5
    FORCE_DAC_CODE = 6
    WRITE_CALIBRATION_DATA_NIBBLE = 7


class Stages(DacModule):
    NAME = "Stages"
    Command = Command
    OUTPUTS = tuple(f"output {i + 1}" for i in range(NUM_CHANNELS))
    CODE_LOW = 0x9FF1   # ~ -2 V
    CODE_HIGH = 0x416B  # ~ +4 V

    def read_slider(self, channel: int) -> int:
        return self.read_pot(channel + NUM_CHANNELS)  # sliders follow pots

    def read_button(self, channel: int) -> bool:
        return self.read_gate(channel + NUM_CHANNELS)  # buttons follow gates

    def clear_forced_outputs(self) -> None:
        self.request(Command.GENERATE_TEST_SIGNALS, 0)

    def firmware_snippet(self, channel, scale, offset):
        # Stages' dac_code() takes level = volts / 8, so its scale is 8x.
        c = f"persistent_data_.channel_calibration_data[{channel}]"
        return (f"{c}.dac_scale = {8 * scale:.4f}f; "
                f"{c}.dac_offset = {offset:.4f}f;")

    def get_state(self) -> list[list[str]]:
        rows = [
            ("Pots", self.read_pot), ("Sliders", self.read_slider),
            ("Buttons", self.read_button), ("Gates", self.read_gate),
            ("Normals", self.read_normalization), ("CVs", self.read_cv),
        ]
        return [[name] + [str(int(read(i))) for i in range(NUM_CHANNELS)]
                for name, read in rows]


def adc_steps() -> list[Step]:
    # Per channel: 0 = all outputs to -1 V, 1 = sample and go to +2 V,
    # 2 = sample, validate and save (the channel's slider LED lights up).
    steps = [Step(channel_step(c, s)) for c in range(NUM_CHANNELS)
             for s in range(3)]
    steps[0] = Step(steps[0].argument,
                    "Patch each output to the TIME/LEVEL input of its own "
                    "channel (output 1 -> input 1, ... output 6 -> input 6).")
    return steps


def calibrate_dac(m: Stages):
    def start():
        m.clear_forced_outputs()
        print("Each channel's slider LED lights once its calibration is "
              "stored.")
    cli.calibrate_dac(m, before=start)


def calibrate_adc(m: Stages):
    print("\n== Stages CV input calibration ==")
    print("Uses the module's own outputs as the reference, so run the DAC "
          "calibration first.")
    if cli.run_calibration_steps(m, adc_steps()):
        print("Done. Any channel whose slider LED did not light up was out "
              "of range; check its patch cable.")


def calibrate_all(m: Stages):
    calibrate_dac(m)
    calibrate_adc(m)


def generate_test_signals(m: Stages):
    m.clear_forced_outputs()
    print("Outputs now play the factory test waveforms.")


def display(m: Stages):
    header = ["Channel"] + [str(c + 1) for c in range(NUM_CHANNELS)]
    print("Press ESC or 'q' to return to the menu.")
    kb = KBHit()
    try:
        first = True
        while True:
            if kb.kbhit() and kb.getch() in ("\x1b", "q"):
                break
            lines = ["\t".join(row) for row in [header] + m.get_state()]
            if not first:
                # Move the cursor back up over the previous table.
                sys.stdout.write("\x1b[1A\x1b[2K" * len(lines))
            sys.stdout.write("".join(line + "\n" for line in lines))
            sys.stdout.flush()
            first = False
    finally:
        kb.set_normal_term()


if __name__ == "__main__":
    cli.main(Stages, [
        ("c", "calibrate DAC, then CV inputs", calibrate_all),
        ("d", "calibrate DAC (outputs) only", calibrate_dac),
        ("a", "calibrate CV inputs only", calibrate_adc),
        ("g", "generate test signals", generate_test_signals),
        ("r", "show live pot/slider/button/gate/CV readings", display),
    ])
