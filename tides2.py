#!/bin/python3
from enum import Enum
from typing import Tuple
from time import sleep
import sys

from mi_module import MIModule


class OutputChannel(Enum):
    O_1 = 0
    O_2 = 1
    O_3 = 2
    O_4 = 3


class Tides2(MIModule):
    def calibrate_dac_channel(self, channel: OutputChannel) \
            -> Tuple[float, float]:
        super().calibrate_dac_channel(channel.value, 0)
        minus_two_volt_reading = float(
            input(f"Enter value on voltmeter for {
                  channel.name} output (should be close to -2V): ")
        )

        super().calibrate_dac_channel(channel.value, 1)
        four_volt_reading = float(
            input(f"Enter value on voltmeter for {
                  channel.name} output (should be close to 4V): ")
        )
        # these DAC code values correspond to
        # value set in file tides2/ui.cc,
        # function HandleFactoryTestingRequest,
        # case FACTORY_TESTING_FORCE_DAC_CODE
        # and should result in voltages -2V and 4V.
        code_4 = 0x416b
        code_m2 = 0x9ff1
        scale = (code_4 - code_m2) / \
            (four_volt_reading - minus_two_volt_reading)
        offset = code_m2 - minus_two_volt_reading * scale

        guard = True
        while guard:
            self.port.write_calibration_data(scale / -0.125, offset)

            # step = 2 forces the module to store written calibration data
            # and set the output to 1V
            sleep(0.1)
            super().calibrate_dac_channel(channel.value, 2)

            key = input(
                "Value on voltmeter should read now 1V. Press y and ENTER to "
                "confirm, any other key and ENTER to retry: ")
            guard = (key != "y")
        return (scale, offset)

    def calibrate_adc_channel(self):
        # SETUP, 1V RATE, 3V RATE, 1V SPREAD, 3V SPREAD
        for step in range(5):
            super().calibrate_adc_channel(0, step)
            sleep(0.5)

    def calibrate_dac(self):
        try:
            input("Press ENTER to start DAC calibration.")
            super().generate_test_signals(True)
            input("All outputs should have orange LEDs right now. "
                  "Press ENTER to continue.")
            data = []
            for channel in list(OutputChannel):
                data.append(self.calibrate_dac_channel(channel))

            print("DAC Calibrated!")
            print(
                "If any output does not read 1V right now, reflash and "
                "rerun the calibration.")
            print(
                "For more accurate ADC calibration results, you can instead copy "
                "the below code into Settings::Init() and rerun ADC calibration"
            )
            for i, (scale, offset) in enumerate(data):
                print(
                    f"c.dac_scale[{i}] = {
                        scale:.4f}f; c.dac_offset[{i}] = {offset:.4f}f;"
                )
        except IOError:
            print("Error during communication. Check power and connection.")
            exit(-1)

    def calibrate_adc(self):
        print("ADC calibration unsupported... yet!")
        return
        # Begin signal output
        try:
            input("Press ENTER to start ADC calibration.")
            self.generate_test_signals()

            print("All outputs should have orange LEDs right now. Please patch "
                  "cables from any output to RATE and SPREAD input "
                  "and then press ENTER")
            input()
            self.calibrate_adc_channel()
        except IOError:
            print("Error during communication. Check power and connection.")
            exit(-1)

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

    print(f"Connecting to Tides2 on port {port}...")

    try:
        tides = Tides2(port)
    except Exception as e:
        print(f"Unable to connect: {e}")
        exit()

    print("Success!")
    print("Remember, only freshly flashed module can be calibrated using "
          "this method (i.e., on its first powerup after flashing). "
          "If at the beginning of any type of calibration LEDs do not turn "
          "orange when specified, that may mean connection issues or "
          "not freshly flashed unit.")
    print("Choose calibration: ")
    print("  a - ADC")
    print("  d - DAC")
    print("  m - both")
    response = input(">>> ")
    if response == "m":
        tides.calibrate()
    elif response == "a":
        tides.calibrate_adc()
    elif response == "d":
        tides.calibrate_dac()
    # else:
    #     manual_prompt(port)
    exit()
