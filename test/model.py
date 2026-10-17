"""Bit-accurate Python golden model of neuro-silicon.

One class per RTL block, each advanced one clk cycle at a time with step(), so any
stimulus sequence can be replayed against the RTL and compared cycle by cycle.
Constants come from src/nm_params.vh (parsed, not copied).
"""

import re
from pathlib import Path

_PARAMS_FILE = Path(__file__).resolve().parent.parent / "src" / "nm_params.vh"


def _parse_literal(text: str) -> int:
    """Verilog literal -> int.  Accepts 8'd100, 4'sd7, 8'hA5, 12'd10, 6, 1'b1."""
    text = text.strip()
    m = re.fullmatch(r"(\d+)'(s?)([bodh])([0-9a-fA-F_]+)", text)
    if not m:
        return int(text)
    width, signed, base, digits = m.groups()
    value = int(digits.replace("_", ""), {"b": 2, "o": 8, "d": 10, "h": 16}[base])
    if signed and value >= 1 << (int(width) - 1):
        value -= 1 << int(width)
    return value


def load_params(path: Path = _PARAMS_FILE) -> dict:
    """Return {name: int} for every `define NM_* in nm_params.vh."""
    params = {}
    for line in path.read_text().splitlines():
        m = re.match(r"\s*`define\s+(NM_\w+)\s+([^/]+)", line)
        if m:
            params[m.group(1)] = _parse_literal(m.group(2))
    return params


P = load_params()


class TickGen:
    """Mirror of src/tick_gen.v.

    Emits time_ref = 1 for one clk cycle every max(tick_div, NM_TICK_DIV_MIN) cycles
    while en = 1. Disabled or in reset: counter cleared, no pulses.
    """

    def __init__(self):
        self.cnt = 0
        self.time_ref = 0

    def step(self, rst: int, en: int, tick_div: int) -> int:
        period = max(tick_div, P["NM_TICK_DIV_MIN"])
        if rst or not en:
            self.cnt, self.time_ref = 0, 0
        elif self.cnt == period - 1:
            self.cnt, self.time_ref = 0, 1
        else:
            self.cnt, self.time_ref = self.cnt + 1, 0
        return self.time_ref


# ----------------------------------------------------------------------------
# tinyODIN lif_neuron.v, ported line by line (12-bit state, 4-bit signed weight)
# ----------------------------------------------------------------------------

_MASK12 = 0xFFF


def lif_update(state: int, leak_str: int, thr: int, w: int,
               syn_event: int, time_ref: int) -> tuple[int, int]:
    """Return (state_next, spike_out) exactly as src/lif_neuron.v computes them.

    state: 12-bit raw value (bit 11 = sign).  w: signed int -8..7.
    """
    w_ext = w & _MASK12                      # sign-extend 4 -> 12 bits
    event_leak = syn_event & time_ref
    event_syn = syn_event & (1 - time_ref)

    leakn_ovfl = (state - leak_str) & _MASK12
    leakn = 0 if leakn_ovfl >> 11 else leakn_ovfl
    leakp_ovfl = (state + leak_str) & _MASK12
    leakp = 0 if not (leakp_ovfl >> 11) else leakp_ovfl
    syn_ovfl = (state + w_ext) & _MASK12
    s11, w11, o11 = state >> 11, w_ext >> 11, syn_ovfl >> 11
    if (not o11) and s11 and w11:
        syn = 0x800                          # negative saturation
    elif o11 and (not s11) and (not w11):
        syn = 0x7FF                          # positive saturation
    else:
        syn = syn_ovfl

    if event_leak:
        nxt = leakp if (state >> 11) else leakn
    elif event_syn:
        nxt = syn
    else:
        nxt = state

    spike = int((not (nxt >> 11)) and nxt >= thr)
    return (0 if spike else nxt), spike


class NeuronSeq:
    """Mirror of src/neuron_seq.v: 2 neurons, 6 slots per time_ref tick."""

    SLOTS = ((0, 0, 0), (0, 0, 1), (0, 1, 0),   # (neuron, is_leak, syn_idx)
             (1, 0, 2), (1, 0, 3), (1, 1, 0))

    def __init__(self):
        self.active, self.slot, self.pending = 0, 0, 0
        self.v = [0, 0]
        self.spike = [0, 0]
        self.cnt = [0, 0]

    def step(self, rst, en, soft_rst, time_ref, in_syn, w, cfg):
        """in_syn: 4-bit int {b2,b1,a2,a1}. w: list of 4 signed ints.
        cfg: list of 2 ints (20-bit neuron word bits [31:12]).
        Returns (spike_a, spike_b) for this cycle."""
        if rst or soft_rst:
            self.__init__()
            return 0, 0

        n, is_leak, idx = self.SLOTS[self.slot]
        pend = (self.pending >> idx) & 1
        consume = self.active and not is_leak and pend
        syn_event = self.active and (is_leak or pend)
        c = cfg[n]
        state_next, spike_out = lif_update(
            self.v[n], (c >> 12) & 0x7F, c & 0xFFF, w[idx], int(syn_event), is_leak)
        fire = syn_event and spike_out and not (c >> 19)

        # registers
        self.pending = (self.pending & ~((1 << idx) if consume else 0)) | (in_syn if en else 0)
        if not self.active:
            if time_ref and en:
                self.active, self.slot = 1, 0
        else:
            self.v[n] = state_next
            if self.slot == P["NM_SEQ_CYCLES"] - 1:
                self.active = 0
            else:
                self.slot += 1
        self.spike = [int(fire and n == 0), int(fire and n == 1)]
        if fire:
            self.cnt[n] = (self.cnt[n] + 1) & 0xFF
        return self.spike[0], self.spike[1]


class EdgeDetect:
    """Mirror of src/edge_detect.v: 2-FF synchroniser + rising-edge pulse."""

    def __init__(self):
        self.sync0 = self.sync1 = self.prev = 0

    def step(self, rst: int, level: int) -> int:
        """Advance one clk. Returns `pulse` as seen *after* this clock edge."""
        if rst:
            self.sync0 = self.sync1 = self.prev = 0
        else:
            self.sync0, self.sync1, self.prev = level, self.sync0, self.sync1
        return int(self.sync1 and not self.prev)


class DelayLine:
    """Mirror of src/delay_line.v. step() returns `out` for the cycle being applied
    (combinational from time_ref and the pre-edge registers)."""

    DEPTH = 1 << P["NM_DELAY_W"]

    def __init__(self):
        self.pend = 0
        self.sr = 0                      # bit k = stage k+1

    def step(self, rst, en, soft_rst, time_ref, delay, spike_in) -> int:
        cur = int((self.pend or spike_in) and en)
        taps = (self.sr << 1) | cur
        out = int(time_ref and (taps >> delay) & 1)
        if rst or soft_rst:
            self.pend, self.sr = 0, 0
        elif time_ref:
            self.pend = 0
            self.sr = ((self.sr << 1) | cur) & ((1 << (self.DEPTH - 1)) - 1)
        else:
            self.pend = cur
        return out


class ConfigRegs:
    """Mirror of src/config_regs.v: the register map, with reset values from
    nm_params.vh. v_*/cnt_* are owned by NeuronSeq and passed in for reads."""

    def __init__(self):
        self.en = 0
        self.soft_rst = 0
        self.delay = P["NM_DELAY_RST"]
        self.tick_div = P["NM_TICK_DIV_RST"]
        self.thr = [P["NM_THR_RST"]] * 2
        self.leak = [P["NM_LEAK_RST"]] * 2
        self.dis = [0, 0]
        w = P["NM_W_RST"] & 0xF
        self.w = [(w << 4) | w] * 2           # W_A, W_B bytes

    # --- derived outputs (same packing as the RTL ports) ---
    def cfg(self, n):
        return (self.dis[n] << 19) | (self.leak[n] << 12) | self.thr[n]

    @property
    def w_pack(self):
        return (self.w[1] << 8) | self.w[0]

    def w_list(self):
        """[a1, a2, b1, b2] as signed ints, for NeuronSeq.step()."""
        def s4(x): return x - 16 if x & 8 else x
        return [s4(self.w[0] & 0xF), s4(self.w[0] >> 4), s4(self.w[1] & 0xF), s4(self.w[1] >> 4)]

    # --- bus ---
    def step(self, rst, wr_en, wr_addr, wr_data):
        """One clk: apply a write (if any). soft_rst is a 1-cycle pulse."""
        self.soft_rst = 0
        if rst:
            self.__init__()
            return
        if not wr_en:
            return
        a, d = wr_addr, wr_data
        if a == P["NM_REG_CTRL"]:
            self.en, self.soft_rst = d & 1, (d >> 1) & 1
        elif a == P["NM_REG_DELAY"]:
            self.delay = d & ((1 << P["NM_DELAY_W"]) - 1)
        elif a == P["NM_REG_TICK_DIV"]:
            self.tick_div = d
        elif a == P["NM_REG_W_A"]:
            self.w[0] = d
        elif a == P["NM_REG_W_B"]:
            self.w[1] = d
        else:
            for n, base in enumerate((P["NM_REG_NEUR_A"], P["NM_REG_NEUR_B"])):
                if a == base + 1:
                    self.thr[n] = (self.thr[n] & 0xFF0) | (d >> 4)
                elif a == base + 2:
                    self.thr[n] = (self.thr[n] & 0x00F) | (d << 4)
                elif a == base + 3:
                    self.dis[n], self.leak[n] = d >> 7, d & 0x7F

    def read(self, addr, v=(0, 0), cnt=(0, 0)):
        a = addr
        if a == P["NM_REG_ID"]:       return P["NM_ID"]
        if a == P["NM_REG_CTRL"]:     return self.en
        if a == P["NM_REG_DELAY"]:    return self.delay
        if a == P["NM_REG_TICK_DIV"]: return self.tick_div
        if a == P["NM_REG_W_A"]:      return self.w[0]
        if a == P["NM_REG_W_B"]:      return self.w[1]
        if a == P["NM_REG_CNT_A"]:    return cnt[0]
        if a == P["NM_REG_CNT_B"]:    return cnt[1]
        for n, base in enumerate((P["NM_REG_NEUR_A"], P["NM_REG_NEUR_B"])):
            if a == base:     return v[n] & 0xFF
            if a == base + 1: return ((self.thr[n] & 0xF) << 4) | (v[n] >> 8)
            if a == base + 2: return self.thr[n] >> 4
            if a == base + 3: return (self.dis[n] << 7) | self.leak[n]
        return 0
