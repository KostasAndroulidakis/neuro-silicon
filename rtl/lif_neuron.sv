// Leaky integrate-and-fire neuron with 2 weighted spike inputs.
module lif_neuron #(
    parameter W1        = 60,    // weight of synapse 1
    parameter W2        = 60,    // weight of synapse 2
    parameter THRESHOLD = 100    // firing level
)(
    input  wire       clk,
    input  wire       rst,
    input  wire       in1,       // 1 = spike arrives on input 1 this tick
    input  wire       in2,       // 1 = spike arrives on input 2 this tick
    output reg        spike,     // 1 for one tick when the neuron fires
    output reg  [7:0] v          // membrane potential: 0..255
);

    // each synapse adds its weight only when its input spikes
    wire [7:0] syn1 = in1 ? W1 : 0;
    wire [7:0] syn2 = in2 ? W2 : 0;

    // next level = current level - leak (1/8) + both synapses
    wire [7:0] v_next = v - (v >> 3) + syn1 + syn2;

    always @(posedge clk) begin
        if (rst) begin
            v     <= 0;
            spike <= 0;
        end else if (v_next >= THRESHOLD) begin
            v     <= 0;              // fire and reset
            spike <= 1;
        end else begin
            v     <= v_next;         // integrate + leak
            spike <= 0;
        end
    end

endmodule
