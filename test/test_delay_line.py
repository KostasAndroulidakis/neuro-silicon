# delay_line: RTL vs model, plus directed checks.   make BLOCK=delay_line
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly

from model import DelayLine, P

PERIOD = P["NM_TICK_DIV_RST"]


async def run(dut, cycles):
    """cycles: list of dicts(rst, en, soft_rst, time_ref, delay, spike_in).
    Returns the list of ticks (tick index) at which `out` pulsed."""
    model = DelayLine()
    out_ticks, tick = [], -1
    for i, c in enumerate(cycles):
        await FallingEdge(dut.clk)
        dut.rst.value, dut.en.value, dut.soft_rst.value = c["rst"], c["en"], c["soft_rst"]
        dut.time_ref.value, dut.delay.value = c["time_ref"], c["delay"]
        getattr(dut, "in").value = c["spike_in"]
        exp = model.step(c["rst"], c["en"], c["soft_rst"], c["time_ref"], c["delay"], c["spike_in"])
        await ReadOnly()                       # out is combinational: check before the edge
        got = int(dut.out.value)
        assert got == exp, f"cycle {i}: out rtl={got} model={exp} ({c})"
        if c["time_ref"]:
            tick += 1
        if got:
            out_ticks.append(tick)
        await RisingEdge(dut.clk)
    return out_ticks


def make(delay, spikes_at, n_ticks, period=PERIOD):
    """Tick t occupies cycles [t*period, (t+1)*period); time_ref on its last cycle.
    spikes_at: {tick: offset_within_tick} where to inject a spike."""
    cycles = [dict(rst=1, en=0, soft_rst=0, time_ref=0, delay=delay, spike_in=0)] * 2
    for t in range(n_ticks):
        for c in range(period):
            cycles.append(dict(rst=0, en=1, soft_rst=0, time_ref=int(c == period - 1),
                               delay=delay, spike_in=int(spikes_at.get(t) == c)))
    return cycles


@cocotb.test()
async def delay_n_means_n_ticks_later(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for d in (0, 1, 3, 15):
        out = await run(dut, make(d, {2: 1}, 25))
        assert out == [2 + d], f"delay {d}: out at ticks {out}, expected [{2 + d}]"


@cocotb.test()
async def spike_in_tick_cycle_counts_for_that_tick(dut):
    """A spike arriving in the very cycle of time_ref belongs to that tick (same rule
    as a direct path into neuron_seq), with any delay."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for d in (0, 2):
        out = await run(dut, make(d, {4: PERIOD - 1}, 20))
        assert out == [4 + d], f"delay {d}: out at ticks {out}"


@cocotb.test()
async def queue_holds_several_spikes(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    out = await run(dut, make(5, {1: 0, 2: 3, 3: 6}, 20))
    assert out == [6, 7, 8], f"out at ticks {out}"


@cocotb.test()
async def random_stimulus(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    rng = random.Random(11)
    cycles = [dict(rst=1, en=0, soft_rst=0, time_ref=0, delay=0, spike_in=0)] * 2
    cnt, period, delay, en = 0, 8, 2, 1
    for _ in range(5000):
        if rng.random() < 0.01:
            delay = rng.randint(0, 15)
        if rng.random() < 0.005:
            en = 1 - en
        if rng.random() < 0.01:
            period = rng.choice([8, 9, 13])
        cnt += 1
        tr = int(cnt >= period)
        cnt = 0 if tr else cnt
        cycles.append(dict(rst=0, en=en, soft_rst=int(rng.random() < 0.002), time_ref=tr,
                           delay=delay, spike_in=int(rng.random() < 0.15)))
    await run(dut, cycles)
