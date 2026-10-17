# Top-level tests on the Tiny Tapeout wrapper (also run at gate level by CI).
# Block-level tests live in test_<block>.py.

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


async def move_object(dut, first, second, gap_ticks, hold=4):
    """Object passes: `first` sensor goes high, then `second` gap_ticks later."""
    period = P["NM_TICK_DIV_RST"]
    first.value = 1
    await ClockCycles(dut.clk, hold)
    first.value = 0
    await ClockCycles(dut.clk, gap_ticks * period - hold)
    second.value = 1
    await ClockCycles(dut.clk, hold)
    second.value = 0


async def count_dir(dut, cycles):
    lr = rl = 0
    for _ in range(cycles):
        await ClockCycles(dut.clk, 1)
        v = int(dut.uo_out.value)
        lr += v & 1
        rl += (v >> 1) & 1
    return lr, rl


@cocotb.test()
async def detects_motion_direction(dut):
    """L then R (DELAY ticks apart) -> dir_lr only; R then L -> dir_rl only."""
    cocotb.start_soon(Clock(dut.clk, 100, unit="us").start())
    await reset(dut)
    period, delay = P["NM_TICK_DIV_RST"], P["NM_DELAY_RST"]

    # ui_in bit 0 = sensor_l, bit 1 = sensor_r: drive the whole vector via helpers
    class Pin:
        def __init__(self, bit): self.bit = bit
        @property
        def value(self): return (int(dut.ui_in.value) >> self.bit) & 1
        @value.setter
        def value(self, v):
            cur = int(dut.ui_in.value)
            dut.ui_in.value = (cur & ~(1 << self.bit)) | (v << self.bit)
    sensor_l, sensor_r = Pin(0), Pin(1)

    cocotb.start_soon(move_object(dut, sensor_l, sensor_r, delay))
    lr, rl = await count_dir(dut, (delay + 6) * period)
    assert (lr, rl) == (1, 0), f"L->R: dir_lr={lr} dir_rl={rl}"

    await ClockCycles(dut.clk, 6 * period)          # let everything decay
    cocotb.start_soon(move_object(dut, sensor_r, sensor_l, delay))
    lr, rl = await count_dir(dut, (delay + 6) * period)
    assert (lr, rl) == (0, 1), f"R->L: dir_lr={lr} dir_rl={rl}"


@cocotb.test()
async def wrong_spacing_does_not_fire(dut):
    """Same direction but far outside the delay window: no detection."""
    cocotb.start_soon(Clock(dut.clk, 100, unit="us").start())
    await reset(dut)
    period, delay = P["NM_TICK_DIV_RST"], P["NM_DELAY_RST"]

    async def mover():
        dut.ui_in.value = 0b01
        await ClockCycles(dut.clk, 4)
        dut.ui_in.value = 0
        await ClockCycles(dut.clk, (delay + 6) * period)   # way too late
        dut.ui_in.value = 0b10
        await ClockCycles(dut.clk, 4)
        dut.ui_in.value = 0

    cocotb.start_soon(mover())
    lr, rl = await count_dir(dut, (2 * delay + 14) * period)
    assert (lr, rl) == (0, 0), f"dir_lr={lr} dir_rl={rl}"
