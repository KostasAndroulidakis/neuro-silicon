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

| Block             | File                    | Responsibility                                   |
|-------------------|-------------------------|--------------------------------------------------|
| `tt_um_neuro_silicon` | src/tt_um_neuro_silicon.v | Pin mapping + reset sync. No logic.          |
| `motion_detector` | src/motion_detector.v   | Top level: wiring only. No logic.                |
| `spi_slave`       | src/spi_slave.v         | SPI -> register write/read strobes                |
| `config_regs`     | src/config_regs.v       | The register bank (SSOT of runtime settings)     |
| `tick_gen`        | src/tick_gen.v          | The ONE source of biological time (`time_ref`)   |
| `edge_detect`     | src/edge_detect.v       | Sensor level -> single 1-clk spike               |
| `delay_line`      | src/delay_line.v        | Delays a spike by N `time_ref` ticks             |
| `lif_update`      | src/lif_update.v        | Pure combinational: state -> next state + spike  |
| `lif_neuron`      | src/lif_neuron.v        | State register + `lif_update`                    |

All widths and reset values: `src/nm_params.vh` (SSOT).

## 5. LIF neuron model

Per `time_ref` tick (not per clk):

```
v_next = sat( v - (v >> leak_shift) + w1*in1 + w2*in2 )   # saturating, never wraps
spike  = (v_next >= threshold)
v      = spike ? 0 : v_next
```

Validated in simulation (threshold 100, leak v/8): one spike of weight 110 fires;
weight 30 does not; four weight-30 spikes fire only if they arrive within a few ticks.

## 6. Register map

TBD (next step). Planned registers: THRESHOLD, LEAK_SHIFT, W_A1, W_A2, W_B1, W_B2,
DELAY, TICK_DIV, plus read-only V_A, V_B for debug. Addresses and bit layout to
be defined here first, then mirrored in Verilog and Python from this table.

## 7. Open questions

- DELAY: depends on sensor spacing and object speed -> explore in Python model.
- Coincidence window: how far apart can two spikes be and still fire? -> Python.
- clock_hz: with time_ref = clk, 10 kHz gives 0.1 ms ticks. Decide with DELAY.
- SPI protocol: frame format (address byte + data byte?) -> define with register map.

## 8. Status

| Block             | Model | RTL | Test |
|-------------------|-------|-----|------|
| wrapper           | -     | done | smoke |
| spi_slave         |       |     |      |
| config_regs       |       |     |      |
| tick_gen          |       |     |      |
| edge_detect       |       |     |      |
| delay_line        |       |     |      |
| lif_update        |       |     |      |
| lif_neuron        | (old) | (old) | (old) |
| motion_detector   |       |     |      |
