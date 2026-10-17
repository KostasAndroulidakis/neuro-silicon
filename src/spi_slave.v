// spi_slave: synchronous SPI slave (mode 0, MSB first) -> register bus.
//
// All three SPI pins are sampled by clk through 2-FF synchronisers, so there is
// a single clock domain. Edges are seen ~3 clk late; MISO is updated on the
// *rising* SCK edge (after the master has sampled), which leaves a full SCK
// period of margin. Requirement: SCK <= clk/8.
//
// One transaction = CS_n low, 16 SCK pulses:
//   bits 15..8 (byte 0, MOSI): [7] 1 = read, 0 = write; [6:0] address
//   bits  7..0 (byte 1):       write -> data on MOSI, applied after the 16th edge
//                              read  -> data on MISO (rd_data for rd_addr)
// Extra SCK pulses while CS_n stays low are ignored. CS_n high aborts/clears.

`default_nettype none

module spi_slave (
    input  wire       clk,
    input  wire       rst,
    // pins
    input  wire       sck,
    input  wire       mosi,
    input  wire       cs_n,
    output wire       miso,
    // register bus (to config_regs)
    output reg        wr_en,      // 1-clk pulse
    output reg  [6:0] wr_addr,
    output reg  [7:0] wr_data,
    output reg  [6:0] rd_addr,    // valid from the end of byte 0
    input  wire [7:0] rd_data     // combinational response from config_regs
);

    // --- Synchronisers and edge detection --------------------------------------
    reg [1:0] sck_s, mosi_s, cs_s;
    reg       sck_q;
    always @(posedge clk) begin
        sck_s  <= {sck_s[0],  sck};
        mosi_s <= {mosi_s[0], mosi};
        cs_s   <= {cs_s[0],   cs_n};
        sck_q  <= sck_s[1];
    end
    wire sck_rise = sck_s[1] & ~sck_q;
    wire selected = ~cs_s[1];
    wire mosi_now = mosi_s[1];

    // --- Shift logic -------------------------------------------------------------
    reg [4:0] bit_cnt;      // 0..16
    reg [6:0] sr_in;        // MOSI shift register (7 bits + the bit being received)
    reg [7:0] sr_out;       // MISO shift register
    reg       is_read;
    reg [1:0] load_out;     // rd_addr became valid: load sr_out 2 cycles later
                            // (tolerates a registered rd_data path)

    assign miso = sr_out[7];

    always @(posedge clk) begin
        wr_en    <= 1'b0;
        load_out <= {load_out[0], 1'b0};
        if (rst) begin
            bit_cnt <= 5'd0;  sr_in <= 7'd0;  sr_out <= 8'd0;  is_read <= 1'b0;
            rd_addr <= 7'd0;  wr_addr <= 7'd0;  wr_data <= 8'd0;  load_out <= 2'b00;
        end else if (!selected) begin
            bit_cnt <= 5'd0;  sr_in <= 7'd0;  sr_out <= 8'd0;  is_read <= 1'b0;
        end else begin
            if (load_out[1])
                sr_out <= is_read ? rd_data : 8'd0;
            if (sck_rise && bit_cnt != 5'd16) begin
                sr_in   <= {sr_in[5:0], mosi_now};
                bit_cnt <= bit_cnt + 5'd1;
                if (bit_cnt == 5'd7) begin               // command byte complete
                    is_read  <= sr_in[6];
                    rd_addr  <= {sr_in[5:0], mosi_now};
                    wr_addr  <= {sr_in[5:0], mosi_now};
                    load_out <= 2'b01;
                end
                if (bit_cnt > 5'd7)                      // master sampled: next bit
                    sr_out <= {sr_out[6:0], 1'b0};
                if (bit_cnt == 5'd15 && !is_read) begin  // data byte complete
                    wr_en   <= 1'b1;
                    wr_data <= {sr_in[6:0], mosi_now};
                end
            end
        end
    end

endmodule
