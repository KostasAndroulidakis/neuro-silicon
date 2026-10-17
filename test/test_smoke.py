# Top-level tests on the Tiny Tapeout wrapper (also run at gate level by CI).
# Block-level tests live in test_<block>.py.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

from model import P
from spi_master import SpiMaster

# ui_in bit map (info.yaml)
SENSOR_L, SENSOR_R, SCK, MOSI, CS_N = 0, 1, 2, 3, 4
# uo_out bit map
DIR_LR, DIR_RL, MISO, SPIKE_A, SPIKE_B, TIME_REF = 0, 1, 2, 3, 4, 5


_ui_in = {}          # shadow of ui_in: cocotb applies writes later, so never read back


def set_in(dut, bit, v):
    cur = _ui_in.get(id(dut), 0)
    cur = (cur & ~(1 << bit)) | (v << bit)
    _ui_in[id(dut)] = cur
    dut.ui_in.value = cur


def out_bit(dut, bit):
    return (int(dut.uo_out.value) >> bit) & 1


def spi(dut):
    return SpiMaster(dut,
                     lambda v: set_in(dut, SCK, v),
                     lambda v: set_in(dut, MOSI, v),
                     lambda v: set_in(dut, CS_N, v),
                     lambda: out_bit(dut, MISO), half_period=4)


async def reset(dut):
    dut.ena.value = 1
    _ui_in[id(dut)] = 1 << CS_N          # SPI idle, sensors low
    dut.ui_in.value = 1 << CS_N
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 3)        # 2-FF reset synchroniser


async def start(dut, enable=True):
    cocotb.start_soon(Clock(dut.clk, 100, unit="us").start())   # 10 kHz
    await reset(dut)
    m = spi(dut)
    if enable:
        await m.write(P["NM_REG_CTRL"], 0b01)
    return m


async def count_dir(dut, cycles):
    lr = rl = 0
    for _ in range(cycles):
        await ClockCycles(dut.clk, 1)
        lr += out_bit(dut, DIR_LR)
        rl += out_bit(dut, DIR_RL)
    return lr, rl


@cocotb.test()
async def spi_id_and_register_roundtrip(dut):
    """The SPI link works: ID reads back, a written register reads back, the
    rest of the map shows its reset values."""
    m = await start(dut, enable=False)
    assert await m.read(P["NM_REG_ID"]) == P["NM_ID"]
    assert await m.read(P["NM_REG_TICK_DIV"]) == P["NM_TICK_DIV_RST"]
    assert await m.read(P["NM_REG_NEUR_A"] + 2) == P["NM_THR_RST"] >> 4
    await m.write(P["NM_REG_W_A"], 0x3D)
    assert await m.read(P["NM_REG_W_A"]) == 0x3D
    assert await m.read(P["NM_REG_W_B"]) == ((P["NM_W_RST"] & 0xF) << 4) | (P["NM_W_RST"] & 0xF)


@cocotb.test()
async def frozen_until_enabled(dut):
    """Before CTRL.EN: no time_ref, no spikes, whatever the sensors do."""
    await start(dut, enable=False)
    set_in(dut, SENSOR_L, 1); set_in(dut, SENSOR_R, 1)
    for _ in range(4 * P["NM_TICK_DIV_RST"]):
        await ClockCycles(dut.clk, 1)
        assert (int(dut.uo_out.value) & 0b111011) == 0, "chip must be silent while EN=0"
        assert dut.uio_oe.value == 0


@cocotb.test()
async def time_ref_runs_at_reset_period(dut):
    await start(dut)
    period = P["NM_TICK_DIV_RST"]

    async def wait_pulse():
        n = 0
        while True:
            await ClockCycles(dut.clk, 1)
            n += 1
            if out_bit(dut, TIME_REF):
                return n
            assert n <= period + 2, "no time_ref pulse"

    await wait_pulse()
    for i in range(10):
        gap = await wait_pulse()
        assert gap == period, f"pulse {i}: gap {gap}, expected {period}"


async def move_object(dut, first, second, gap_ticks, hold=4):
    period = P["NM_TICK_DIV_RST"]
    set_in(dut, first, 1)
    await ClockCycles(dut.clk, hold)
    set_in(dut, first, 0)
    await ClockCycles(dut.clk, gap_ticks * period - hold)
    set_in(dut, second, 1)
    await ClockCycles(dut.clk, hold)
    set_in(dut, second, 0)


@cocotb.test()
async def detects_motion_direction(dut):
    """L then R (DELAY ticks apart) -> dir_lr only; R then L -> dir_rl only.
    Afterwards the spike counters and membrane potentials read back over SPI."""
    m = await start(dut)
    period, delay = P["NM_TICK_DIV_RST"], P["NM_DELAY_RST"]

    cocotb.start_soon(move_object(dut, SENSOR_L, SENSOR_R, delay))
    assert await count_dir(dut, (delay + 6) * period) == (1, 0)
    await ClockCycles(dut.clk, 6 * period)
    cocotb.start_soon(move_object(dut, SENSOR_R, SENSOR_L, delay))
    assert await count_dir(dut, (delay + 6) * period) == (0, 1)

    assert await m.read(P["NM_REG_CNT_A"]) == 1
    assert await m.read(P["NM_REG_CNT_B"]) == 1
    await m.write(P["NM_REG_CTRL"], 0b11)               # SOFT_RST (EN stays 1)
    assert await m.read(P["NM_REG_CNT_A"]) == 0
    assert await m.read(P["NM_REG_NEUR_A"]) == 0        # v_a cleared


@cocotb.test()
async def retuned_over_spi(dut):
    """Raise the threshold so a coincidence no longer fires, then lower it back."""
    m = await start(dut)
    period, delay = P["NM_TICK_DIV_RST"], P["NM_DELAY_RST"]
    await m.write(P["NM_REG_NEUR_A"] + 2, 0x02)         # thr_a = 0x020 = 32 > 14
    cocotb.start_soon(move_object(dut, SENSOR_L, SENSOR_R, delay))
    assert await count_dir(dut, (delay + 6) * period) == (0, 0)
    await m.write(P["NM_REG_NEUR_A"] + 2, 0x00)         # thr_a back to 10
    await m.write(P["NM_REG_NEUR_A"] + 1, 0xA0)
    await ClockCycles(dut.clk, 4 * period)
    cocotb.start_soon(move_object(dut, SENSOR_L, SENSOR_R, delay))
    assert await count_dir(dut, (delay + 6) * period) == (1, 0)


@cocotb.test()
async def wrong_spacing_does_not_fire(dut):
    await start(dut)
    period, delay = P["NM_TICK_DIV_RST"], P["NM_DELAY_RST"]
    cocotb.start_soon(move_object(dut, SENSOR_L, SENSOR_R, delay + 6))
    assert await count_dir(dut, (2 * delay + 14) * period) == (0, 0)
