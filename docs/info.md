<!--- This file becomes the project's page in the Tiny Tapeout datasheet. -->

## How it works

neuro-silicon is a tiny digital spiking neural network: two leaky integrate-and-fire
(LIF) neurons that detect the **direction of motion** of an object passing between two
sensors.

Each sensor edge becomes a spike. Neuron A receives the left spike through a delay line
and the right spike directly; neuron B the mirror image. A neuron only fires when its two
inputs arrive (almost) together, so A fires for left-to-right motion and B for
right-to-left. The delay, the neurons' threshold and leak, and the four synaptic weights
are all set over SPI, so the same silicon can be tuned to sensor spacing and object speed.

Architecture: a single time-multiplexed LIF neuron (C. Frenkel's tinyODIN `lif_neuron.v`,
unmodified) serves both neurons in 6 clock cycles per "biological tick"; the tick rate is
a programmable divider of the clock. 12-bit membrane potentials with saturation, 4-bit
signed weights (inhibitory synapses possible). About 40 % of a 1x2 tile.

## How to test

1. Apply a clock (10 kHz is a good default: one tick = TICK_DIV / 10 kHz) and reset.
2. Over SPI (mode 0, MSB first, SCK <= clk/8, 16-bit frames: `[R/W][addr:7]` then data):
   read address `0x00`, expect `0xA5`.
3. Write `0x01` (CTRL) = `0x01` to enable. The chip is silent until then.
4. Drive `ui[0]` (left sensor) high for a few clocks, then `ui[1]` (right sensor)
   `DELAY` ticks later: `uo[0]` (dir_lr) pulses for one clock. Reverse the order:
   `uo[1]` (dir_rl) pulses.
5. Read `0x30` / `0x31`: spike counters. Read `0x10` / `0x14`: live membrane potentials.

Register map (all 8-bit; reset values in brackets):

| Addr | Name | R/W | Meaning |
|------|------|-----|---------|
| 0x00 | ID | R | 0xA5 |
| 0x01 | CTRL | RW | [0] EN [0], [1] SOFT_RST (write 1: clears potentials, delay queues, counters) |
| 0x02 | DELAY | RW | delay line length in ticks, 0..15 [2] |
| 0x03 | TICK_DIV | RW | clocks per tick, min 8 [8] |
| 0x10..0x13 | NEUR_A | RW | neuron A word, little-endian: [11:0] V (read-only), [23:12] THR [10], [30:24] LEAK [4], [31] DISABLE [0] |
| 0x14..0x17 | NEUR_B | RW | neuron B word, same layout |
| 0x20 | W_A | RW | [3:0] weight delay(L)->A, [7:4] weight R->A, 4-bit signed [0x77] |
| 0x21 | W_B | RW | [3:0] weight delay(R)->B, [7:4] weight L->B [0x77] |
| 0x30 | CNT_A | R | spikes of A since SOFT_RST |
| 0x31 | CNT_B | R | spikes of B since SOFT_RST |

Defaults give a coincidence detector: one spike (7) stays below threshold (10), two in
the same tick (14) fire, and a lone spike leaks away in two ticks.

## External hardware

Two digital sensors on `ui[0]`/`ui[1]` (IR break-beam, or push buttons for a manual
demo), optional LEDs on `uo[0]`/`uo[1]`. SPI from the demo board's RP2040 on
`ui[2]` SCK, `ui[3]` MOSI, `ui[4]` CS_n, `uo[2]` MISO.
