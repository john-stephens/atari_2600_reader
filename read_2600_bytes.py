
from __future__ import print_function

import smbus
import time
import struct
import argparse
import sys

# Argument definition and handling
parser = argparse.ArgumentParser(description="Read bytes from an Atari 2600 cartridge via I2C and output then on the console for debuggging.")
parser.add_argument("-n", dest="num_bytes", metavar="num", type=int, required=True, help="Number of bytes to read")
parser.add_argument("-o", dest="rom_offset", metavar="offset", default="0x00", help="Offset to start reading from (hex or int) [default: 0x00]")
parser.add_argument("--rom-delay", metavar="delay", type=float, default=0.2, help="ROM delay in seconds between setting the address and reading a byte [default=0.2]")
parser.add_argument("--retries", metavar="num", type=int, default=3, help="Number of retried when an I/O error is received during reading [default: 3]")
parser.add_argument("--i2c-bus", metavar="num", type=int, default=1, help="The I2C bus to read from (0=/dev/i2c-0, 1=/dev/i2c-1) [default: 1]")
parser.add_argument("--write-bus1", metavar="addr", default="0x20", help="The I2C bus address to use to write the first 8 bytes of the ROM address (hex or int) [default: 0x20]")
parser.add_argument("--write-bank1", metavar="num", type=int, default=0, choices=[0, 1, 2], help="The MCP23017 or MCP23008 bank to use to write the first 8 bytes of the ROM address (0=MCP23017 Bank A, 1=MCP23017 Bank B, 2=MCP23008) [default: 0]")
parser.add_argument("--write-bus2", metavar="addr", default="0x20", help="The I2C bus address to use to write the last 5 bytes of the ROM address (hex or int) [default: 0x20]")
parser.add_argument("--write-bank2", metavar="num", type=int, default=1, choices=[0, 1, 2], help="The MCP23017 or MCP23008 bank to use to write the last 5 bytes of the ROM address (0=MCP23017 Bank A, 1=MCP23017 Bank B, 2=MCP23008) [default: 1]")
parser.add_argument("--read-bus", metavar="addr", default="0x24", help="The I2C bus address to use to read the ROM data (hex or int) [default: 0x24]")
parser.add_argument("--read-bank", metavar="num", type=int, default=0, choices=[0, 1, 2], help="The MCP23017 or MCP23008 bank to use to read the ROM data (0=MCP23017 Bank A, 1=MCP23017 Bank B, 2=MCP23008) [default: 0]")

args = parser.parse_args()

# ROM settings
ROM_SIZE = args.num_bytes
ROM_OFFSET = int(args.rom_offset, 0)
ROM_DELAY = args.rom_delay
MAX_RETRIES = args.retries

# I2C bus settings
I2C_BUS = args.i2c_bus

# The 2600 has 13 address pins, so we need to spread these over two banks
# with the first 8 bits on the first bank and the remaining 5 on the second.
ADDR_WRITE_BUS1 = int(args.write_bus1, 0)
ADDR_WRITE_BANK1 = args.write_bank1

ADDR_WRITE_BUS2 = int(args.write_bus2, 0)
ADDR_WRITE_BANK2 = args.write_bank2

# The 2600 has 8 data pins, so we can use a single bank for that
ADDR_READ_BUS = int(args.read_bus, 0)
ADDR_READ_BANK = args.read_bank

# I2C Register Constants for MCP23017 and MCP23008
#
# Taken from the following datasheets:
# MCP23017: http://ww1.microchip.com/downloads/en/DeviceDoc/20001952C.pdf (table 3-3)
# MCP23008: http://ww1.microchip.com/downloads/en/DeviceDoc/21919e.pdf (table 1-3)
I2C_REG_IODIR = [ 0x00, 0x01, 0x00 ]
I2C_REG_GPIO = [ 0x12, 0x13, 0x09 ]
I2C_IODIR_PORT_READ = 0xFF
I2C_IODIR_PORT_WRITE = 0x00

# Configure the MCP23017/MCP23008 chips for reading and writing
def configBus(bus):
    # Write bus
    print("Configuring bus 0x{0:02x}, bank {1} for writing (reg: 0x{2:02x})" . format(ADDR_WRITE_BUS1, ADDR_WRITE_BANK1, I2C_REG_IODIR[ ADDR_WRITE_BANK1 ]))
    bus.write_byte_data(ADDR_WRITE_BUS1, I2C_REG_IODIR[ ADDR_WRITE_BANK1 ], I2C_IODIR_PORT_WRITE)

    print("Configuring bus 0x{0:02x}, bank {1} for writing (reg: 0x{2:02x})" . format(ADDR_WRITE_BUS2, ADDR_WRITE_BANK2, I2C_REG_IODIR[ ADDR_WRITE_BANK2 ]))
    bus.write_byte_data(ADDR_WRITE_BUS2, I2C_REG_IODIR[ ADDR_WRITE_BANK2 ], I2C_IODIR_PORT_WRITE)

    # Read bus
    print("Configuring bus 0x{0:02x}, bank {1} for reading (reg: 0x{2:02x})" . format(ADDR_READ_BUS, ADDR_READ_BANK, I2C_REG_IODIR[ ADDR_READ_BANK ]))
    bus.write_byte_data(ADDR_READ_BUS, I2C_REG_IODIR[ ADDR_READ_BANK ], I2C_IODIR_PORT_READ)

# Set the address to read from the cartridge
def setAddress(bus, address):
    bus.write_byte_data(ADDR_WRITE_BUS1, I2C_REG_GPIO[ ADDR_WRITE_BANK1 ], address & 0xFF)
    bus.write_byte_data(ADDR_WRITE_BUS2, I2C_REG_GPIO[ ADDR_WRITE_BANK2 ], address >> 8)
    time.sleep(ROM_DELAY)

# Read a byte from the cartridge
def readByte(bus, retry=0):
    try:
        return bus.read_byte_data(ADDR_READ_BUS, I2C_REG_GPIO[ ADDR_READ_BANK ])
    except:
        if retry < MAX_RETRIES:
            return readByte(bus, retry + 1)
        else:
            raise

# Test code to validate the address line wiring, moves from the first
# address pin to the last with a 30 second delay
#
#bit = 1
#
#for x in range(0, 13):
#    setAddress(bit)
#    bit = bit << 1
#    time.sleep(30)

bus = smbus.SMBus(I2C_BUS)

configBus(bus)

for x in range(0, ROM_SIZE):

    setAddress(bus, x + ROM_OFFSET)
    byte = readByte(bus)
    print("{0:02x}" . format(byte))

bus.close();

