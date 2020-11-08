from DriverLoader import PmxDriver
import ctypes
import struct

class PhysVirtAddress:
    def __init__(self, sz, pa, va):
        self.sz = sz
        self.pa = pa
        self.va = va

    def __int__(self):
        return self.pa

class PciAddress:
    def __init__(self, bus, dev, func, offset=0):
        self.b = bus
        self.d = dev
        self.f = func
        self.o = offset
    def __add__(self, other):
        if type(other) == int:
            new_offset = self.o + other
            if new_offset < 0 or new_offset >= 0x1000:
                raise ValueError("Offset overflow")
            return PciAddress(self.b, self.d, self.f, self.o + other)
        else:
            raise TypeError("You can't add anything except int")

    def __sub__(self, other):
        return self.__add__(-other)

    def mmOffset(self):
        return self.o + ((self.b * 0x20 + self.d) * 8 + self.f) * 0x1000

# types of access
U8 = 0
U16 = 1
U32 = 2

class PmxInterface:
    def __init__(self):
        self.d = PmxDriver("AsrDrv101")
        self.pciMmAddress = None
        self.pciMmTopBus = 0

    def MemRead(self, address, size, access=U8):
        buf = ctypes.c_buffer(size)
        request = struct.pack("<QIIQ", address, size, access, ctypes.addressof(buf))
        if self.d.IoCtl(0x222808, request, len(request)):
            return bytearray(buf)
        else:
            return None

    def MemRead8(self, address):
        result = self.MemRead(address, 1, U8)
        return struct.unpack("<B", result)[0] if result else None
    
    def MemRead16(self, address):
        result = self.MemRead(address, 2, U16)
        return struct.unpack("<H", result)[0] if result else None

    def MemRead32(self, address):
        result = self.MemRead(address, 4, U32)
        return struct.unpack("<I", result)[0] if result else None

    def MemRead64(self, address):
        result = self.MemRead(address, 8, U32)
        return struct.unpack("<Q", result)[0] if result else None

    def MemWrite(self, address, data, access=U8):
        buf = ctypes.c_buffer(data, len(data))
        request = struct.pack("<QIIQ", address, len(data), access, ctypes.addressof(buf))
        return self.d.IoCtl(0x22280C, request, len(request)) is not None

    def MemWrite8(self, address, value):
        return self.MemWrite(address, struct.pack("<B", value), U8)

    def MemWrite16(self, address, value):
        return self.MemWrite(address, struct.pack("<H", value), U16)

    def MemWrite32(self, address, value):
        return self.MemWrite(address, struct.pack("<I", value), U32)

    def IoRead(self, address, access=U8):
        ioctl = 0x222810 + 8 * access
        request = struct.pack("<II", address, 0)
        result = self.d.IoCtl(ioctl, request, len(request))
        if result is not None:
            return struct.unpack("<I", result[4:8])[0]

    def IoRead8(self, address):
        return self.IoRead(address, U8)

    def IoRead16(self, address):
        return self.IoRead(address, U16)

    def IoRead32(self, address):
        return self.IoRead(address, U32)

    def IoWrite(self, address, value, access=U8):
        ioctl = 0x222814 + 8 * access
        request = struct.pack("<II", address, value)
        return self.d.IoCtl(ioctl, request, len(request)) is not None

    def IoWrite8(self, address, value):
        return self.IoWrite(address, value, U8)

    def IoWrite16(self, address, value):
        return self.IoWrite(address, value, U16)

    def IoWrite32(self, address, value):
        return self.IoWrite(address, value, U32)

    def CrRead(self, number):
        request = struct.pack("<IIQ", number, 0, 0)
        result = self.d.IoCtl(0x22286C, request, len(request))
        if result is not None:
            return struct.unpack("<Q", result[8:16])[0]

    def CrWrite(self, number, value):
        request = struct.pack("<IIQ", number, 0, value)
        return self.d.IoCtl(0x222870, request, len(request)) is not None

    def PciReadMm(self, bdfo, access=U8):
        if not self.pciMmAddress:
            return None
        if bdfo.b >= self.pciMmTopBus:
            raise ValueError("Above the max supported bus")
        if bdfo.d < 0 or bdfo.d >= 0x20 or bdfo.f < 0 or bdfo.f >= 0x8 or bdfo.o < 0 or bdfo.o >= 0x1000:
            raise ValueError("Bad Pci Address")
        addr = bdfo.mmOffset() + self.pciMmAddress
        if access == U8:
            return self.MemRead8(addr)
        elif access == U16:
            return self.MemRead16(addr)
        else:
            return self.MemRead32(addr)

    def PciRead(self, bdfo, access=U8):
        if self.pciMmAddress:
            return self.PciReadMm(bdfo, access)
        if bdfo.o >= 0x100:
            raise ValueError("Offset is above 0x100, consider switching to PciReadMm with DetectPciMm")
        if bdfo.d < 0 or bdfo.d >= 0x20 or bdfo.f < 0 or bdfo.f >= 0x8 or bdfo.o < 0:
            raise ValueError("Bad Pci Address")
        request = struct.pack("<BBBBHHI", bdfo.b, bdfo.d, bdfo.f, 0, bdfo.o, 0, 0)
        ioctl = 0x222830 + 8 * access
        result = self.d.IoCtl(ioctl, request, len(request))
        if result is not None:
            return struct.unpack("<I", result[8:12])[0]
    
    def PciRead8(self, bdfo):
        return self.PciRead(bdfo, U8)

    def PciRead16(self, bdfo):
        return self.PciRead(bdfo, U16)
    
    def PciRead32(self, bdfo):
        return self.PciRead(bdfo, U32)

    def PciRead64(self, bdfo):
        Hi = self.PciRead32(bdfo+4)
        Lo = self.PciRead32(bdfo)
        if Hi is None or Lo is None:
            return None
        return Lo | (Hi << 32)

    def PciWrite(self, bdfo, value, access=U8):
        request = struct.pack("<BBBBHHI", bdfo.b, bdfo.d, bdfo.f, 0, bdfo.o, 0, value)
        ioctl = 0x222834 + 8 * access
        return self.d.IoCtl(ioctl, request, len(request)) is not None

    def PciWrite8(self, bdfo, value):
        return self.PciWrite(bdfo, value, U8)

    def PciWrite16(self, bdfo, value):
        return self.PciWrite(bdfo, value, U16)
        
    def PciWrite32(self, bdfo, value):
        return self.PciWrite(bdfo, value, U32)

    def PciWrite64(self, bdfo, value):
        return self.PciWrite32(bdfo + 4, value >> 32) and self.PciWrite32(bdfo, value & 0xFFFFFFFF)

    def MsrRead(self, number):
        request = struct.pack("<IIII", 0, 0, number, 0)
        result = self.d.IoCtl(0x222848, request, len(request))
        if result is not None:
            (lo, pad, num, hi) = struct.unpack("<IIII", result)
            return lo | (hi << 32)

    def MsrWrite(self, number, value):
        request = struct.pack("<IIII", value & 0xFFFFFFFF, 0, number, value >> 32)
        return self.d.IoCtl(0x22284C, request, len(request)) is not None

    def TscRead(self):
        request = struct.pack("<Q", 0)
        result = self.d.IoCtl(0x222864, request, len(request))
        if result is not None:
            return struct.unpack("<Q", result[0:8])[0]

    def PmcRead(self, address):
        request = struct.pack("<IIQ", address, 0, 0)
        result = self.d.IoCtl(0x222868, request, len(request))
        if result is not None:
            return struct.unpack("<Q", result[8:16])[0]

    def CpuidRead(self, eax):
        request = struct.pack("<IIII", eax, 0, 0, 0)
        result = self.d.IoCtl(0x222850, request, len(request))
        if result is not None:
            return struct.unpack("<IIII", result)

    def PhysAlloc(self, size):
        request = struct.pack("<IIQ", size, 0, 0)
        result = self.d.IoCtl(0x222880, request, len(request))
        if result is not None:
            (s, p, v) = struct.unpack("<IIQ", result)
            return PhysVirtAddress(s, p, v)

    def PhysFree(self, pva):
        request = struct.pack("<IIQ", pva.sz, 0, pva.va)
        return self.d.IoCtl(0x222884, request, len(request)) is not None

    def PhysSearch(self, address, size, pattern, step=1, skip=0, backwards=0):
        patbuf = ctypes.c_buffer(pattern, len(pattern))
        request = struct.pack("<QIIIIQIIQ", address, size, step, skip, 0, ctypes.addressof(patbuf), len(pattern), backwards, 0)
        result = self.d.IoCtl(0x222894, request, len(request))
        if result is not None:
            return struct.unpack("<Q", result[0x28:0x30])[0]

    def DetectPciMm(self):
        if self.pciMmAddress is not None:
            return self.pciMmAddress
        self.pciMmAddress = 0
        rsdp = self.PhysSearch(0xE0000, 0x20000, b"RSD PTR ", step=0x10)
        if rsdp:
            #rsdp way, use rsdt only for simplicity
            rsdt = self.MemRead32(rsdp + 0x10)
            (rsdtSign, rsdtLen) = struct.unpack("<II", self.MemRead(rsdt, 8, U32))
            if rsdtSign == 0x54445352: #RSDT
                headerSize = 0x24
                rsdtData = self.MemRead(rsdt + headerSize, rsdtLen - headerSize, U32)
                for i in range(len(rsdtData) // 4):
                    pa = struct.unpack("<I", rsdtData[i*4:(i+1)*4])[0]
                    table = self.MemRead(pa, 0x40, U32)
                    if table[0:4] == b"MCFG":
                        #we have found the right table, parse it
                        (self.pciMmAddress, pciSeg, botBus, self.pciMmTopBus) = struct.unpack("<QHBB", table[0x2C:0x38])
        elif self.PciRead16(PciAddress(0,0,0,0)) == 0x8086:
            #try intel way
            pciexbar = self.PciRead64(PciAddress(0,0,0,0x60))
            if pciexbar & 1:
                self.pciMmTopBus = (1 << (8 - ((pciexbar >> 1) & 3))) - 1
                self.pciMmAddress = pciexbar & 0xFFFF0000
        return self.pciMmAddress