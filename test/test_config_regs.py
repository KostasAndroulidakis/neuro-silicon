# config_regs: RTL vs model under random bus traffic.   make BLOCK=config_regs
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly

from model import ConfigRegs, P


async def run(dut, cycles):
    model = ConfigRegs()
    for i, c in enumerate(cycles):
        await FallingEdge(dut.clk)
        dut.rst.value, dut.wr_en.value = c["rst"], c["wr_en"]
        dut.wr_addr.value, dut.wr_data.value, dut.rd_addr.value = c["wr_addr"], c["wr_data"], c["rd_addr"]
        dut.v_a.value, dut.v_b.value, dut.cnt_a.value, dut.cnt_b.value = *c["v"], *c["cnt"]
        model.step(c["rst"], c["wr_en"], c["wr_addr"], c["wr_data"])
        await RisingEdge(dut.clk)
        await ReadOnly()
        got = dict(en=int(dut.en.value), soft_rst=int(dut.soft_rst.value),
                   delay=int(dut.delay.value), tick_div=int(dut.tick_div.value),
                   cfg_a=int(dut.cfg_a.value), cfg_b=int(dut.cfg_b.value),
                   w_pack=int(dut.w_pack.value), rd_data=int(dut.rd_data.value))
        exp = dict(en=model.en, soft_rst=model.soft_rst, delay=model.delay,
                   tick_div=model.tick_div, cfg_a=model.cfg(0), cfg_b=model.cfg(1),
                   w_pack=model.w_pack, rd_data=model.read(c["rd_addr"], c["v"], c["cnt"]))
        assert got == exp, f"cycle {i}: {c}\n rtl  {got}\n model {exp}"
    return model


def idle(**kw):
    c = dict(rst=0, wr_en=0, wr_addr=0, wr_data=0, rd_addr=0, v=(0, 0), cnt=(0, 0))
    c.update(kw)
    return c


@cocotb.test()
async def reset_values_match_params(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    cycles = [idle(rst=1)] * 2 + [idle(rd_addr=a) for a in range(0x40)]
    model = await run(dut, cycles)
    assert model.en == 0 and model.thr[0] == P["NM_THR_RST"]


@cocotb.test()
async def soft_reset_is_one_pulse(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    cycles = [idle(rst=1)] * 2 + [idle(wr_en=1, wr_addr=P["NM_REG_CTRL"], wr_data=0b11)] + [idle()] * 3
    await run(dut, cycles)


@cocotb.test()
async def random_bus(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    rng = random.Random(9)
    cycles = [idle(rst=1)] * 2
    for _ in range(4000):
        cycles.append(idle(rst=int(rng.random() < 0.002),
                           wr_en=int(rng.random() < 0.3),
                           wr_addr=rng.randrange(128), wr_data=rng.randrange(256),
                           rd_addr=rng.randrange(128),
                           v=(rng.randrange(4096), rng.randrange(4096)),
                           cnt=(rng.randrange(256), rng.randrange(256))))
    await run(dut, cycles)
