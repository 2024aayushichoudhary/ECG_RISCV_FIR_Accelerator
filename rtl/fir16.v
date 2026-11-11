// rtl/fir16.v : 16-tap fixed-point FIR, Q1.15 coefficients, FC = 35 Hz @ 360 Hz
`timescale 1ns/1ps
module fir16 (
    input  wire               clk,
    input  wire               rst,        // synchronous, active-high
    input  wire               in_valid,   // 1-cycle strobe: in_data is a new sample
    input  wire signed [15:0] in_data,
    output reg                out_valid,  // 1-cycle strobe: out_data is a result
    output reg  signed [15:0] out_data
);
    // ---- coefficients: copied from results/tables/fir_coefficients_q15.txt ----
    function signed [15:0] coef;
        input integer k;
        begin
            case (k)
                0:  coef = -16'sd113;
                1:  coef = -16'sd146;
                2:  coef = -16'sd98;
                3:  coef =  16'sd363;
                4:  coef =  16'sd1520;
                5:  coef =  16'sd3300;
                6:  coef =  16'sd5174;
                7:  coef =  16'sd6384;
                8:  coef =  16'sd6384;
                9:  coef =  16'sd5174;
                10: coef =  16'sd3300;
                11: coef =  16'sd1520;
                12: coef =  16'sd363;
                13: coef = -16'sd98;
                14: coef = -16'sd146;
                15: coef = -16'sd113;
                default: coef = 16'sd0;
            endcase
        end
    endfunction

    // ---- delay line: xd[0] = x[n-1] ... xd[14] = x[n-15] ----
    reg signed [15:0] xd [0:14];
    integer i;
    always @(posedge clk) begin
        if (rst) begin
            for (i = 0; i < 15; i = i + 1) xd[i] <= 16'sd0;
        end else if (in_valid) begin
            xd[0] <= in_data;
            for (i = 1; i < 15; i = i + 1) xd[i] <= xd[i-1];
        end
    end

    // ---- stage 1: 16 signed multiplies (no reset needed: valid bit guards them) ----
    reg signed [31:0] p [0:15];
    integer j;
    always @(posedge clk) begin
        if (in_valid) begin
            p[0] <= in_data * coef(0);                       // x[n]   * h0
            for (j = 1; j < 16; j = j + 1)
                p[j] <= xd[j-1] * coef(j);                   // x[n-j] * hj
        end
    end

    // ---- stage 2: adder tree, 32-bit signed (bound proven in 03_fixed_point.py) ----
    reg signed [31:0] acc;
    always @(posedge clk) begin
        acc <= p[0]  + p[1]  + p[2]  + p[3]
             + p[4]  + p[5]  + p[6]  + p[7]
             + p[8]  + p[9]  + p[10] + p[11]
             + p[12] + p[13] + p[14] + p[15];
    end

    // ---- stage 3: round to nearest, >>> 15, saturate to int16 ----
    wire signed [31:0] rnd = acc + 32'sd16384;       // + 2^14 (half an output LSB)
    wire signed [31:0] shf = rnd >>> 15;             // arithmetic shift
    wire signed [15:0] sat = (shf >  32'sd32767)  ? 16'sh7FFF :
                             (shf < -32'sd32768) ? 16'sh8000 :
                              shf[15:0];

    // ---- valid pipeline + output register ----
    reg v1, v2;
    always @(posedge clk) begin
        if (rst) begin
            v1 <= 1'b0; v2 <= 1'b0; out_valid <= 1'b0; out_data <= 16'sd0;
        end else begin
            v1        <= in_valid;
            v2        <= v1;
            out_valid <= v2;
            if (v2) out_data <= sat;
        end
    end
endmodule