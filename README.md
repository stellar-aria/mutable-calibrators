# Mutable Calibrators

Scripts and associated utility classes for automating calibrating various Mutable Instruments Modules including Marbles and Stages (more to come as I build them or are contributed).

Right now **only Marbles script** was troubleshooted and tested.

## Usage

### Marbles
Marbles ***must*** be *freshly flashed* for the factory UART
port to remain opened. This means, that it has to be the exact first
start of the unit after flashing it using ST-Link or other
programmer.

Syntax:
python marbles.py \[DEVICE\]

DEVICE is an optional parameter for specifying the serial interface from command line.

After running the marbles.py script you will be asked which calibration to perform.

#### DAC calibration
This consists of reading the values on all outputs (Y, X1, X2, X3) using a
voltmeter with good resolution. Calculated scale and offset values for all
outputs will be sent to the module, but you *could* get even more accuracy
by recompiling the firmware with pre-calculated calibration values, as
given at the end of the script.

#### ADC calibration
This consists of connecting any output to RATE and to SPEED input, then
waiting for a moment. The accuracy of this calibration is only as good, as 
the calibration of DAC. 

#### Tips

* Remember to connect GND to serial interface, not only RX/TX.
* To achieve the *freshly flashed* state a little easier you can edit 
the `stmlib/makefile.inc` file and change the `POSTLUDE` variable by 
*removing* `-c "reset run"`. This will hold the module in hardware reset 
after flashing, allowing you to power it down, disconnect the programmer 
and connect the serial interface.


## Requirements:
- Python: ^3.12
- pyserial: `pip install pyserial`

## License:
GPLv3 unless otherwise noted
