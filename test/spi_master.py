# Bit-banged SPI master for cocotb tests (mode 0, MSB first, 16-bit frames).
# Works on any set of pin accessors, so the same code drives a block-level
# spi_slave and the chip's ui_in/uo_out pins.

from cocotb.triggers import ClockCycles


class SpiMaster:
    def __init__(self, dut, set_sck, set_mosi, set_cs_n, get_miso, half_period=4):
        self.dut = dut
        self.set_sck, self.set_mosi, self.set_cs_n, self.get_miso = set_sck, set_mosi, set_cs_n, get_miso
        self.half = half_period           # clk cycles per half SCK period (>= 2)

    async def _xfer(self, rw, addr, data):
        frame = (rw << 15) | ((addr & 0x7F) << 8) | (data & 0xFF)
        self.set_cs_n(0)
        await ClockCycles(self.dut.clk, self.half)
        got = 0
        for i in range(15, -1, -1):
            self.set_mosi((frame >> i) & 1)
            await ClockCycles(self.dut.clk, self.half)
            self.set_sck(1)                                   # slave samples MOSI
            got = (got << 1) | self.get_miso()                # master samples MISO
            await ClockCycles(self.dut.clk, self.half)
            self.set_sck(0)
        await ClockCycles(self.dut.clk, self.half)
        self.set_cs_n(1)
        self.set_mosi(0)
        await ClockCycles(self.dut.clk, self.half)
        return got & 0xFF

    async def write(self, addr, data):
        await self._xfer(0, addr, data)

    async def read(self, addr):
        return await self._xfer(1, addr, 0)
