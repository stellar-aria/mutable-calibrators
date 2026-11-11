"""Shared interactive plumbing for the per-module calibration scripts."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable, Sequence

from factory_test import ProtocolError
from mi_module import DacModule, MIModule, compute_dac_calibration, settle

# A reading further than this from its nominal value is probably a typo
# (millivolts, wrong sign, wrong output) and is double-checked.
SUSPICIOUS_DEVIATION_VOLTS = 0.5


def pause(message: str) -> None:
    input(f"{message} Press ENTER to continue.")


def confirm(message: str) -> bool:
    return input(f"{message} [y/N] ").strip().lower() in ("y", "yes")


def ask_volts(prompt: str, nominal: float) -> float:
    while True:
        text = input(f"{prompt} (should be close to {nominal:+g} V): ")
        try:
            value = float(text.strip().replace(",", "."))
        except ValueError:
            print(f"  '{text}' is not a number; enter the reading in volts.")
            continue
        if abs(value - nominal) > SUSPICIOUS_DEVIATION_VOLTS and not confirm(
                f"  {value:+g} V is far from {nominal:+g} V. Use it anyway?"):
            continue
        return value


# --- DAC (output) calibration --------------------------------------------

def calibrate_dac_channel(module: DacModule, channel: int) -> tuple[float, float]:
    name = module.OUTPUTS[channel]
    while True:
        module.force_dac_code(channel, 0)
        v_low = ask_volts(f"Voltmeter reading on {name}",
                          module.NOMINAL_LOW_VOLTS)
        module.force_dac_code(channel, 1)
        v_high = ask_volts(f"Voltmeter reading on {name}",
                           module.NOMINAL_HIGH_VOLTS)
        scale, offset = compute_dac_calibration(
            module.CODE_LOW, v_low, module.CODE_HIGH, v_high)
        try:
            module.write_dac_calibration(channel, scale, offset)
        except ValueError as e:
            print(f"  {e}. Measuring {name} again.")
            continue
        if confirm(f"{name} should now read {module.CHECK_VOLTS:+g} V. "
                   "Does it?"):
            return scale, offset
        print(f"  Measuring {name} again.")


def calibrate_dac(module: DacModule, before: Callable[[], None] | None = None
                  ) -> list[tuple[float, float]]:
    print(f"\n== {module.NAME} DAC calibration ==")
    print("Measure each output with a voltmeter (a 4.5-digit meter or better "
          "is recommended) and type the readings in volts.")
    if before:
        before()
    data = [calibrate_dac_channel(module, ch)
            for ch in range(len(module.OUTPUTS))]
    print("DAC calibrated and stored.")
    print("To bake these values into the firmware instead, add to "
          "Settings::Init():")
    for ch, (scale, offset) in enumerate(data):
        print("  " + module.firmware_snippet(ch, scale, offset))
    return data


# --- ADC (input) calibration ---------------------------------------------

@dataclass(frozen=True)
class Step:
    """One CALIBRATE request.

    instructions: shown to the user before the step (they press ENTER).
    settle: wait for filtered ADC readings to settle before sending.
    reports_success: the firmware replies 1 on success / 0 on failure."""
    argument: int
    instructions: str | None = None
    settle: bool = True
    reports_success: bool = False


def run_calibration_steps(module: MIModule, steps: Sequence[Step]) -> bool:
    for step in steps:
        if step.instructions:
            pause(step.instructions)
        if step.settle:
            settle()
        reply = module.calibrate(step.argument)
        if step.reports_success and not reply:
            print(f"The module rejected calibration step {step.argument}: the "
                  "measured value was out of range. Check the patching and "
                  "the reference voltage, then start over.")
            return False
    return True


# --- Entry point ---------------------------------------------------------

FRESHLY_FLASHED_WARNING = (
    "The factory-test port is only open on a *freshly flashed* module (its "
    "first power-up after flashing, before any settings were saved). Once a "
    "calibration has been stored the module is no longer freshly flashed, so "
    "do every calibration you need in this one session.")

Action = tuple[str, str, Callable[[MIModule], object]]


def main(module_cls: type[MIModule], actions: Sequence[Action],
         argv: Sequence[str] = sys.argv) -> None:
    port = argv[1] if len(argv) > 1 else input("Serial port: ").strip()
    print(f"Connecting to {module_cls.NAME} on {port}...")
    try:
        module = module_cls(port)
    except Exception as e:  # serial.SerialException, OSError, ...
        sys.exit(f"Unable to open {port}: {e}")

    print(FRESHLY_FLASHED_WARNING)
    by_key = {key: (label, fn) for key, label, fn in actions}
    try:
        while True:
            print(f"\n{module_cls.NAME}: what would you like to do?")
            for key, label, _ in actions:
                print(f"  {key} - {label}")
            print("  q - quit")
            choice = input(">>> ").strip().lower()
            if choice in ("q", "quit"):
                break
            if choice not in by_key:
                print(f"Unknown choice '{choice}'.")
                continue
            try:
                by_key[choice][1](module)
            except ProtocolError as e:
                print(f"Communication error: {e}")
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        module.close()


def reference_voltage_prompt(volts: float, jack: str) -> str:
    return (f"Patch a precise {volts:g} V reference (check it with a "
            f"voltmeter) into {jack}.")


def pitch_steps(jack: str, start: int, unpatched: str) -> list[Step]:
    """The CALIBRATE sequence shared by Clouds, Elements, Plaits, Rings and
    Warps: `start` enters calibration mode, start+1 samples 1 V (and the
    zero offsets of the other CV inputs), start+2 samples 3 V and saves."""
    return [
        Step(start, f"Unpatch {unpatched}.", settle=False),
        Step(start + 1, reference_voltage_prompt(1.0, jack)),
        Step(start + 2, reference_voltage_prompt(3.0, jack)),
    ]
