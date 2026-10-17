# Smoke test: the wrapper comes out of reset with all outputs idle.
# This exists so the CI pipeline is green from the first commit; real block
# tests are added one file per block (test_lif.py, test_delay.py, ...).

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

from model import P


async def reset(dut):
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)   # let the 2-FF reset synchroniser settle


@cocotb.test()
async def outputs_idle_after_reset(dut):
    cocotb.start_soon(Clock(dut.clk, 100, unit="us").start())   # 10 kHz
    await reset(dut)

    for _ in range(20):
        await ClockCycles(dut.clk, 1)
        assert (int(dut.uo_out.value) & 0x1F) == 0, "no spikes expected without input"
        assert dut.uio_oe.value == 0, "bidirectional pins must stay inputs"


@cocotb.test()
async def time_ref_runs_at_reset_period(dut):
    """uo_out[5] (time_ref) pulses every NM_TICK_DIV_RST cycles after reset."""
    cocotb.start_soon(Clock(dut.clk, 100, unit="us").start())
    await reset(dut)
    period = P["NM_TICK_DIV_RST"]

    async def wait_pulse():
        n = 0
        while True:
            await ClockCycles(dut.clk, 1)
            n += 1
            if (int(dut.uo_out.value) >> 5) & 1:
                return n
            assert n <= period + 2, "no time_ref pulse"

    await wait_pulse()                       # align to the first pulse
    for i in range(10):
        gap = await wait_pulse()
        assert gap == period, f"pulse {i}: gap {gap} cycles, expected {period}"
