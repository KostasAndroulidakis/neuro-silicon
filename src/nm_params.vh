// neuro-silicon: global parameters (single source of truth).
// Every module that needs a width or a default value includes this file.
// Changing a value here changes it everywhere, including the Python model,
// which parses this file (see test/model.py).

`ifndef NM_PARAMS_VH
`define NM_PARAMS_VH

// --- Data widths ---------------------------------------------------------
`define NM_V_W        8     // membrane potential width (0..255)
`define NM_W_W        8     // synaptic weight width
`define NM_THR_W      8     // firing threshold width
`define NM_LEAK_W     3     // leak shift amount width (leak = v >> shift)
`define NM_DELAY_W    4     // delay line length width (0..15 ticks)
`define NM_TICK_DIV_W 8     // time_ref prescaler divider width

// --- Reset values (what the chip does before any SPI configuration) -------
`define NM_THR_RST      8'd100   // threshold:  validated in simulation
`define NM_LEAK_RST     3'd3     // leak = v/8: validated in simulation
`define NM_W_RST        8'd60    // 60 + 60 >= 100: only coincidence fires
`define NM_DELAY_RST    4'd2     // TBD after Python exploration
`define NM_TICK_DIV_RST 8'd1     // time_ref every clk cycle (no prescale)

`endif
