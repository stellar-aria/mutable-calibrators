from enum import Enum, IntEnum
from typing import Tuple
from factory_test import *
import sys

from mi_module import MIModule


class OutputChannel(Enum):
    Y = 0
    X_1 = 1
    X_2 = 2
    X_3 = 3


# For both ADC and CV
class InputChannel(Enum):
    DEJA_VU_AMOUNT = 0
    DEJA_VU_LENGTH = 1
    T_RATE = 2
    T_BIAS = 3
    T_JITTER = 4
    X_SPREAD = 5
    X_BIAS = 6
    X_STEPS = 7


class ClockInput(IntEnum):
    T = 0
    X = 1


class Marbles(MIModule):
    def calibrate_dac_channel(self, channel: OutputChannel) -> Tuple[float, float]:
        super().calibrate_dac_channel(channel.value, 0)
        one_volt_reading = input(
            f"Enter value on voltmeter for {channel.__name__} output: "
        )

        super().calibrate_dac_channel(channel.value, 1)
        three_volt_reading = input(
            f"Enter value on voltmeter for {channel.__name__} output: "
        )

        scale = {}
        offset = {}

        code_1 = 26555
        code_3 = 14129
        scale = (code_3 - code_1) / (three_volt_reading - one_volt_reading)
        offset = code_1 - one_volt_reading * scale

        self.port.write_calibration_data(channel.value, scale, offset / -0.125)
        return (scale, offset)

    def calibrate_adc_channel(self, channel: InputChannel):
        # SETUP, 1V RATE, 3V RATE, 1V SPREAD, 3V SPREAD
        for step in range(5):
            super().calibrate_adc_channel(channel, step)

    def calibrate_dac(self):
        data = []
        for channel in list(OutputChannel):
            data.append(self.calibrate_dac_channel(channel))

        print("DAC Calibrated!")
        print(
            "For more accurate calibration results, you can instead copy the below code into Settings::Init() and rerun ADC calibration"
        )
        for i, (scale, offset) in enumerate(data):
            print(
                f"c.dac_scale[{i}] = {scale:.4f}f; c.dac_offset[{i}] = {offset:.4f}f;"
            )

    def calibrate_adc(self):
        # Begin signal output
        self.generate_test_signals()

        print("Please patch from any outputs to RATE and SPREAD and then press ENTER")
        input()
        for channel in list(InputChannel):
            self.calibrate_adc_channel(channel)

        print("ADC Calibrated!")

    def calibrate(self):
        self.calibrate_dac()
        self.calibrate_adc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        print("Enter port to connect on:")
        port = input()

    print(f"Connecting to Marbles on port {port}...")

    try:
        marbles = Marbles(port)
    except Exception as e:
        print(f"Unable to connect: {e}")
        exit()

    print("Success!")
    print("Begin calibration? (y/N)")
    response = input(">>> ")
    if response == "y":
        marbles.calibrate(port)
    # else:
    #     manual_prompt(port)
    exit()
