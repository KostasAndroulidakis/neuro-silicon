// config_regs: the runtime configuration of the chip, as seen over SPI.
//
// Single source of truth for every tunable: CTRL, DELAY, TICK_DIV, the parameter
// fields of both neuron words, and the four synaptic weights. Membrane potentials
// and spike counters are owned by neuron_seq and only *read* here.
// Reset values are the NM_*_RST constants, so the chip is a working coincidence
// detector before any SPI traffic, but stays frozen until CTRL.EN is set.

`default_nettype none
`include "nm_params.vh"

module config_regs (
    input  wire        clk,
    input  wire        rst,
    // register bus (from spi_slave)
    input  wire        wr_en,
    input  wire [6:0]  wr_addr,
    input  wire [7:0]  wr_data,
    input  wire [6:0]  rd_addr,
    output reg  [7:0]  rd_data,
    // live values owned elsewhere (read-only here)
    input  wire [`NM_V_W-1:0] v_a,
    input  wire [`NM_V_W-1:0] v_b,
    input  wire [7:0]  cnt_a,
    input  wire [7:0]  cnt_b,
    // configuration outputs
    output reg         en,
    output reg         soft_rst,       // 1-clk pulse
    output reg  [`NM_DELAY_W-1:0]    delay,
    output reg  [`NM_TICK_DIV_W-1:0] tick_div,
    output wire [19:0] cfg_a,          // {disable, leak_str[6:0], thr[11:0]}
    output wire [19:0] cfg_b,
    output wire [15:0] w_pack          // {w_b2, w_b1, w_a2, w_a1}
);

    reg [`NM_THR_W-1:0]  thr_a,  thr_b;
    reg [`NM_LEAK_W-1:0] leak_a, leak_b;
    reg                  dis_a,  dis_b;
    reg [7:0]            w_a,    w_b;

    assign cfg_a  = {dis_a, leak_a, thr_a};
    assign cfg_b  = {dis_b, leak_b, thr_b};
    assign w_pack = {w_b, w_a};

    // --- Writes ----------------------------------------------------------------
    always @(posedge clk) begin
        soft_rst <= 1'b0;                              // self-clearing
        if (rst) begin
            en       <= 1'b0;
            delay    <= `NM_DELAY_RST;
            tick_div <= `NM_TICK_DIV_RST;
            thr_a    <= `NM_THR_RST;   thr_b  <= `NM_THR_RST;
            leak_a   <= `NM_LEAK_RST;  leak_b <= `NM_LEAK_RST;
            dis_a    <= 1'b0;          dis_b  <= 1'b0;
            w_a      <= {`NM_W_RST, `NM_W_RST};
            w_b      <= {`NM_W_RST, `NM_W_RST};
        end else if (wr_en) begin
            case (wr_addr)
                `NM_REG_CTRL:         begin en <= wr_data[0]; soft_rst <= wr_data[1]; end
                `NM_REG_DELAY:        delay    <= wr_data[`NM_DELAY_W-1:0];
                `NM_REG_TICK_DIV:     tick_div <= wr_data;
                `NM_REG_NEUR_A + 1:   thr_a[3:0]  <= wr_data[7:4];   // byte 1: {thr[3:0], v[11:8]}
                `NM_REG_NEUR_A + 2:   thr_a[11:4] <= wr_data;        // byte 2: thr[11:4]
                `NM_REG_NEUR_A + 3:   {dis_a, leak_a} <= wr_data;    // byte 3: {disable, leak}
                `NM_REG_NEUR_B + 1:   thr_b[3:0]  <= wr_data[7:4];
                `NM_REG_NEUR_B + 2:   thr_b[11:4] <= wr_data;
                `NM_REG_NEUR_B + 3:   {dis_b, leak_b} <= wr_data;
                `NM_REG_W_A:          w_a <= wr_data;
                `NM_REG_W_B:          w_b <= wr_data;
                default: ;                                           // ID, V, counters: read-only
            endcase
        end
    end

    // --- Reads (combinational) ---------------------------------------------------
    always @(*) begin
        case (rd_addr)
            `NM_REG_ID:           rd_data = `NM_ID;
            `NM_REG_CTRL:         rd_data = {7'd0, en};
            `NM_REG_DELAY:        rd_data = {{(8-`NM_DELAY_W){1'b0}}, delay};
            `NM_REG_TICK_DIV:     rd_data = tick_div;
            `NM_REG_NEUR_A:       rd_data = v_a[7:0];
            `NM_REG_NEUR_A + 1:   rd_data = {thr_a[3:0], v_a[11:8]};
            `NM_REG_NEUR_A + 2:   rd_data = thr_a[11:4];
            `NM_REG_NEUR_A + 3:   rd_data = {dis_a, leak_a};
            `NM_REG_NEUR_B:       rd_data = v_b[7:0];
            `NM_REG_NEUR_B + 1:   rd_data = {thr_b[3:0], v_b[11:8]};
            `NM_REG_NEUR_B + 2:   rd_data = thr_b[11:4];
            `NM_REG_NEUR_B + 3:   rd_data = {dis_b, leak_b};
            `NM_REG_W_A:          rd_data = w_a;
            `NM_REG_W_B:          rd_data = w_b;
            `NM_REG_CNT_A:        rd_data = cnt_a;
            `NM_REG_CNT_B:        rd_data = cnt_b;
            default:              rd_data = 8'h00;
        endcase
    end

endmodule
