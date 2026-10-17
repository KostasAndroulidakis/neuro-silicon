// motion_detector: chip top level. Wiring only, no logic.
//
//  sensor_l -> edge_detect -> spike_l --+-> delay_line --> A.syn1
//                                       +----------------> B.syn2
//  sensor_r -> edge_detect -> spike_r --+-> delay_line --> B.syn1
//                                       +----------------> A.syn2
//
//  Neuron A fires on "L then R" (dir_lr), neuron B on "R then L" (dir_rl).
//  All settings come from config_regs, programmed over SPI.

`default_nettype none
`include "nm_params.vh"

module motion_detector (
    input  wire clk,
    input  wire rst,          // synchronous, active high
    // sensors
    input  wire sensor_l,
    input  wire sensor_r,
    // SPI
    input  wire spi_sck,
    input  wire spi_mosi,
    input  wire spi_cs_n,
    output wire spi_miso,
    // results
    output wire dir_lr,
    output wire dir_rl,
    // debug
    output wire time_ref
);

    // SPI -> register bus -> configuration
    wire        wr_en;
    wire [6:0]  wr_addr, rd_addr;
    wire [7:0]  wr_data, rd_data;
    spi_slave u_spi (
        .clk(clk), .rst(rst),
        .sck(spi_sck), .mosi(spi_mosi), .cs_n(spi_cs_n), .miso(spi_miso),
        .wr_en(wr_en), .wr_addr(wr_addr), .wr_data(wr_data),
        .rd_addr(rd_addr), .rd_data(rd_data));

    wire        en, soft_rst;
    wire [`NM_DELAY_W-1:0]    delay;
    wire [`NM_TICK_DIV_W-1:0] tick_div;
    wire [19:0] cfg_a, cfg_b;
    wire [15:0] w_pack;
    wire [`NM_V_W-1:0] v_a, v_b;
    wire [7:0]  cnt_a, cnt_b;
    config_regs u_regs (
        .clk(clk), .rst(rst),
        .wr_en(wr_en), .wr_addr(wr_addr), .wr_data(wr_data),
        .rd_addr(rd_addr), .rd_data(rd_data),
        .v_a(v_a), .v_b(v_b), .cnt_a(cnt_a), .cnt_b(cnt_b),
        .en(en), .soft_rst(soft_rst), .delay(delay), .tick_div(tick_div),
        .cfg_a(cfg_a), .cfg_b(cfg_b), .w_pack(w_pack));

    // Biological time
    tick_gen u_tick_gen (
        .clk(clk), .rst(rst), .en(en), .tick_div(tick_div), .time_ref(time_ref));

    // Sensors -> spikes
    wire spike_l, spike_r;
    edge_detect u_edge_l (.clk(clk), .rst(rst), .level(sensor_l), .pulse(spike_l));
    edge_detect u_edge_r (.clk(clk), .rst(rst), .level(sensor_r), .pulse(spike_r));

    // Delayed copies
    wire spike_l_d, spike_r_d;
    delay_line u_delay_l (
        .clk(clk), .rst(rst), .en(en), .soft_rst(soft_rst), .time_ref(time_ref),
        .delay(delay), .in(spike_l), .out(spike_l_d));
    delay_line u_delay_r (
        .clk(clk), .rst(rst), .en(en), .soft_rst(soft_rst), .time_ref(time_ref),
        .delay(delay), .in(spike_r), .out(spike_r_d));

    // Neuron core: in_syn = {b2, b1, a2, a1}
    neuron_seq u_neuron_seq (
        .clk(clk), .rst(rst), .en(en), .soft_rst(soft_rst), .time_ref(time_ref),
        .in_syn({spike_l, spike_r_d, spike_r, spike_l_d}),
        .w_pack(w_pack), .cfg_a(cfg_a), .cfg_b(cfg_b),
        .spike_a(dir_lr), .spike_b(dir_rl),
        .v_a(v_a), .v_b(v_b), .cnt_a(cnt_a), .cnt_b(cnt_b));

endmodule
