module counter (
    input  wire       clk,
    input  wire       rst,
    output reg  [1:0] count    // 2-bit register: 0..3
);
    always @(posedge clk) begin
        if (rst)
            count <= 2'b00;
        else
            count <= count + 1;
    end
endmodule
