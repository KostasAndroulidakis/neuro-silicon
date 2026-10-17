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

    // Not yet built: outputs idle.
    assign dir_lr   = 1'b0;
    assign dir_rl   = 1'b0;
    assign spi_miso = 1'b0;
    assign spike_a  = 1'b0;
    assign spike_b  = 1'b0;

    // Keep the linter quiet about inputs not consumed yet.
    wire _unused = &{ena, sensor_l, sensor_r, spi_sck, spi_mosi, spi_cs_n,
                     ui_in[7:5], uio_in, 1'b0};

endmodule
