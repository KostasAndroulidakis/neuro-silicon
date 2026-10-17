// neuron_seq: time-multiplexed neuron core for NM_N_NEUR = 2 neurons.
//
// One tinyODIN lif_neuron (pure combinational) is shared by both neurons, exactly
// as tinyODIN shares one across 256. On every time_ref pulse the sequencer runs
// NM_SEQ_CYCLES = 6 slots, one clk each:
//
//   slot 0: neuron A, synapse 1 (if a spike is pending)
//   slot 1: neuron A, synapse 2 (if pending)
//   slot 2: neuron A, leak
//   slot 3..5: the same for neuron B
//
// Incoming spikes (1-clk pulses on in_syn) are latched into `pending` at any time
// and consumed in their slot. A spike arriving in the very cycle its slot consumes
// it stays pending for the next tick, so nothing is ever lost.
//
// Ownership (single source of truth):
//   - membrane potentials v_a, v_b live HERE (neuron word bits [11:0])
//   - per-neuron parameters cfg_* come from config_regs (neuron word bits [31:12])
//   - weights come from config_regs (W_A, W_B registers)

`default_nettype none
`include "nm_params.vh"

module neuron_seq (
    input  wire        clk,
    input  wire        rst,       // synchronous, active high
    input  wire        en,        // CTRL.EN: 0 = frozen, spikes ignored
    input  wire        soft_rst,  // CTRL.SOFT_RST: clear state, keep config
    input  wire        time_ref,  // from tick_gen

    input  wire [3:0]  in_syn,    // {b2, b1, a2, a1} spike pulses
    input  wire [15:0] w_pack,    // {w_b2, w_b1, w_a2, w_a1}, 4-bit signed each
    input  wire [19:0] cfg_a,     // {disable, leak_str[6:0], thr[11:0]}
    input  wire [19:0] cfg_b,

    output reg         spike_a,   // 1-clk pulse per emitted spike
    output reg         spike_b,
    output reg  [`NM_V_W-1:0] v_a,
    output reg  [`NM_V_W-1:0] v_b,
    output reg  [7:0]  cnt_a,     // spikes since reset / soft_rst, wraps
    output reg  [7:0]  cnt_b
);

    // --- Sequencer state -------------------------------------------------------
    reg        active;
    reg  [2:0] slot;
    reg  [3:0] pending;

    // --- Slot decode -----------------------------------------------------------
    reg        sel_b;      // 0 = neuron A, 1 = neuron B
    reg        is_leak;
    reg  [1:0] syn_idx;    // index into in_syn / w_pack (valid when !is_leak)
    always @(*) begin
        case (slot)
            3'd0: begin sel_b = 1'b0; is_leak = 1'b0; syn_idx = 2'd0; end
            3'd1: begin sel_b = 1'b0; is_leak = 1'b0; syn_idx = 2'd1; end
            3'd2: begin sel_b = 1'b0; is_leak = 1'b1; syn_idx = 2'd0; end
            3'd3: begin sel_b = 1'b1; is_leak = 1'b0; syn_idx = 2'd2; end
            3'd4: begin sel_b = 1'b1; is_leak = 1'b0; syn_idx = 2'd3; end
            default: begin sel_b = 1'b1; is_leak = 1'b1; syn_idx = 2'd0; end
        endcase
    end

    wire [19:0]        sel_cfg   = sel_b ? cfg_b : cfg_a;
    wire [`NM_V_W-1:0] sel_state = sel_b ? v_b   : v_a;
    wire [3:0]         sel_w     = w_pack[syn_idx*4 +: 4];
    wire               consume   = active & ~is_leak & pending[syn_idx];
    wire               syn_event = active & (is_leak | pending[syn_idx]);

    // --- The shared neuron (tinyODIN, unmodified) ------------------------------
    wire [`NM_V_W-1:0] state_next;
    wire               spike_out;
    lif_neuron u_lif (
        .param_leak_str  (sel_cfg[18:12]),
        .param_thr       (sel_cfg[11:0]),
        .state_core      (sel_state),
        .state_core_next (state_next),
        .syn_weight      (sel_w),
        .syn_event       (syn_event),
        .time_ref        (is_leak),
        .spike_out       (spike_out)
    );

    // A disabled neuron still updates its state but never emits (tinyODIN rule).
    wire fire = syn_event & spike_out & ~sel_cfg[19];

    // --- Registers ---------------------------------------------------------------
    wire [3:0] consume_mask = consume ? (4'b0001 << syn_idx) : 4'b0000;

    always @(posedge clk) begin
        if (rst || soft_rst) begin
            active  <= 1'b0;
            slot    <= 3'd0;
            pending <= 4'b0000;
            v_a     <= 0;
            v_b     <= 0;
            spike_a <= 1'b0;
            spike_b <= 1'b0;
            cnt_a   <= 8'd0;
            cnt_b   <= 8'd0;
        end else begin
            // spike capture: consume first, then OR in new arrivals (never lose one)
            pending <= (pending & ~consume_mask) | (en ? in_syn : 4'b0000);

            // sequencer
            if (!active) begin
                if (time_ref && en) begin
                    active <= 1'b1;
                    slot   <= 3'd0;
                end
            end else begin
                if (sel_b) v_b <= state_next; else v_a <= state_next;
                if (slot == `NM_SEQ_CYCLES - 1) active <= 1'b0;
                else                             slot   <= slot + 3'd1;
            end

            // outputs: 1-clk pulses
            spike_a <= active & ~sel_b & fire;
            spike_b <= active &  sel_b & fire;
            if (active & ~sel_b & fire) cnt_a <= cnt_a + 8'd1;
            if (active &  sel_b & fire) cnt_b <= cnt_b + 8'd1;
        end
    end

endmodule
