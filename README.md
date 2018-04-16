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

Lastly, wire all of the SDA pins together. Do the same thing for the SCK pins.

The MCP23017 & MCP23008 chips can now be wired to the Raspberry Pi's GPIO
port with 4 wires:
* +5V
* GND
* SDA
* SCK

Datasheets:
* MCP23017: http://ww1.microchip.com/downloads/en/DeviceDoc/20001952C.pdf
* MCP23008: http://ww1.microchip.com/downloads/en/DeviceDoc/21919e.pdf

### Atari 2600 Cartridge

The hardest part to find for this project is the 24-pin edge connector. I was
fortunate enough to acquire the cartridge port and edge connector from a
parts 2600.  Many of the Atari 2600 cartridges have a spring-loaded protector
that retracts to expose the cartridge PCB connector. Utilizing the stock
cartridge port makes them super easy hook up.

The Atari 2600 cartridge has 24 pins:
* 13 address lines (A0-A12)
* 8 data lines (D1-D8)
* 2 ground lines (GND, sGND)
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

## Testing

### I2C Chips

Hook up the SDA, SCK, GND, and +5V lines to the Raspberry Pi's GPIO port.

Run:
```
i2cdetect -y 1
```

Note: You may need to use "-y 0" on older Raspberry Pis.

In my case, addresses 0x20 and 0x24 were detected:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: 20 -- -- -- 24 -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
```

If nothing is detected, check your wiring. Also, validate that the
Raspberry Pi's I2C port is enabled.

### Atari 2600 Cartridge

I included a debug utility that prints bytes out to the console. This can be
used to verify that you are actually getting data off of the cartridge.

```
python read_2600_bytes.py -o 0x1000 -n 16
```

You should see something like this:
```
Configuring bus 0x20, bank 0 for writing (reg: 0x00)
Configuring bus 0x20, bank 1 for writing (reg: 0x01)
Configuring bus 0x24, bank 0 for reading (reg: 0x00)
4c
6e
f4
a0
08
88
10
fd
ea
a0
04
38
b0
01
18
ea
```

If you see all zeros output, check your wiring. If you see adjacent bytes
that are exactly the same, you might want to also double-check your wiring.

## Usage

In order to copy a cartridge, you will need to know how big the ROM is that you
want to copy. This site has a pretty good reference table at the bottom:
http://www.classic-games.com/atari2600/bankswitch.html

For example, here is how you can copy a 4KB ROM and output the data to
"test.rom".
```
python read_2600.py -s 4 -o test.rom
```

You can test your dump by using the Stella emulator. You should see the name of
the game and the copyright year as the window title.

If you see any "Mismatch" lines in your output, you may have a cartridge with
a dirty or bad connector, which is causing bad bytes to be output.

