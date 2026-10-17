module tb;
  reg  a, b;
  wire sum, carry;

  half_adder dut (.a(a), .b(b), .sum(sum), .carry(carry));

  initial begin
    $dumpfile("dump.vcd");
    $dumpvars;
    $monitor("a=%b b=%b | carry=%b sum=%b", a, b, carry, sum);

    a = 0; b = 0; #10;
    a = 0; b = 1; #10;
    a = 1; b = 0; #10;
    a = 1; b = 1; #10;

    $finish;
  end
endmodule
