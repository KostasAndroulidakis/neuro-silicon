// neuro-silicon: global parameters (single source of truth).
// Every module that needs a width or a default value includes this file;
// test/model.py parses it so the Python golden model uses the same numbers.
//
// Widths follow tinyODIN's lif_neuron.v, which is used unmodified (see NOTICE).

`ifndef NM_PARAMS_VH
`define NM_PARAMS_VH

// --- Neuron word layout (tinyODIN neuron_core packing) --------------------
//   [31]    DISABLE   1 = neuron never spikes
//   [30:24] LEAK_STR  subtracted from v on every time_ref tick (7 bit)
//   [23:12] THR       firing threshold (12 bit)
//   [11:0]  V         membrane potential (12 bit, bit 11 = sign)
`define NM_NEUR_W     32
`define NM_V_W        12
`define NM_THR_W      12
`define NM_LEAK_W     7
`define NM_SYN_W      4     // synaptic weight, signed: -8..+7

// --- Our blocks ------------------------------------------------------------
`define NM_N_NEUR     2     // neurons A and B
`define NM_DELAY_W    4     // delay line length: 0..15 time_ref ticks
`define NM_TICK_DIV_W 8     // time_ref every TICK_DIV clk cycles
`define NM_SEQ_CYCLES 6     // clk cycles the sequencer needs per time_ref tick
                            // (2 neurons x {syn1, syn2, leak})
`define NM_TICK_DIV_MIN 8   // tick_gen clamps TICK_DIV below this; must be >= NM_SEQ_CYCLES

// --- Reset values ----------------------------------------------------------
`define NM_THR_RST       12'd10   // coincidence: 7 + 7 = 14 >= 10, a single 7 < 10
`define NM_LEAK_RST      7'd4     // -4 per tick: a lone spike (7) is gone in 2 ticks,
                                  // so only same/adjacent-tick arrivals can sum to >= 10
`define NM_W_RST         4'sd7    // all four synapses excitatory, max weight
`define NM_DELAY_RST     4'd2     // TBD after Python exploration
`define NM_TICK_DIV_RST  8'd8     // minimum legal value (= NM_SEQ_CYCLES rounded up)
`define NM_ID            8'hA5

`endif
