import sys
import time
from typing import Tuple
from factory_test import Command
from kbhit import KBHit
from mi_module import MIModule

NUM_CHANNELS = 6
DEFAULT_SCALE = -32263
DEFAULT_OFFSET = 32768

SLEEP_TIME = 0.25


class Stages(MIModule):
    def read_slider(self, channel: int) -> int:
        # sliders after pots
        return self.read_pot(channel + NUM_CHANNELS)

    def read_button(self, channel: int) -> bool:
        # buttons after gates
        return self.read_gate(channel + NUM_CHANNELS)

    def calibrate_dac_channel(self, channel: int) -> Tuple[int, int]:
        # Begin signal output
        super().calibrate_dac_channel(channel, 0)  # Channel to -1.0V
        neg_one_reading = float(
            input(f"Enter value on voltmeter for output {channel}: ")
        )

        super().calibrate_dac_channel(channel, 1)  # Channel to +2.5V
        pos_two_point_five_reading = float(
            input(f"Enter value on voltmeter for output {channel}: ")
        )

        # Calculate scale and offset
        neg_one = -1 / 8
        pos_two_point_five = 2 / 8
        neg_one_dac_code = (
            (neg_one * DEFAULT_SCALE) / (neg_one_reading / 8)
        ) * neg_one + DEFAULT_OFFSET
        pos_two_point_five_dac_code = (
            (pos_two_point_five * DEFAULT_SCALE) / (pos_two_point_five_reading / 8)
        ) * pos_two_point_five + DEFAULT_OFFSET

        scale = (pos_two_point_five_dac_code - neg_one_dac_code) / (
            (pos_two_point_five - neg_one)
        )
        offset = neg_one_dac_code - (neg_one * scale)

        # Send
        self.port.write_calibration_data(scale, offset)

        # Save to module
        super().calibrate_dac_channel(channel, 3)

        return (scale, offset)

    def calibrate_adc_channel(self, channel: int):
        super().calibrate_adc_channel(channel, 0)
        time.sleep(SLEEP_TIME)

        super().calibrate_adc_channel(channel, 1)
        time.sleep(SLEEP_TIME)

        super().calibrate_adc_channel(channel, 2)
        time.sleep(SLEEP_TIME)

    def calibrate(self):
        print("Beginning full calibration")
        dac_data = []
        for i in range(NUM_CHANNELS):
            dac_data[i] = self.calibrate_dac_channel(i)

        print("Patch all channels to their corresponding TIME/LEVEL input. Press enter when ready.")
        input()
        for i in range(NUM_CHANNELS):
            self.calibrate_adc_channel(i)
        print("Calibration complete!")

        print(
            "For more accurate DAC output, insert the below code before the return of Settings::Init() and rerun ADC calibration"
        )
        for scale, offset in dac_data:
            print(
                f"persistent_data_.channel_calibration_data[{i}].dac_scale = {scale:.4f};"
            )
            print(
                f"persistent_data_.channel_calibration_data[{i}].dac_offset = {offset:.4f};"
            )

    def get_state(self):
        pots = [self.read_pot(i) for i in range(NUM_CHANNELS)]
        buttons = [self.read_button(i) for i in range(NUM_CHANNELS)]
        sliders = [self.read_slider(i) for i in range(NUM_CHANNELS)]
        normals = [self.read_normalization(i) for i in range(NUM_CHANNELS)]
        gates = [self.read_gate(i) for i in range(NUM_CHANNELS)]
        cvs = [self.read_cv(i) for i in range(NUM_CHANNELS)]
        return [pots, buttons, sliders, normals, gates, cvs]

def display(stages):
    kb = KBHit()
    print("Press ESC or 'q' to exit")
    channels = [f"Channel {c}" for c in range(NUM_CHANNELS)]
    while True:
        if kb.kbhit():
            c = kb.getch()
            if ord(c) == 27 or c == 'q': # ESC
                break

        state = [channels] + stages.get_state()
        output = ["\t".join(data) for data in state]
        for line in output:
            sys.stdout.write("\x1b[1A\x1b[2K")  # move up cursor and delete whole line

        for line in output:
            sys.stdout.write(line + "\n")  # reprint the lines

if __name__ == "__main__":
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        print("Enter port to connect on:")
        port = input()

    try:
        stages = Stages(port)
    except Exception as e:
        print(f"Unable to connect: {e}")
        exit()

    print(f"Attached to serial port {port}...")

    print("Stages:")
    while True:
        print("What would you like to do?")
        print("(c): Calibrate both ")
        print("(a): Calibrate only the ADC")
        print("(d): Calibrate only the DAC")
        print("(g): Generate test signals")
        print("(r): read the current state of the module")
        print("(q): quit")
        response = input(">>> ")
        match response:
            case "c" | "calibrate":
                stages.calibrate()

            case "a" | "adc":
                print("Patch all channels to their corresponding TIME/LEVEL input. Press enter when ready.")
                input()
                for i in range(NUM_CHANNELS):
                    stages.calibrate_adc_channel(i)

            case "d" | "dac":
                for i in range(NUM_CHANNELS):
                    stages.calibrate_dac_channel(i)

            case 'g' | "generate":
                stages.generate_test_signals()

            case "r" | "read":
                display(stages)

            case "q" | "quit":
                exit()
