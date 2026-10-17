// tick_gen: the single source of "biological time".
//
// Emits time_ref = 1 for one clk cycle every max(tick_div, NM_TICK_DIV_MIN) cycles.
// Every slow process in the chip (neuron leak, delay lines) advances on time_ref,
// never on clk directly, so changing TICK_DIV rescales the whole network's time.
// While en = 0 (or in reset) the counter is held at 0 and no pulses are produced.

`default_nettype none
`include "nm_params.vh"

module tick_gen (
    input  wire                       clk,
    input  wire                       rst,       // synchronous, active high
    input  wire                       en,        // CTRL.EN
    input  wire [`NM_TICK_DIV_W-1:0]  tick_div,  // from config_regs
    output reg                        time_ref   // 1-cycle pulse
);

    // Clamp: the neuron sequencer needs NM_SEQ_CYCLES per tick, so a period
    // below NM_TICK_DIV_MIN would make ticks overlap.
    wire [`NM_TICK_DIV_W-1:0] period =
        (tick_div < `NM_TICK_DIV_MIN) ? `NM_TICK_DIV_MIN : tick_div;

    reg [`NM_TICK_DIV_W-1:0] cnt;

    always @(posedge clk) begin
        if (rst || !en) begin
            cnt      <= 0;
            time_ref <= 1'b0;
        end else if (cnt == period - 1) begin
            cnt      <= 0;
            time_ref <= 1'b1;
        end else begin
            cnt      <= cnt + 1;
            time_ref <= 1'b0;
        end
    end

endmodule
