# Mutable Calibrators

Scripts that calibrate Mutable Instruments modules through their hidden
factory-test UART port (see `stmlib`-based firmware in
[mutable-eurorack](https://github.com/pichenettes/eurorack)).

| Script        | Module        | What gets calibrated                                   | Reference needed                 |
|---------------|---------------|--------------------------------------------------------|----------------------------------|
| `marbles.py`  | Marbles       | DAC (Y, X1–X3), T RATE / X SPREAD inputs               | Voltmeter                        |
| `tides2.py`   | Tides (2018)  | DAC (OUT 1–4), V/OCT input                             | Voltmeter                        |
| `stages.py`   | Stages        | DAC (6 outputs), 6 TIME/LEVEL inputs; live input view  | Voltmeter                        |
| `plaits.py`   | Plaits        | V/OCT input                                            | Precise 1 V and 3 V source       |
| `clouds.py`   | Clouds        | V/OCT input                                            | Precise 1 V and 3 V source       |
| `elements.py` | Elements      | V/OCT input                                            | Precise 1 V and 3 V source       |
| `rings.py`    | Rings         | V/OCT input, V/OCT normalization threshold             | Precise 1 V and 3 V source       |
| `warps.py`    | Warps         | LEVEL 1 CV (V/OCT) input, LEVEL 1/2 normalization      | Precise 1 V and 3 V source       |
| `beads.py`    | Beads         | V/OCT and DENSITY inputs                               | Precise 1 V and 3 V source       |

Marbles and Tides (2018) have been tested on hardware. The other scripts
follow the firmware source and pass the hardware-free tests, but have not
been run against a real module yet. Reports are welcome.

Other modules in the repository (Braids, Branches, Frames, Grids, Peaks,
Streams, Tides (2015), Yarns, ...) have no factory-test UART. Calibrate them
from the front panel as described in their manuals.

## Usage

```
python <module>.py [DEVICE]
```

`DEVICE` is the serial interface (e.g. `/dev/ttyUSB0`, `COM3`); you are
prompted for it if omitted. A menu then offers the calibrations the module
supports.

### The module must be freshly flashed

The factory-test port only listens on a module's **first power-up after
flashing**, before any settings were saved. Storing a calibration saves
settings, so do every calibration you need (e.g. DAC *and* inputs) in one
session. Otherwise you have to reflash.

To make this easier, edit `stmlib/makefile.inc` and remove `-c "reset run"`
from `POSTLUDE`. The module then stays in reset after flashing, so you can
power it down, disconnect the programmer and connect the serial adapter.

### Wiring

Connect RX, TX **and GND** of a 3.3 V USB-serial adapter to the module's
debug UART (9600 baud, 8N1). On Stages, the factory-test UART is the left
chaining link, not a separate header.

### DAC (output) calibration: Marbles, Tides (2018), Stages

For each output the module drives two fixed DAC codes (about −2 V and +4 V);
type in what the voltmeter reads. The script computes scale and offset,
stores them on the module and drives the output to +1 V. If the output then
does not read +1 V, answer `n` to measure that output again. At the end the
script prints the values as C code you can bake into `Settings::Init()`.

### Input calibration

* **Marbles, Tides (2018), Stages** use their own (DAC-calibrated) outputs as
  the reference. Run the DAC calibration first, then patch as prompted:
  * Marbles: any output to T RATE and any output to X SPREAD.
  * Tides (2018): OUT 1 to V/OCT.
  * Stages: each output to its own channel's TIME/LEVEL input.
* **Plaits, Clouds, Elements, Rings, Warps, Beads** need an external
  reference: patch exactly 1 V, then exactly 3 V, when prompted. Check the
  source with a voltmeter. Leave every other input unpatched, because the
  zero offsets of the other CV inputs are captured at the same time. Rings
  and Warps then calibrate their normalization-probe threshold with the
  input unpatched. Beads also calibrates DENSITY CV the same way.

Most modules don't report whether an input calibration succeeded over the
port. If a reading is out of range, the module shows its error LED pattern
instead of saving. Beads reports each step and the script stops at the
first failure.

## Development

```
python -m unittest test_calibrators
```

The tests emulate the firmware side of the protocol (reply bytes, nibble
accumulator, scale/offset decoding), so they need no hardware.

Layout: `factory_test.py` is the wire protocol, `mi_module.py` holds the
module base classes and the DAC maths, and `cli.py` has the shared
interactive flows. Each `<module>.py` holds that firmware's command table
(opcode numbers differ between modules) and its calibration steps.

## Requirements

- Python 3.10+
- pyserial: `pip install -r requirements.txt`

## License

GPLv3 unless otherwise noted
