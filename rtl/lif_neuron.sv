module lif_neuron (
    input  wire       clk,
    input  wire       rst,
    input  wire [3:0] in_current,   // input "water": 0..15 per tick
    output reg        spike,        // 1 for one tick when the neuron fires
    output reg  [7:0] v             // membrane potential: 0..255
);

    localparam THRESHOLD = 100;     // a named constant: the firing level

    // next level = current level - leak (1/8) + input
    wire [7:0] v_next = v - (v >> 3) + in_current;

    always @(posedge clk) begin
        if (rst) begin
            v     <= 0;             // empty bucket at start
            spike <= 0;
        end else if (v_next >= THRESHOLD) begin
            v     <= 0;             // FIRE: empty the bucket...
            spike <= 1;             // ...and ring the bell
        end else begin
            v     <= v_next;        // integrate + leak
            spike <= 0;
        end
    end

endmodule