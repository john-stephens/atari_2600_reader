
import smbus
import time
import struct

# Output settings
OUTPUT_FILE = 'test.rom'

# ROM settings
ROM_SIZE = 4096
ROM_OFFSET = 0x1000
ROM_DELAY = 0.2 # Delay between setting address and reading a byte
MAX_RETRIES = 3 # Number of retries to work around occasional I/O errors

# I2C bus settings
I2C_BUS = 1	# 0=/dev/i2c-0, 1=/dev/i2c-1

# The 2600 has 13 address pins, so we need to spread these over two banks
# with the first 8 bits on the first bank and the remaining 5 on the second.
ADDR_WRITE_BUS1 = 0x20 
ADDR_WRITE_BANK1 = 0 # 0=MCP23017 Bank A, 1=MCP23017 Bank B, 2=MCP23008

ADDR_WRITE_BUS2 = 0x20
ADDR_WRITE_BANK2 = 1 # 0=MCP23017 Bank A, 1=MCP23017 Bank B, 2=MCP23008

# The 2600 has 8 data pins, so we can use a single bank for that
ADDR_READ_BUS = 0x24
ADDR_READ_BANK = 0 # 0=MCP23017 Bank A, 1=MCP23017 Bank B, 2=MCP23008

# I2C Register Constants for MCP23017 and MCP23008
#
# Taken from the following datasheets:
# MCP23017: http://ww1.microchip.com/downloads/en/DeviceDoc/20001952C.pdf
# MCP23008: http://ww1.microchip.com/downloads/en/DeviceDoc/21919e.pdf
I2C_REG_IODIR = [ 0x00, 0x01, 0x00 ]
I2C_REG_GPIO = [ 0x12, 0x13, 0x09 ]
I2C_IODIR_PORT_READ = 0xFF
I2C_IODIR_PORT_WRITE = 0x00

def configBus(bus):
    # Configure the write bus
    print("Configuring bus 0x{0:02x}, bank {1} for writing (reg: 0x{2:02x})" . format(ADDR_WRITE_BUS1, ADDR_WRITE_BANK1, I2C_REG_IODIR[ ADDR_WRITE_BANK1 ]))
    bus.write_byte_data(ADDR_WRITE_BUS1, I2C_REG_IODIR[ ADDR_WRITE_BANK1 ], I2C_IODIR_PORT_WRITE)

    print("Configuring bus 0x{0:02x}, bank {1} for writing (reg: 0x{2:02x})" . format(ADDR_WRITE_BUS2, ADDR_WRITE_BANK2, I2C_REG_IODIR[ ADDR_WRITE_BANK2 ]))
    bus.write_byte_data(ADDR_WRITE_BUS2, I2C_REG_IODIR[ ADDR_WRITE_BANK2 ], I2C_IODIR_PORT_WRITE)

    # Configure the read bus
    print("Configuring bus 0x{0:02x}, bank {1} for reading (reg: 0x{2:02x})" . format(ADDR_READ_BUS, ADDR_READ_BANK, I2C_REG_IODIR[ ADDR_READ_BANK ]))
    bus.write_byte_data(ADDR_READ_BUS, I2C_REG_IODIR[ ADDR_READ_BANK ], I2C_IODIR_PORT_READ)

def setAddress(bus, address):
    bus.write_byte_data(ADDR_WRITE_BUS1, I2C_REG_GPIO[ ADDR_WRITE_BANK1 ], address & 0xFF)
    bus.write_byte_data(ADDR_WRITE_BUS2, I2C_REG_GPIO[ ADDR_WRITE_BANK2 ], address >> 8)
    time.sleep(ROM_DELAY)

def readByte(bus, retry=0):
    try:
        return bus.read_byte_data(ADDR_READ_BUS, I2C_REG_GPIO[ ADDR_READ_BANK ])
    except:
        if retry < MAX_RETRIES:
            return readByte(bus, retry + 1)
        else:
            raise

def checkRom(bus):

    print("Checking ROM...")

    bytes = []

    for x in range(0, 16):
        setAddress(bus, x + ROM_OFFSET)
        byte = readByte(bus)
        bytes.append(byte)

    if checkRomZeros(bytes) and checkRomOnes(bytes) and checkRomDuplicate(bytes):
        print("ROM Checks Passed")
        return True

    return False

def checkRomZeros(bytes):
    if bytes.count(0) == len(bytes):
        print("Error: all zeros returned, is cartridge inserted?")
        return False

    return True

def checkRomOnes(bytes):
    if bytes.count(0xFF) == len(bytes):
        print("Error: all ones returned, wiring issue?")
        return False

    return True

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

    file = open(OUTPUT_FILE, "wb")

    for x in range(0, ROM_SIZE):

        if x % 128 == 0:
            print("Reading {0} of {1}" . format(x, ROM_SIZE))

        setAddress(bus, x + ROM_OFFSET)
        byte = readByte(bus)
        file.write(struct.pack('B', byte))
#        print "%x" % (byte)

    file.close()

bus.close();
