![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg)

# neuro-silicon

A tiny digital spiking neural network chip: two LIF neurons that detect the
direction of motion between two sensors, configurable over SPI. Built on the
Tiny Tapeout (Sky130) flow; the neuromorphic unit of a larger navigation SoC
([docs/soc-architecture.md](docs/soc-architecture.md)).

Status: RTL complete, every block verified against a bit-exact Python model with
cocotb, chip-level tests drive it through its pins (also at gate level in CI),
GDS builds clean at ~40 % of a 1x2 tile.

- Specification and design decisions: [docs/spec.md](docs/spec.md)
- Tiny Tapeout datasheet page: [docs/info.md](docs/info.md)
- Pinout, tile count and source list: [info.yaml](info.yaml)

## Layout

```
info.yaml          Tiny Tapeout metadata: top module, tiles, pinout, source list (SSOT)
src/               RTL, one module per file; nm_params.vh holds all widths/defaults (SSOT)
                   tt_um_neuro_silicon.v (TT wrapper) > motion_detector.v (top) > blocks
pyproject.toml     Python dependencies for tests + model (SSOT, locked in uv.lock)
test/              cocotb tests (one file per block) + Python golden model
docs/              spec, block diagram, datasheet page
.github/workflows  CI: tests, GDS build, docs
```

## Run the tests

```
uv sync
cd test
uv run make
```

`make blocks` runs every block against its Python model; `make` runs the chip-level
tests through the Tiny Tapeout pins. Waveforms land in `test/tb.fst` (GTKWave or Surfer).

## Credits

Architecture principles follow C. Frenkel's open-source
[tinyODIN](https://github.com/ChFrenkel/tinyODIN) (Solderpad 2.1).
