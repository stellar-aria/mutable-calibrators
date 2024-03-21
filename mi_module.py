from factory_test import DebugPort, Command


class MIModule:
    def __init__(self, port: str) -> None:
        self.port = DebugPort(port)

    def __read_analog(self, command: Command, channel: int) -> int:
        self.port.send(command, channel)
        return self.port.read()

    def __read_digital(self, command: Command, channel: int) -> bool:
        self.port.send(command, channel)
        return bool(self.port.read())

    def read_cv(self, channel: int) -> int:
        return self.__read_analog(Command.READ_CV, channel)

    def read_pot(self, channel: int) -> int:
        return self.__read_analog(Command.READ_POT, channel)

    def read_gate(self, channel: int) -> bool:
        return self.__read_digital(Command.READ_GATE, channel)

    def read_normalization(self, channel: int) -> bool:
        self.port.send(Command.READ_NORMALIZATION, channel)
        return bool(self.port.read())

    def __calibrate(self, command: Command, channel: int, step: int):
        self.port.send(command, (channel << 2) | step)

    def calibrate_adc_channel(self, channel: int, step: int):
        self.__calibrate(Command.CALIBRATE, channel, step)

    def calibrate_dac_channel(self, channel: int, step: int):
        self.__calibrate(Command.FORCE_DAC_CODE, channel, step)

    def generate_test_signals(self, output: bool = True):
        self.port.send(Command.GENERATE_TEST_SIGNALS, int(output))
