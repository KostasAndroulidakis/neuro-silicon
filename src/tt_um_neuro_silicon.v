/*
 * neuro-silicon: Tiny Tapeout wrapper.
 *
 * Responsibilities of this file (and nothing else):
 *   1. map Tiny Tapeout's fixed pins to named signals (see info.yaml)
 *   2. synchronise the external active-low reset into an internal active-high one
 *   3. instantiate the chip top level (motion_detector)
 *
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

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
    wire dir_lr, dir_rl, spi_miso, time_ref;

    assign uo_out  = {2'b00, time_ref, dir_rl, dir_lr, spi_miso, dir_rl, dir_lr};
    assign uio_out = 8'b0;      // bidirectional pins unused...
    assign uio_oe  = 8'b0;      // ...configured as inputs

    // --- 2. Reset synchroniser (2 flip-flops, active-high internally) -----
    reg rst_meta, rst;
    always @(posedge clk) begin
        rst_meta <= ~rst_n;
        rst      <= rst_meta;
    end

    // --- 3. The chip -------------------------------------------------------
    motion_detector u_chip (
        .clk      (clk),
        .rst      (rst),
        .sensor_l (ui_in[0]),
        .sensor_r (ui_in[1]),
        .spi_sck  (ui_in[2]),
        .spi_mosi (ui_in[3]),
        .spi_cs_n (ui_in[4]),
        .spi_miso (spi_miso),
        .dir_lr   (dir_lr),
        .dir_rl   (dir_rl),
        .time_ref (time_ref)
    );

    wire _unused = &{ena, ui_in[7:5], uio_in, 1'b0};

endmodule
