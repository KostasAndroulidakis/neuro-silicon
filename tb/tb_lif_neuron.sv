module tb;

  reg        clk, rst;
  reg  [3:0] in_current;
  wire       spike;
  wire [7:0] v;

  lif_neuron dut (.clk(clk), .rst(rst), .in_current(in_current),
                  .spike(spike), .v(v));

  always #5 clk = ~clk;

  initial begin
    $dumpfile("dump.vcd");
    $dumpvars;

    clk = 0; rst = 1; in_current = 0;
    #20; rst = 0;

    in_current = 15; #400;    // experiment 1: strong input -> fires fast
    in_current = 13; #400;    // experiment 2: minimum input -> fires slowly
    in_current = 12; #400;    // experiment 3: just below -> never fires

    $finish;
  end

endmodule