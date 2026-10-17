module half_adder (
    input  wire a,
    input  wire b,
    output wire sum,    // XOR
    output wire carry   // AND
);
    assign sum   = a ^ b;
    assign carry = a & b;
endmodule
