# neuron_seq: RTL vs golden model, cycle by cycle, plus directed checks.
# Run with:  make BLOCK=neuron_seq

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly

from model import NeuronSeq, P


def cfg_word(thr, leak, disable=0):
    return (disable << 19) | (leak << 12) | thr


def w_pack(w):                      # w = [a1, a2, b1, b2], signed
    return sum(((wi & 0xF) << (4 * i)) for i, wi in enumerate(w))


class Stim:
    """Builds a per-cycle stimulus list with a time_ref every `period` cycles."""

    def __init__(self, period=8, thr=10, leak=1, w=(7, 7, 7, 7)):
        self.period, self.cycles = period, []
        self.cfg = [cfg_word(thr, leak), cfg_word(thr, leak)]
        self.w = list(w)
        self.en, self.soft_rst = 1, 0

    def cycle(self, in_syn=0, **kw):
        c = dict(rst=0, en=self.en, soft_rst=self.soft_rst, time_ref=0,
                 in_syn=in_syn, w=list(self.w), cfg=list(self.cfg))
        c.update(kw)
        self.cycles.append(c)
        return self

    def ticks(self, n, in_syn_at_tick=0):
        """n full periods; in_syn pulses are injected 2 cycles before each tick."""
        for _ in range(n):
            for c in range(self.period):
                tr = int(c == self.period - 1)
                inj = in_syn_at_tick if c == self.period - 3 else 0
                self.cycle(in_syn=inj, time_ref=tr)
        return self


async def run(dut, cycles):
    model = NeuronSeq()
    spikes = [0, 0]
    for i, c in enumerate(cycles):
        await FallingEdge(dut.clk)
        dut.rst.value, dut.en.value, dut.soft_rst.value = c["rst"], c["en"], c["soft_rst"]
        dut.time_ref.value, dut.in_syn.value = c["time_ref"], c["in_syn"]
        dut.w_pack.value = w_pack(c["w"])
        dut.cfg_a.value, dut.cfg_b.value = c["cfg"]
        exp = model.step(c["rst"], c["en"], c["soft_rst"], c["time_ref"],
                         c["in_syn"], c["w"], c["cfg"])
        await RisingEdge(dut.clk)
        await ReadOnly()
        got = (int(dut.spike_a.value), int(dut.spike_b.value))
        assert got == exp, f"cycle {i}: spikes rtl={got} model={exp} ({c})"
        assert int(dut.v_a.value) == model.v[0] and int(dut.v_b.value) == model.v[1], \
            f"cycle {i}: v rtl=({int(dut.v_a.value)},{int(dut.v_b.value)}) model={model.v}"
        assert (int(dut.cnt_a.value), int(dut.cnt_b.value)) == tuple(model.cnt), \
            f"cycle {i}: counters rtl=({int(dut.cnt_a.value)},{int(dut.cnt_b.value)}) model={model.cnt}"
        spikes[0] += got[0]
        spikes[1] += got[1]
    return model, spikes


def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())


@cocotb.test()
async def coincidence_fires_isolated_does_not(dut):
    """thr=10, w=7, leak=1: an isolated spike (7 < 10) decays away without firing;
    two spikes on different synapses in the same tick (14 >= 10) fire."""
    start(dut)
    s = Stim().cycle(rst=1).cycle(rst=1)
    for _ in range(5):
        s.ticks(1, in_syn_at_tick=0b0001).ticks(8)     # a1 alone, then 8 ticks of decay
    for _ in range(5):
        s.ticks(1, in_syn_at_tick=0b0011).ticks(8)     # a1 + a2 together
    for _ in range(5):
        s.ticks(1, in_syn_at_tick=0b1100).ticks(8)     # b1 + b2 together
    s.ticks(1)                                         # let the last tick finish
    _, spikes = await run(dut, s.cycles)
    assert spikes == [5, 5], f"spike counts {spikes}, expected [5, 5]"


@cocotb.test()
async def weak_inputs_sum_only_if_close(dut):
    """w=4, thr=10, leak=1: two spikes on the same synapse at consecutive ticks sum
    (4 + 4 - 1 = 7 < 10, no), three do (7 + 4 - 1 = 10 >= 10, yes)."""
    start(dut)
    s = Stim(w=(4, 4, 4, 4)).cycle(rst=1).cycle(rst=1)
    s.ticks(2, in_syn_at_tick=0b0001).ticks(3)     # 2 spikes then rest: no fire
    s.ticks(3, in_syn_at_tick=0b0001).ticks(3)     # 3 spikes in a row: fires once
    _, spikes = await run(dut, s.cycles)
    assert spikes == [1, 0], f"spike counts {spikes}, expected [1, 0]"


@cocotb.test()
async def disabled_neuron_is_silent(dut):
    start(dut)
    s = Stim().cycle(rst=1).cycle(rst=1)
    s.cfg[0] = cfg_word(10, 1, disable=1)
    s.ticks(5, in_syn_at_tick=0b0011)
    model, spikes = await run(dut, s.cycles)
    assert spikes == [0, 0]
    assert model.v[0] == 0, "state must still reset after an (unemitted) spike"


@cocotb.test()
async def soft_reset_clears_state_keeps_running(dut):
    start(dut)
    s = Stim(w=(4, 4, 4, 4)).cycle(rst=1).cycle(rst=1)
    s.ticks(2, in_syn_at_tick=0b0001)          # v_a = 7
    s.soft_rst = 1; s.cycle(); s.soft_rst = 0  # clear
    s.ticks(2, in_syn_at_tick=0b0001).ticks(2) # only 2 more: must NOT fire (would with 4)
    _, spikes = await run(dut, s.cycles)
    assert spikes == [0, 0]


@cocotb.test()
async def random_stimulus(dut):
    """Random spikes, weights (incl. inhibitory), thresholds, leaks, enable, soft
    reset, and tick periods: RTL and model must agree on every cycle."""
    start(dut)
    rng = random.Random(7)
    cycles = [dict(rst=1, en=0, soft_rst=0, time_ref=0, in_syn=0, w=[0] * 4, cfg=[0, 0])] * 2
    w = [7, 7, 7, 7]
    cfg = [cfg_word(10, 1), cfg_word(10, 1)]
    en, cnt, period = 1, 0, 8
    for _ in range(6000):
        if rng.random() < 0.01:
            w = [rng.randint(-8, 7) for _ in range(4)]
        if rng.random() < 0.01:
            cfg = [cfg_word(rng.randint(1, 40), rng.randint(0, 5), int(rng.random() < 0.1))
                   for _ in range(2)]
        if rng.random() < 0.005:
            en = 1 - en
        if rng.random() < 0.01:
            period = rng.choice([8, 9, 12, 20])
        cnt += 1
        tr = int(cnt >= period)
        if tr:
            cnt = 0
        cycles.append(dict(rst=0, en=en, soft_rst=int(rng.random() < 0.002), time_ref=tr,
                           in_syn=rng.getrandbits(4) if rng.random() < 0.3 else 0,
                           w=list(w), cfg=list(cfg)))
    await run(dut, cycles)
