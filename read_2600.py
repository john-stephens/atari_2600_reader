
from __future__ import print_function

import smbus
import time
import struct
import argparse
import sys
import math

# Argument definition and handling
parser = argparse.ArgumentParser(description="Read an Atari 2600 cartridge via I2C")
parser.add_argument("-s", dest="rom_size", metavar="size", type=int, required=True, choices=[2, 4, 8, 16], help="ROM size in kb (2, 4, 8, 16)")
parser.add_argument("-o", dest="output_file", metavar="filename", required=True, help="ROM output file")
parser.add_argument("-b", dest="rom_bank", metavar="type", default="auto", choices=["auto", "F8", "F6"], help="ROM bank switching method (auto, F8, F6) [default: F8]")
parser.add_argument("--rom-delay", metavar="delay", type=float, default=0.2, help="ROM delay in seconds between setting the address and reading a byte [default=0.2]")
parser.add_argument("--retries", metavar="num", type=int, default=3, help="Number of retried when an I/O error is received during reading [default: 3]")
parser.add_argument("--i2c-bus", metavar="num", type=int, default=1, help="The I2C bus to read from (0=/dev/i2c-0, 1=/dev/i2c-1) [default: 1]")
parser.add_argument("--write-bus1", metavar="addr", default="0x20", help="The I2C bus address to use to write the first 8 bytes of the ROM address [default: 0x20]")
parser.add_argument("--write-bank1", metavar="num", type=int, default=0, choices=[0, 1, 2], help="The MCP23017 or MCP23008 bank to use to write the first 8 bytes of the ROM address (0=MCP23017 Bank A, 1=MCP23017 Bank B, 2=MCP23008) [default: 0]")
parser.add_argument("--write-bus2", metavar="addr", default="0x20", help="The I2C bus address to use to write the last 5 bytes of the ROM address [default: 0x20]")
parser.add_argument("--write-bank2", metavar="num", type=int, default=1, choices=[0, 1, 2], help="The MCP23017 or MCP23008 bank to use to write the last 5 bytes of the ROM address (0=MCP23017 Bank A, 1=MCP23017 Bank B, 2=MCP23008) [default: 1]")
parser.add_argument("--read-bus", metavar="addr", default="0x24", help="The I2C bus address to use to read the ROM data [default: 0x24]")
parser.add_argument("--read-bank", metavar="num", type=int, default=0, choices=[0, 1, 2], help="The MCP23017 or MCP23008 bank to use to read the ROM data (0=MCP23017 Bank A, 1=MCP23017 Bank B, 2=MCP23008) [default: 0]")

args = parser.parse_args()

# Output settings
OUTPUT_FILE = args.output_file

# ROM settings
ROM_SIZE = args.rom_size * 1024
ROM_OFFSET = 0x1000
ROM_MAX_BANK = 4096
ROM_BANK = args.rom_bank
ROM_F8_BANKS = [ 0x1FF8, 0x1FF9 ]
ROM_F6_BANKS = [ 0x1FF6, 0x1FF7, 0x1FF8, 0x1FF9 ]
ROM_DELAY = args.rom_delay
MAX_RETRIES = args.retries
RETRY_DELAY = 5

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

def realAddress(address):
    return ( ( address - ROM_OFFSET ) % ROM_MAX_BANK ) + ROM_OFFSET

def bankNumber(address):
    return int(math.floor( ( address - ROM_OFFSET ) / ROM_MAX_BANK ))

# Perform bank switching to correct the bank before reading, if needed
def bankSwitch(bus, address, rom_bank):

    real_address = realAddress(address)
    bank_number = bankNumber(address)

    if rom_bank == "F8" and ( real_address == ROM_OFFSET or ( real_address - 1 ) in ROM_F8_BANKS ):
        print("\nBank switch! {0:x} {1:x}" . format(address, ROM_F8_BANKS[ bank_number ]))
        setAddress(bus, ROM_F8_BANKS[ bank_number ])

    elif rom_bank == "F6" and ( real_address == ROM_OFFSET or ( real_address - 1 ) in ROM_F6_BANKS ):
        print("\nBank switch! {0:x} {1:x}" . format(address, ROM_F6_BANKS[ bank_number ]))
        setAddress(bus, ROM_F6_BANKS[ bank_number ])

# Set the address to read from the cartridge
def setAddress(bus, address):
    bus.write_byte_data(ADDR_WRITE_BUS1, I2C_REG_GPIO[ ADDR_WRITE_BANK1 ], address & 0xFF)
    bus.write_byte_data(ADDR_WRITE_BUS2, I2C_REG_GPIO[ ADDR_WRITE_BANK2 ], address >> 8)
#    time.sleep(ROM_DELAY)

# Read a byte from the cartridge
def readByte(bus, retry=0):
    try:
        return bus.read_byte_data(ADDR_READ_BUS, I2C_REG_GPIO[ ADDR_READ_BANK ])
    except:
        if retry < MAX_RETRIES:
            print("\nRetry delay!")
            time.sleep(RETRY_DELAY)
            return readByte(bus, retry + 1)
        else:
            raise

def readByteFast(bus, retry=0):
    last_byte = None
    byte_count = 0

    while byte_count < 10:

        byte = readByte(bus, retry)

        if byte == last_byte:
            byte_count += 1
        else:
            if last_byte != None:
                print("Mismatch {0:x} {1:x}" . format(last_byte, byte))
                time.sleep(ROM_DELAY)
            last_byte = byte
            byte_count = 0

    return byte

# Check the ROM for basic errors
def checkRom(bus):

    print("Checking ROM...")

    bytes = []

    for x in range(0, 16):
        setAddress(bus, x + ROM_OFFSET)
        byte = readByte(bus)
        bytes.append(byte)

    if checkRomZeros(bytes) and checkRomDuplicate(bytes):
        print("ROM checks passed")
        return True

    return False

# Check the ROM for all zeros
def checkRomZeros(bytes):
    if bytes.count(0) == len(bytes):
        print("Error: all zeros returned, is cartridge inserted?")
        return False

    return True

# Check the ROM for pairs of bytes with duplicate values
def checkRomDuplicate(bytes):
    num_bytes = len(bytes)
    count = 0

    for x in range(0, num_bytes/2):
        if bytes[x * 2] == bytes[x * 2 + 1]:
            count += 1

    if count == num_bytes/2:
        print("Error: duplicate bytes returned, wiring issue?")
        return False

    return True

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

if checkRom(bus):

    # Set the default ROM bank method
    if ROM_SIZE == 8192 and ROM_BANK == "auto":
        ROM_BANK = "F8"

    if ROM_SIZE == 16384 and ROM_BANK == "auto":
        ROM_BANK = "F6"

    if ROM_BANK == "auto":
        ROM_BANK = None

    file = open(OUTPUT_FILE, "wb")

    for x in range(0, ROM_SIZE):
        bankSwitch(bus, x + ROM_OFFSET, ROM_BANK)
        setAddress(bus, realAddress(x + ROM_OFFSET))
        byte = readByteFast(bus)
        file.write(struct.pack('B', byte))
        sys.stdout.write("\rRead {0} of {1} bytes" . format(x + 1, ROM_SIZE));
        sys.stdout.flush()

    file.close()

    print("\nDone!")

bus.close();

