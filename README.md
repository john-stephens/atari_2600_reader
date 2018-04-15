# Atari 2600 Cartridge Reader

## Overview

This is a Python-based Atari 2600 cartridge reader for the Raspberry Pi.
Data is read via the Pi's I2C port and either 2x MCP23017s or 3x MCP23008s
I/O expander chips. 3 8-bit I2C GPIO ports are needed to make this work.

Supported cartridges:
* 2KB
* 4KB
* 8KB (F8 bank switching)
* 16KB (F6 bank switching)

Other bank switching methods should be relatively easy to add, but I didn't
have any of them to test with.

See http://www.classic-games.com/atari2600/bankswitch.html for more info
about bank switching and cartridge sizes.

### Why I2C?

For Atari 2600 cartridges, I2C isn't really necessary. Only 21 I/O pins are
needed, which the standard Raspberry Pi 40-pin GPIO connector can provide.
However, this project was a stepping stone towards reading a Commodore 64
cartridge, which requires more I/O ports. This was a good project to get my
feet wet playing with I2C and the MCP23017 chip.

## Hardware

* Raspberry Pi with I2C port enabled
* 2x MCP23017 16-port or 3x MCP23008 8-port I/O expander chips
* Atari 2600 24-pin Edge Connector

## Wiring

### I2C Chips

Start by wiring the MCP23017 or MCP23008 chips on your breadboard.
Here are the pinouts that you'll need:

![MCP23017 Pins](img/mcp23017_pins.png?raw=true "MCP23017 Pins")
![MCP23008 Pins](img/mcp23008_pins.png?raw=true "MCP23008 Pins")

In order to power the chips, you'll need to wire Vdd and RESET to +5V
and Vss to GND. The NC and INT pins can be left floating (not wired up).

Each chip will need to be given a separate I2C bus address so that we can
read/write from the appropriately. This can be done by wiring the
A0, A1, and A2 pins to either +5V or GND. 8 addresses are possible:

| Address | A0  | A1  | A2  |
| ------- | --- | --- | --- |
| 0x20    | GND | GND | GND |
| 0x21    | +5V | GND | GND |
| 0x22    | GND | +5V | GND |
| 0x23    | +5V | +5V | GND |
| 0x24    | GND | GND | +5V |
| 0x25    | +5V | GND | +5V |
| 0x26    | GND | +5V | +5V |
| 0x27    | +5V | +5V | +5V |

I utilized 2x MCP23017 chips and set them to addresses 0x20 and 0x24.

Lastly, wire all of the SDA pins together in parallel. Do the same thing for
the SCK lines.

The MCP23017 & MCP23008 chips can now be wired to the Raspberry Pi's GPIO
port with 4 wires:
* +5V
* GND
* SDA
* SCK

### Atari 2600 Cartridge

The Atari 2600 cartridge has 24 pins:
* 13 address lines
* 8 data lines
* 2 ground lines
* 1 +5V line

![Atari 2600 Edge Connector](img/atari_2600_pinout.png?raw=true "Atari 2600 Edge Connector")

It is important to make sure that you have the edge connector oriented the
correct way relative to the cartridge. The diagram above is looking top-down
into the edge connector (the part that the cartridge plugs into). It is not a
diagram of the cartridge PCB connector. Note the orientation of the cartridge's
side label and top label text relative to the edge connector. +5V is on the
label side of the cartridge at pin #23.

Wire A0-A7 in order to the first MCP23017 or MCP23008 8-bit port.

Wire A8-A12 in order to the second MCP23017 or MCP23008 8-bit port. Note that
A10 and A11 are swapped.

Wire D1-D8 in order to the third MCP23017 or MCP23008 8-bit port.

+5V goes to +5V. GND and sGND go to GND.

Simple enough.

## Usage


