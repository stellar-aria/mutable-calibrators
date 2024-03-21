from serial import Serial
from enum import Enum
import struct

# top 3 bits are command, bottom 5 are argument
ARGUMENT_MASK = 0x1F
COMMAND_MASK = 0xE0
COMMAND_POS = 5


class Command(Enum):
    READ_POT = 0
    READ_CV = 1
    READ_GATE = 2
    GENERATE_TEST_SIGNALS = 3
    CALIBRATE = 4
    READ_NORMALIZATION = 5
    FORCE_DAC_CODE = 6
    WRITE_CALIBRATION_DATA_NIBBLE = 7  # done in nibbles (4 bit chunks)


class TestingRequest:
    def __init__(self, command: Command, argument: int):
        assert 0 <= argument < 32
        self.command = command
        self.argument = argument

    # 1 byte output
    def packed(self) -> int:
        output = self.command.value << COMMAND_POS
        output |= self.argument & ARGUMENT_MASK
        return output


class CalibrationData:
    def __init__(self, scale: float, offset: float):
        self.scale = scale
        self.offset = offset

    # 4 byte output
    def packed(self) -> bytes:
        # two uint16_t (unsigned shorts) for a 4 byte (uint32_t) message
        # scale is high short
        # offset is low short
        return struct.pack(">HH", int(self.scale), int(self.offset))


class DebugPort:

    def __init__(self, port: str):
        self.port = Serial(port)

    def send(self, command: Command, argument: int):
        self.port.write(TestingRequest(command, argument).packed())

    def read(self) -> int:
        return self.port.read()[0]

    def write_calibration_data(self, scale: float, offset: float):
        for byte in CalibrationData(scale, offset).packed():
            # top nibble
            self.send(TestingRequest(Command.WRITE_CALIBRATION_DATA_NIBBLE, byte >> 4))

            # bottom nibble
            self.send(TestingRequest(Command.WRITE_CALIBRATION_DATA_NIBBLE, byte & 0xF))
