# Smoke test: the wrapper comes out of reset with all outputs idle.
# This exists so the CI pipeline is green from the first commit; real block
# tests are added one file per block (test_lif.py, test_delay.py, ...).

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


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
        assert dut.uo_out.value == 0, "no spikes expected without input"
        assert dut.uio_oe.value == 0, "bidirectional pins must stay inputs"
