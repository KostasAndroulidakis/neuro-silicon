# spi_slave: protocol checks against a bit-banged master.   make BLOCK=spi_slave
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

from spi_master import SpiMaster


def master(dut, half=4):
    return SpiMaster(dut,
                     lambda v: setattr(dut.sck, "value", v),
                     lambda v: setattr(dut.mosi, "value", v),
                     lambda v: setattr(dut.cs_n, "value", v),
                     lambda: int(dut.miso.value), half)


async def setup(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.sck.value = dut.mosi.value = 0
    dut.cs_n.value = 1
    dut.rd_data.value = 0
    dut.rst.value = 1
    await ClockCycles(dut.clk, 3)
    dut.rst.value = 0
    await ClockCycles(dut.clk, 3)

    async def fake_regs():            # rd_data = f(rd_addr), like config_regs would
        while True:
            await RisingEdge(dut.clk)
            dut.rd_data.value = (int(dut.rd_addr.value) * 37 + 0x5A) & 0xFF
    cocotb.start_soon(fake_regs())

    writes = []

    async def catch_writes():
        while True:
            await RisingEdge(dut.clk)
            if int(dut.wr_en.value):
                writes.append((int(dut.wr_addr.value), int(dut.wr_data.value)))
    cocotb.start_soon(catch_writes())
    return writes


@cocotb.test()
async def write_then_read(dut):
    writes = await setup(dut)
    m = master(dut)
    await m.write(0x03, 0xC7)
    await m.write(0x7F, 0x01)
    assert writes == [(0x03, 0xC7), (0x7F, 0x01)], writes
    for addr in (0x00, 0x10, 0x31, 0x7F):
        got = await m.read(addr)
        assert got == (addr * 37 + 0x5A) & 0xFF, f"read {addr:#x}: {got:#x}"
    assert len(writes) == 2, "reads must not produce writes"


@cocotb.test()
async def slow_and_fast_sck(dut):
    """Any SCK at or below clk/8 must work identically."""
    writes = await setup(dut)
    for half in (4, 5, 7, 20):
        m = master(dut, half)
        await m.write(0x20, half)
        assert writes[-1] == (0x20, half), (half, writes[-1])
        assert await m.read(0x05) == (5 * 37 + 0x5A) & 0xFF


@cocotb.test()
async def aborted_frame_writes_nothing(dut):
    writes = await setup(dut)
    m = master(dut)
    # 12 of 16 bits, then CS_n released
    frame = (0 << 15) | (0x02 << 8) | 0xFF
    dut.cs_n.value = 0
    for i in range(15, 3, -1):
        dut.mosi.value = (frame >> i) & 1
        await ClockCycles(dut.clk, 4); dut.sck.value = 1
        await ClockCycles(dut.clk, 4); dut.sck.value = 0
    dut.cs_n.value = 1
    await ClockCycles(dut.clk, 10)
    assert writes == [], writes
    await m.write(0x02, 0x05)                  # next frame still works
    assert writes == [(0x02, 0x05)]


@cocotb.test()
async def extra_clocks_are_ignored(dut):
    writes = await setup(dut)
    frame = (0 << 15) | (0x21 << 8) | 0x33
    dut.cs_n.value = 0
    for i in range(15, -1, -1):
        dut.mosi.value = (frame >> i) & 1
        await ClockCycles(dut.clk, 4); dut.sck.value = 1
        await ClockCycles(dut.clk, 4); dut.sck.value = 0
    for _ in range(9):                         # junk clocks with MOSI = 1
        dut.mosi.value = 1
        await ClockCycles(dut.clk, 4); dut.sck.value = 1
        await ClockCycles(dut.clk, 4); dut.sck.value = 0
    dut.cs_n.value = 1
    await ClockCycles(dut.clk, 10)
    assert writes == [(0x21, 0x33)], writes


@cocotb.test()
async def random_transactions(dut):
    writes = await setup(dut)
    rng = random.Random(5)
    expected = []
    m = master(dut, 4)
    for _ in range(60):
        addr = rng.randrange(128)
        if rng.random() < 0.5:
            data = rng.randrange(256)
            await m.write(addr, data)
            expected.append((addr, data))
        else:
            assert await m.read(addr) == (addr * 37 + 0x5A) & 0xFF
    assert writes == expected
