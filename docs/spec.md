# neuro-silicon: Specification

Status: **draft**. Decisions marked TBD are open; everything else is settled.

## 1. Purpose

A tiny neuromorphic chip that detects the **direction of motion** between two
sensors using two leaky integrate-and-fire (LIF) neurons and spike timing.
An object passing left -> right makes `dir_lr` spike; right -> left makes `dir_rl` spike.

Target: Tiny Tapeout, Sky130, 1x1 tile, shuttle TTSKY26d (deadline 2026-11-30).

## 2. Pins

Fixed by Tiny Tapeout: 8 in, 8 out, 8 bidir, `clk`, `rst_n`. Our mapping lives in
`info.yaml` (single source of truth); summary:

| Pin      | Dir | Signal     | Description                              |
|----------|-----|------------|------------------------------------------|
| ui[0]    | in  | sensor_l   | Left sensor, level (1 = beam blocked)    |
| ui[1]    | in  | sensor_r   | Right sensor, level                      |
| ui[2..4] | in  | spi_*      | SPI slave: SCK, MOSI, CS_n               |
| uo[0]    | out | dir_lr     | 1-tick spike: motion left -> right       |
| uo[1]    | out | dir_rl     | 1-tick spike: motion right -> left       |
| uo[2]    | out | spi_miso   | SPI readback                             |
| uo[3..4] | out | spike_a/b  | Raw neuron spikes (debug)                |
| uo[5]    | out | time_ref   | Slow tick (debug)                        |

## 3. Architecture

```
                         +-----------+
 SPI (from RP2040/MCU) ->| spi_slave |-> config registers (threshold, leak,
                         +-----------+   weights, delay, tick divider)
                                              |
            +----------+                      v
 clk ------>| tick_gen |---- time_ref ---> everything below
            +----------+

 sensor_l -> [edge_det] -> spike_l ---+--> [delay N] --+
                                      |                +--> [lif A] --> dir_lr
 sensor_r -> [edge_det] -> spike_r -----------+--------+
                                      |       |
                                      |       +--> [delay N] --+
                                      +-----------------------+--> [lif B] --> dir_rl
```

Principle: a neuron fires only when two spikes arrive (almost) together.
The delay makes that happen for exactly one direction of motion.

## 4. Blocks (one responsibility each)

Reuse policy: C. Frenkel's tinyODIN is the reference. Files are copied unmodified
where they fit; the rest follows its structure at 2-neuron scale (see NOTICE).

| Block             | File                      | Origin     | Responsibility                                      |
|-------------------|---------------------------|------------|-----------------------------------------------------|
| `tt_um_neuro_silicon` | src/tt_um_neuro_silicon.v | ours   | Pin mapping + reset sync. No logic.                 |
| `motion_detector` | src/motion_detector.v     | ours       | Top level: wiring only. No logic.                   |
| `spi_slave`       | src/spi_slave.v           | ours       | Synchronous SPI slave (single clock domain) -> register strobes. tinyODIN's uses SCK as a 2nd clock, unsuitable for TT. |
| `config_regs`     | src/config_regs.v         | ours       | Neuron words, weights, CTRL/DELAY/TICK_DIV, read-only counters (SSOT at runtime) |
| `tick_gen`        | src/tick_gen.v            | ours       | The ONE source of biological time (`time_ref`)      |
| `edge_detect`     | src/edge_detect.v         | ours       | Sensor level -> single 1-clk spike                  |
| `delay_line`      | src/delay_line.v          | ours       | Delays a spike by N `time_ref` ticks                |
| `neuron_seq`      | src/neuron_seq.v          | ours, tinyODIN pattern | Sequencer: per tick, for each neuron apply syn1, syn2, leak through `lif_neuron`; writes state back; counts spikes |
| `lif_neuron`      | src/lif_neuron.v          | **tinyODIN, unmodified** | Pure combinational 12-bit LIF update: state -> next state + spike |

All widths and reset values: `src/nm_params.vh` (SSOT).

## 5. LIF neuron model (tinyODIN `lif_neuron.v`)

The neuron is combinational: it receives one *event* at a time and returns the next
state. Events are serialised by `neuron_seq`, so two spikes arriving in the same tick
are applied one after the other.

```
synaptic event (syn_event=1, time_ref=0):  v_next = sat12( v + sign_extend(w) )
leak event     (syn_event=1, time_ref=1):  v_next = v - leak_str, clamped at 0
                                           (negative v leaks towards 0 from below)
spike          = (v_next >= thr) and v_next >= 0
on spike       : v_next = 0
```

- `v`: 12-bit signed (bit 11 = sign), saturating, never wraps.
- `w`: 4-bit signed, so inhibitory synapses are possible.
- Per-neuron parameters `thr`, `leak_str`, `disable` live inside the neuron's 32-bit
  word (layout in `nm_params.vh`), exactly like tinyODIN's neuron memory.

Validated behaviour carried over from our earlier 8-bit neuron: one strong input fires,
one weak does not, weak inputs sum only if they arrive close together.

## 6. Register map

This table is the single source of truth for runtime configuration. `config_regs.v`
and `test/model.py` are written from it, never the other way round.
All registers are 8 bits wide (SPI moves bytes). Multi-byte values are little-endian.
Reset values equal the `NM_*_RST` constants in `src/nm_params.vh`, so the chip is a
valid coincidence detector before any SPI traffic, but stays silent until `EN` is set.

| Addr      | Name            | R/W | Reset  | Meaning                                                |
|-----------|-----------------|-----|--------|--------------------------------------------------------|
| 0x00      | `ID`            | R   | 0xA5   | Constant. Reading 0xA5 proves the SPI link works.      |
| 0x01      | `CTRL`          | RW  | 0x00   | [0] EN: 1 = neurons run, 0 = frozen (safe to configure; tinyODIN's SPI_GATE_ACTIVITY). [1] SOFT_RST: write 1 to clear v, delay lines, counters; self-clearing. |
| 0x02      | `DELAY`         | RW  | 2      | [3:0] delay line length in time_ref ticks              |
| 0x03      | `TICK_DIV`      | RW  | 8      | time_ref every TICK_DIV clk cycles; values < 8 are treated as 8 |
| 0x10-0x13 | `NEUR_A`        | RW  | see vh | Neuron A 32-bit word, byte 0 = bits [7:0]. Layout: [31] DISABLE, [30:24] LEAK_STR, [23:12] THR, [11:0] V. Writing V while EN=1 is allowed but racy; use EN=0. |
| 0x14-0x17 | `NEUR_B`        | RW  | see vh | Neuron B word, same layout                             |
| 0x20      | `W_A`           | RW  | 0x77   | [3:0] W_A1 (delay(spike_l) -> A), [7:4] W_A2 (spike_r -> A), both 4-bit signed |
| 0x21      | `W_B`           | RW  | 0x77   | [3:0] W_B1 (delay(spike_r) -> B), [7:4] W_B2 (spike_l -> B) |
| 0x30      | `SPIKE_CNT_A`   | R   | -      | Spikes of neuron A since SOFT_RST (wraps at 256)       |
| 0x31      | `SPIKE_CNT_B`   | R   | -      | Spikes of neuron B since SOFT_RST (wraps at 256)       |

Reading `NEUR_x` bytes 0-1 gives the live membrane potential (tinyODIN readback).
Unmapped addresses read as 0x00; writes to them are ignored.

### SPI protocol

Mode 0 (CPOL=0, CPHA=0), MSB first, CS_n active low, one 16-bit transaction per CS_n pulse.
SCK, MOSI and CS_n are sampled by the core clock (synchronous slave), so SCK must be
at most clk/4.

```
byte 0 (MOSI): [7] = 1 read / 0 write     [6:0] = address
byte 1:        write -> data on MOSI       read -> data on MISO
```

Writes take effect at the end of the transaction (CS_n rising edge), so a register
never changes mid-byte.

## 7. Open questions

- DELAY: depends on sensor spacing and object speed -> explore in Python model.
- Coincidence window: how far apart can two spikes be and still fire? -> Python.
- clock_hz: one time_ref tick = TICK_DIV clk cycles (>= 8). At 10 kHz clk and TICK_DIV=8, 1 tick = 0.8 ms. Decide with DELAY.

## 8. Status

| Block             | Model | RTL  | Test  |
|-------------------|-------|------|-------|
| wrapper           | -     | done | smoke |
| lif_neuron        | -     | done (tinyODIN) | - |
| tick_gen          |       |      |       |
| neuron_seq        |       |      |       |
| edge_detect       |       |      |       |
| delay_line        |       |      |       |
| config_regs       |       |      |       |
| spi_slave         |       |      |       |
| motion_detector   |       |      |       |
