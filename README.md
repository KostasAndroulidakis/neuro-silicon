![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg)

# neuro-silicon

A tiny digital spiking neural network chip: two LIF neurons that detect the
direction of motion between two sensors. Built for Tiny Tapeout (Sky130).

- Specification and design decisions: [docs/spec.md](docs/spec.md)
- Tiny Tapeout datasheet page: [docs/info.md](docs/info.md)
- Pinout, tile count and source list: [info.yaml](info.yaml)

## Layout

```
info.yaml          Tiny Tapeout metadata: top module, tiles, pinout, source list (SSOT)
src/               RTL, one module per file; nm_params.vh holds all widths/defaults (SSOT)
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

Waveforms land in `test/tb.fst` (open with GTKWave or Surfer).

## Credits

Architecture principles follow C. Frenkel's open-source
[tinyODIN](https://github.com/ChFrenkel/tinyODIN) (Solderpad 2.1).
