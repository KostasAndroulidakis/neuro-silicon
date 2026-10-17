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
