from PyPmx import PmxInterface, PciAddress, U32

spi = PciAddress(0, 31, 5)
pmx = PmxInterface()
spiMmio = pmx.PciRead32(spi + 0x10) & 0xFFFFF000

biosLen = 0x800000
biosData = b""
f = open("dump.bin", "wb")

for i in range(0, biosLen, 0x40):
    # write address
    pmx.MemWrite32(spiMmio + 0x08, i)
    # write command
    #        read      0x40 bytes      start     clear fcerr & fgo
    cmd = (0 << 17) | (0x3F << 24) | (1 << 16) |         3
    pmx.MemWrite32(spiMmio + 0x04, cmd)
    # wait for read or error
    curCmd = pmx.MemRead32(spiMmio + 0x04)
    while curCmd & 3 == 0:
        curCmd = pmx.MemRead32(spiMmio + 0x04)
    # read data
    data = pmx.MemRead(spiMmio + 0x10, 0x40, U32)
    f.write(data)