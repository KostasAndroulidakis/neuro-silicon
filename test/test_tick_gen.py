# tick_gen: RTL vs golden model, cycle by cycle.
# Run with:  make BLOCK=tick_gen

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly

from model import TickGen, P


async def run_and_compare(dut, stimulus):
    """stimulus: list of (rst, en, tick_div) per cycle. Compares time_ref every cycle."""
    model = TickGen()
    for cycle, (rst, en, div) in enumerate(stimulus):
        await FallingEdge(dut.clk)          # drive inputs away from the sampling edge
        dut.rst.value, dut.en.value, dut.tick_div.value = rst, en, div
        expected = model.step(rst, en, div)
        await RisingEdge(dut.clk)           # the RTL samples here...
        await ReadOnly()                    # ...and outputs are stable now
        got = int(dut.time_ref.value)
        assert got == expected, (
            f"cycle {cycle}: rst={rst} en={en} div={div}: rtl={got} model={expected}")
    return model


@cocotb.test()
async def fixed_periods(dut):
    """Each tick_div (including clamped ones) gives one pulse per period."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for div in (0, 1, P["NM_TICK_DIV_MIN"], P["NM_TICK_DIV_MIN"] + 1, 20, 255):
        stim = [(1, 0, div)] * 3 + [(0, 1, div)] * 600
        await run_and_compare(dut, stim)


@cocotb.test()
async def pulse_count_matches_period(dut):
    """Count pulses directly over a long window: a check the model cannot bias."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for div in (P["NM_TICK_DIV_MIN"], 10, 50):
        await FallingEdge(dut.clk)
        dut.rst.value, dut.en.value, dut.tick_div.value = 1, 0, div
        for _ in range(3):
            await FallingEdge(dut.clk)
        dut.rst.value, dut.en.value = 0, 1
        pulses = 0
        n = div * 20
        for _ in range(n):
            await RisingEdge(dut.clk)
            await ReadOnly()
            pulses += int(dut.time_ref.value)
        assert pulses == 20, f"div={div}: {pulses} pulses in {n} cycles, expected 20"


@cocotb.test()
async def disabled_is_silent(dut):
    """en = 0 produces no pulses and restarts the period cleanly when re-enabled."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    div = 10
    stim = [(1, 0, div)] * 2 + [(0, 1, div)] * 25 + [(0, 0, div)] * 40 + [(0, 1, div)] * 25
    await run_and_compare(dut, stim)


@cocotb.test()
async def random_stimulus(dut):
    """Random en/tick_div changes mid-run: model and RTL must still agree."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    rng = random.Random(1)
    stim = [(1, 0, 8)] * 2
    for _ in range(2000):
        stim.append((0, rng.random() < 0.9, rng.choice([0, 3, 8, 9, 12, 31, 200])))
    await run_and_compare(dut, stim)
