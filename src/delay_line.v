// delay_line: delays a spike by `delay` time_ref ticks (0..2^NM_DELAY_W-1).
//
// Spikes are 1-clk pulses that may arrive at any time; they are collected in
// `pend` until the next time_ref, then enter a shift register that advances one
// stage per tick. `out` is a 1-clk pulse *in the time_ref cycle* in which the
// spike leaves, so a spike with delay 0 reaches the neuron in the same tick as
// an undelayed spike that arrived at the same moment (same timing as a direct
// path into neuron_seq).

`default_nettype none
`include "nm_params.vh"

module delay_line (
    input  wire                     clk,
    input  wire                     rst,
    input  wire                     en,        // CTRL.EN: 0 = inputs ignored
    input  wire                     soft_rst,  // clears the queue
    input  wire                     time_ref,
    input  wire [`NM_DELAY_W-1:0]   delay,     // from config_regs
    input  wire                     in,        // spike in (1-clk pulse)
    output wire                     out        // spike out (1-clk pulse)
);

    localparam DEPTH = (1 << `NM_DELAY_W);     // 16 stages for 4-bit delay

    reg              pend;
    reg [DEPTH-2:0]  sr;                       // stages 1..15; stage 0 is `cur`

    wire cur = (pend | in) & en;               // everything that arrived before this tick
    wire [DEPTH-1:0] taps = {sr, cur};

    assign out = time_ref & taps[delay];

    always @(posedge clk) begin
        if (rst || soft_rst) begin
            pend <= 1'b0;
            sr   <= {(DEPTH-1){1'b0}};
        end else if (time_ref) begin
            pend <= 1'b0;                      // absorbed into the shift register
            sr   <= {sr[DEPTH-3:0], cur};
        end else begin
            pend <= cur;
        end
    end

endmodule
