// Testbench: one strong and one weak synapse.
module tb;

  reg        clk, rst, in1, in2;
  wire       spike;
  wire [7:0] v;

  // override the default weights: synapse 1 strong, synapse 2 weak
  lif_neuron #(.W1(110), .W2(30)) dut (
    .clk(clk), .rst(rst), .in1(in1), .in2(in2),
    .spike(spike), .v(v)
  );

  always #5 clk = ~clk;          // one tick every 10 time units

  initial begin
    $dumpfile("dump.vcd");
    $dumpvars;

    clk = 0; rst = 1; in1 = 0; in2 = 0;
    #20; rst = 0;

    // experiment 1: ONE spike on the strong synapse
    in1 = 1; #10; in1 = 0; #100;

    // experiment 2: ONE spike on the weak synapse
    in2 = 1; #10; in2 = 0; #100;

    // experiment 3: FOUR weak spikes, back-to-back
    in2 = 1; #40; in2 = 0; #100;

    // experiment 4: FOUR weak spikes, spread out in time
    repeat (4) begin
      in2 = 1; #10;
      in2 = 0; #100;
    end

    $finish;
  end

endmodule
