# edge_detect: RTL vs model, plus directed checks.   make BLOCK=edge_detect
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly

from model import EdgeDetect


async def run(dut, levels, rst_cycles=2):
    model = EdgeDetect()
    pulses = 0
    seq = [(1, 0)] * rst_cycles + [(0, l) for l in levels]
    for i, (rst, lvl) in enumerate(seq):
        await FallingEdge(dut.clk)
        dut.rst.value, dut.level.value = rst, lvl
        exp = model.step(rst, lvl)
        await RisingEdge(dut.clk)
        await ReadOnly()
        got = int(dut.pulse.value)
        assert got == exp, f"cycle {i}: rtl={got} model={exp}"
        pulses += got
    return pulses


@cocotb.test()
async def one_pulse_per_rising_edge(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    levels = [0] * 5 + [1] * 50 + [0] * 5 + [1] * 1 + [0] * 5 + [1] * 3 + [0] * 5
    assert await run(dut, levels) == 3


@cocotb.test()
async def random_levels(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    rng = random.Random(3)
    lvl, levels = 0, []
    for _ in range(3000):
        if rng.random() < 0.1:
            lvl ^= 1
        levels.append(lvl)
    await run(dut, levels)
