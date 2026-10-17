// edge_detect: asynchronous sensor level -> one clk-wide spike on each rising edge.
//
// Two flip-flops synchronise the external signal to clk (metastability guard),
// a third remembers the previous value. pulse = "went high this cycle".

`default_nettype none

module edge_detect (
    input  wire clk,
    input  wire rst,
    input  wire level,     // raw sensor pin, may change at any time
    output wire pulse      // 1 for one clk per rising edge, 2 clk after it
);

    reg sync0, sync1, prev;

    always @(posedge clk) begin
        if (rst) begin
            sync0 <= 1'b0;
            sync1 <= 1'b0;
            prev  <= 1'b0;
        end else begin
            sync0 <= level;
            sync1 <= sync0;
            prev  <= sync1;
        end
    end

    assign pulse = sync1 & ~prev;

endmodule
