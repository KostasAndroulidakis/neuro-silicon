/*
 * neuro-silicon: Tiny Tapeout wrapper.
 *
 * Responsibilities of this file (and nothing else):
 *   1. map Tiny Tapeout's fixed pins to named internal signals (see info.yaml)
 *   2. synchronise the external active-low reset into an internal active-high one
 *   3. instantiate the chip blocks (motion_detector once it exists)
 *
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
`include "nm_params.vh"

module tt_um_neuro_silicon (
    input  wire [7:0] ui_in,    // dedicated inputs
    output wire [7:0] uo_out,   // dedicated outputs
    input  wire [7:0] uio_in,   // bidirectional: input path
    output wire [7:0] uio_out,  // bidirectional: output path
    output wire [7:0] uio_oe,   // bidirectional: enable (1 = output)
    input  wire       ena,      // always 1 when powered; ignored
    input  wire       clk,
    input  wire       rst_n     // active-low reset
);

    // --- 1. Pin mapping (names match info.yaml) ---------------------------
    wire sensor_l  = ui_in[0];
    wire sensor_r  = ui_in[1];
    wire spi_sck   = ui_in[2];
    wire spi_mosi  = ui_in[3];
    wire spi_cs_n  = ui_in[4];

    wire dir_lr, dir_rl, spi_miso, spike_a, spike_b, time_ref;

    assign uo_out  = {2'b00, time_ref, spike_b, spike_a, spi_miso, dir_rl, dir_lr};
    assign uio_out = 8'b0;      // bidirectional pins unused...
    assign uio_oe  = 8'b0;      // ...configured as inputs

    // --- 2. Reset synchroniser (2 flip-flops, active-high internally) -----
    reg rst_meta, rst;
    always @(posedge clk) begin
        rst_meta <= ~rst_n;
        rst      <= rst_meta;
    end

    // --- 3. Chip blocks ----------------------------------------------------
    // Blocks are added here as they are built and tested. Until config_regs
    // exists, runtime settings are the reset constants from nm_params.vh.
    tick_gen u_tick_gen (
        .clk      (clk),
        .rst      (rst),
        .en       (1'b1),
        .tick_div (`NM_TICK_DIV_RST),
        .time_ref (time_ref)
    );

    // Until config_regs exists, every runtime setting is its reset constant.
    wire        en       = 1'b1;
    wire        soft_rst = 1'b0;
    wire [19:0] cfg      = {1'b0, `NM_LEAK_RST, `NM_THR_RST};

    // Sensors -> spikes
    wire spike_l, spike_r;
    edge_detect u_edge_l (.clk(clk), .rst(rst), .level(sensor_l), .pulse(spike_l));
    edge_detect u_edge_r (.clk(clk), .rst(rst), .level(sensor_r), .pulse(spike_r));

    // Delayed copies: A listens for "L then R", B for "R then L"
    wire spike_l_d, spike_r_d;
    delay_line u_delay_l (
        .clk(clk), .rst(rst), .en(en), .soft_rst(soft_rst), .time_ref(time_ref),
        .delay(`NM_DELAY_RST), .in(spike_l), .out(spike_l_d));
    delay_line u_delay_r (
        .clk(clk), .rst(rst), .en(en), .soft_rst(soft_rst), .time_ref(time_ref),
        .delay(`NM_DELAY_RST), .in(spike_r), .out(spike_r_d));

    // Neuron core: in_syn = {b2, b1, a2, a1}
    wire [`NM_V_W-1:0] v_a, v_b;
    wire [7:0] cnt_a, cnt_b;
    neuron_seq u_neuron_seq (
        .clk      (clk),
        .rst      (rst),
        .en       (en),
        .soft_rst (soft_rst),
        .time_ref (time_ref),
        .in_syn   ({spike_l, spike_r_d, spike_r, spike_l_d}),
        .w_pack   ({4{`NM_W_RST}}),
        .cfg_a    (cfg),
        .cfg_b    (cfg),
        .spike_a  (spike_a),
        .spike_b  (spike_b),
        .v_a      (v_a),
        .v_b      (v_b),
        .cnt_a    (cnt_a),
        .cnt_b    (cnt_b)
    );

    // Direction outputs are the neuron spikes (spike_a/b pins duplicate them for debug).
    assign dir_lr   = spike_a;
    assign dir_rl   = spike_b;
    assign spi_miso = 1'b0;             // spi_slave not built yet

    // Keep the linter quiet about signals not consumed yet.
    wire _unused = &{ena, spi_sck, spi_mosi, spi_cs_n, ui_in[7:5], uio_in,
                     v_a, v_b, cnt_a, cnt_b, 1'b0};

endmodule
