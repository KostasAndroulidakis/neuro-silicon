module tb;
  reg        clk, rst;
  wire [1:0] count;

  counter dut (.clk(clk), .rst(rst), .count(count));

  always #5 clk = ~clk;        // clock: one tick every 10

  initial begin
    $dumpfile("dump.vcd");
    $dumpvars;
    clk = 0; rst = 1;
    #20; rst = 0;              // release reset
    #100;
    $finish;
  end
endmodule
