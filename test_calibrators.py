"""Hardware-free tests: a fake serial port emulates the firmware side of the
factory-test protocol (one reply byte per request, nibble accumulator, the
-(high)/8 scale convention) so the byte stream and the maths can be checked.

Run with:  python -m unittest test_calibrators
"""

import builtins
import unittest
from unittest import mock

import cli
import mi_module
from beads import Beads
from clouds import Clouds
from elements import Elements
from factory_test import (DebugPort, ProtocolError, calibration_nibbles,
                          channel_step, pack_request)
from marbles import Marbles
from plaits import Plaits
from rings import Rings
from stages import Stages
from tides2 import Tides2
from warps import Warps


class FakeFirmware:
    """Serial stand-in implementing the firmware's request handling for
    FORCE_DAC_CODE (opcode 6) and WRITE_CALIBRATION_DATA_NIBBLE (opcode 7),
    with an analog output whose true response is volts = (code - off) / scale.
    """

    def __init__(self, true_scale=-4100.0, true_offset=32700.0,
                 code_low=0x9FF1, code_high=0x416B, reply=0, silent=False):
        self.true_scale, self.true_offset = true_scale, true_offset
        self.code_low, self.code_high = code_low, code_high
        self.reply, self.silent = reply, silent
        self.sent = []
        self.pending = b""
        self.accumulator = 0
        self.stored = {}       # channel -> (scale per volt, offset)
        self.forced = {}       # channel -> dac code

    # serial API used by DebugPort
    def reset_input_buffer(self):
        self.pending = b""

    def write(self, data):
        for byte in data:
            self.sent.append(byte)
            self._handle(byte >> 5, byte & 0x1F)
            if not self.silent:
                self.pending += bytes([self.reply])

    def read(self, n):
        out, self.pending = self.pending[:n], self.pending[n:]
        return out

    def close(self):
        pass

    def _handle(self, opcode, argument):
        if opcode == 6:
            channel, step = argument >> 2, argument & 3
            if step == 0:
                self.forced[channel] = self.code_low
            elif step == 1:
                self.forced[channel] = self.code_high
            else:
                offset = float(self.accumulator & 0xFFFF)
                scale = -float(self.accumulator >> 16) * 0.125
                self.stored[channel] = (scale, offset)
                self.forced[channel] = int(1.0 * scale + offset)
        elif opcode == 7:
            self.accumulator = ((self.accumulator << 4) | (argument & 0xF)) \
                & 0xFFFFFFFF

    def volts(self, channel):
        return (self.forced[channel] - self.true_offset) / self.true_scale


class ProtocolTests(unittest.TestCase):
    def test_pack_request(self):
        self.assertEqual(pack_request(4, 5), bytes([0x85]))
        with self.assertRaises(ValueError):
            pack_request(8, 0)
        with self.assertRaises(ValueError):
            pack_request(0, 32)

    def test_channel_step(self):
        self.assertEqual(channel_step(5, 2), 0b10110)
        with self.assertRaises(ValueError):
            channel_step(0, 4)

    def test_nibbles_round_trip(self):
        acc = 0
        for n in calibration_nibbles(0xBEEF, 0x1234):
            acc = (acc << 4) | n
        self.assertEqual(acc, 0xBEEF1234)

    def test_nibbles_reject_out_of_range(self):
        with self.assertRaises(ValueError):
            calibration_nibbles(-1, 0)
        with self.assertRaises(ValueError):
            calibration_nibbles(0, 0x10000)

    def test_every_request_consumes_its_reply(self):
        fw = FakeFirmware(reply=42)
        port = DebugPort(fw)
        self.assertEqual(port.request(1, 3), 42)
        self.assertEqual(fw.pending, b"")

    def test_missing_reply_raises(self):
        port = DebugPort(FakeFirmware(silent=True))
        with self.assertRaises(ProtocolError):
            port.request(0, 0)


class CommandTableTests(unittest.TestCase):
    """Opcodes must match each firmware's FactoryTestingCommand enum."""

    def test_tables(self):
        expected = {
            Marbles: {"GENERATE_TEST_SIGNALS": 3, "CALIBRATE": 4,
                      "READ_NORMALIZATION": 5, "FORCE_DAC_CODE": 6,
                      "WRITE_CALIBRATION_DATA_NIBBLE": 7},
            Stages: {"FORCE_DAC_CODE": 6, "WRITE_CALIBRATION_DATA_NIBBLE": 7},
            Tides2: {"FORCE_DAC_CODE": 6, "WRITE_CALIBRATION_DATA_NIBBLE": 7},
            Clouds: {"SET_BYPASS": 3, "CALIBRATE": 4},
            Elements: {"SET_BYPASS": 3, "CALIBRATE": 4},
            Rings: {"SET_BYPASS": 3, "CALIBRATE": 4, "READ_NORMALIZATION": 5},
            Warps: {"SET_BYPASS": 3, "CALIBRATE": 4, "READ_NORMALIZATION": 5},
            Plaits: {"GENERATE_TEST_SIGNAL": 3, "CALIBRATE": 4,
                     "READ_NORMALIZATION": 5},
            Beads: {"CALIBRATE": 4, "READ_NORMALIZATION": 5},
        }
        for cls, names in expected.items():
            for name, value in names.items():
                self.assertEqual(cls.Command[name], value, f"{cls.NAME}.{name}")
            self.assertEqual(cls.Command.READ_POT, 0)

    def test_foreign_command_rejected(self):
        rings = Rings(DebugPort(FakeFirmware()))
        with self.assertRaises(TypeError):
            rings.request(Marbles.Command.GENERATE_TEST_SIGNALS)

    def test_missing_command(self):
        with self.assertRaises(NotImplementedError):
            Clouds(DebugPort(FakeFirmware())).read_normalization(0)


class DacCalibrationTests(unittest.TestCase):
    def run_channel(self, cls, fw, channel=0, answers=("y",)):
        module = cls(DebugPort(fw))
        readings = []

        def fake_input(prompt=""):
            if "Voltmeter" in prompt:
                return f"{fw.volts(channel):.4f}"
            readings.append(prompt)
            return answers[min(len(readings) - 1, len(answers) - 1)]

        with mock.patch.object(builtins, "input", fake_input):
            return cli.calibrate_dac_channel(module, channel)

    def test_calibrated_output_reads_check_voltage(self):
        for cls in (Marbles, Stages, Tides2):
            fw = FakeFirmware(true_scale=-4100.0, true_offset=32700.0,
                              code_low=cls.CODE_LOW, code_high=cls.CODE_HIGH)
            scale, offset = self.run_channel(cls, fw, channel=2)
            self.assertAlmostEqual(scale, -4100.0, delta=1.0)
            self.assertAlmostEqual(offset, 32700.0, delta=1.0)
            self.assertAlmostEqual(fw.volts(2), cls.CHECK_VOLTS, delta=0.002,
                                   msg=cls.NAME)

    def test_marbles_default_scale_fits(self):
        # Marbles' nominal -6212.8 codes/V must survive the 16-bit encoding.
        fw = FakeFirmware(true_scale=-6212.8, true_offset=32768.0,
                          code_low=Marbles.CODE_LOW,
                          code_high=Marbles.CODE_HIGH)
        self.run_channel(Marbles, fw)
        self.assertAlmostEqual(fw.stored[0][0], -6212.8, delta=0.2)

    def test_retry_remeasures(self):
        fw = FakeFirmware()
        with mock.patch.object(builtins, "print"):
            self.run_channel(Tides2, fw, answers=("n", "y"))
        forced_steps = [b & 3 for b in fw.sent if b >> 5 == 6]
        self.assertEqual(forced_steps, [0, 1, 2, 0, 1, 2])

    def test_compute_dac_calibration(self):
        scale, offset = mi_module.compute_dac_calibration(1000, -2.0, 0, 4.0)
        self.assertAlmostEqual(scale, -1000 / 6)
        self.assertAlmostEqual(offset, 1000 - 2.0 * 1000 / 6)


class StepSequenceTests(unittest.TestCase):
    def calibrate_args(self, cls, steps):
        fw = FakeFirmware(reply=1)
        module = cls(DebugPort(fw))
        with mock.patch.object(builtins, "input", lambda p="": ""), \
                mock.patch.object(mi_module, "SETTLE_TIME", 0):
            self.assertTrue(cli.run_calibration_steps(module, steps))
        return [b & 0x1F for b in fw.sent if b >> 5 == 4]

    def test_sequences(self):
        import beads, clouds, elements, marbles, plaits, rings, stages, \
            tides2, warps
        self.assertEqual(self.calibrate_args(Marbles, marbles.ADC_STEPS),
                         [0, 1, 2, 3, 4])
        self.assertEqual(self.calibrate_args(Tides2, tides2.ADC_STEPS),
                         [0, 1, 2])
        for mod, cls in ((clouds, Clouds), (elements, Elements),
                         (plaits, Plaits)):
            self.assertEqual(self.calibrate_args(cls, mod.STEPS), [0, 1, 2])
        for mod, cls in ((rings, Rings), (warps, Warps)):
            self.assertEqual(self.calibrate_args(cls, mod.STEPS),
                             [0, 1, 2, 3, 4, 5])
        self.assertEqual(self.calibrate_args(Beads, beads.STEPS),
                         [3, 4, 5, 6, 7])
        self.assertEqual(
            self.calibrate_args(Stages, stages.adc_steps()),
            [channel_step(c, s) for c in range(6) for s in range(3)])

    def test_beads_failure_stops(self):
        import beads
        fw = FakeFirmware(reply=0)
        module = Beads(DebugPort(fw))
        with mock.patch.object(builtins, "input", lambda p="": ""), \
                mock.patch.object(mi_module, "SETTLE_TIME", 0), \
                mock.patch.object(builtins, "print"):
            self.assertFalse(cli.run_calibration_steps(module, beads.STEPS))
        self.assertEqual(len(fw.sent), 1)


if __name__ == "__main__":
    unittest.main()
