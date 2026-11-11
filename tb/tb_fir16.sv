// tb/tb_fir16.sv : self-checking testbench against Python golden vectors
`timescale 1ns/1ps
module tb_fir16;
    // >>> CHECK THIS PATH (forward slashes, trailing slash) <<<
    localparam string DIR = "D:/Vlsi_miniproject/ecg_riscv_fir/data/processed/";
    localparam int MAXN = 4096;

    logic               clk = 1'b0;
    logic               rst = 1'b1;
    logic               in_valid = 1'b0;
    logic signed [15:0] in_data  = '0;
    wire                out_valid;
    wire  signed [15:0] out_data;

    fir16 dut (.clk(clk), .rst(rst), .in_valid(in_valid), .in_data(in_data),
               .out_valid(out_valid), .out_data(out_data));

    always #5 clk = ~clk;                       // 100 MHz simulation clock

    logic [15:0] xmem [0:MAXN-1];               // input samples (from x_*.mem)
    logic [15:0] ymem [0:MAXN-1];               // golden outputs (from y_*_fixed.mem)
    int total_errors = 0;

    // gap = clock cycles between samples (1 = back-to-back, 5 = one sample per 5 clocks)
    task automatic run_set(input string name, input int n, input int gap);
        int errors, out_cnt, first_out, cyc, fh;
string xfile, yfile, outfile;
integer check_fd;

errors = 0;
out_cnt = 0;
first_out = -1;

// Construct complete filenames
xfile   = $sformatf("%sx_%s.mem", DIR, name);
yfile   = $sformatf("%sy_%s_fixed.mem", DIR, name);
outfile = $sformatf("%sy_%s_rtl_dec.txt", DIR, name);

// Display paths for debugging
$display("Loading input : %s", xfile);
$display("Loading golden: %s", yfile);

// Check input file exists
check_fd = $fopen(xfile, "r");
if (check_fd == 0)
    $fatal(1, "ERROR: Cannot open input file: %s", xfile);
$fclose(check_fd);

// Check golden file exists
check_fd = $fopen(yfile, "r");
if (check_fd == 0)
    $fatal(1, "ERROR: Cannot open golden file: %s", yfile);
$fclose(check_fd);

// Load files
$readmemh(xfile, xmem);
$readmemh(yfile, ymem);

// Check that data was actually loaded
if ($isunknown(xmem[0]))
    $fatal(1, "ERROR: Input memory contains X values");

if ($isunknown(ymem[0]))
    $fatal(1, "ERROR: Golden memory contains X values");

// Open output file
fh = 0;
if (gap == 1) begin
    fh = $fopen(outfile, "w");
    if (fh == 0)
        $fatal(1, "ERROR: Cannot create output file: %s", outfile);
end
        rst = 1'b1; in_valid = 1'b0;            // reset = empty delay line, like Python
        repeat (3) @(posedge clk);
        #1 rst = 1'b0;

        for (cyc = 0; cyc < n*gap + 8; cyc++) begin
            if ((cyc % gap == 0) && (cyc / gap < n)) begin
                in_valid = 1'b1; in_data = xmem[cyc / gap];
            end else begin
                in_valid = 1'b0; in_data = 16'sh5A5A;   // garbage: DUT must ignore it
            end
            @(posedge clk); #1;                 // look just after the edge
            if (out_valid) begin
                if (first_out < 0) first_out = cyc;
                if (out_cnt < n) begin
                    if (out_data !== ymem[out_cnt]) begin
                        errors++;
                        if (errors <= 10)
                            $display("  MISMATCH %s idx=%0d  RTL=%0d  golden=%0d",
                                     name, out_cnt, out_data, $signed(ymem[out_cnt]));
                    end
                    if (fh != 0) $fdisplay(fh, "%0d", out_data);
                end
                out_cnt++;
            end
        end
        if (out_cnt != n) errors++;             // wrong number of outputs
        $display("[%-6s gap=%0d] outputs=%0d/%0d  first out_valid at cycle %0d  mismatches=%0d  %s",
                 name, gap, out_cnt, n, first_out, errors, (errors == 0) ? "PASS" : "FAIL");
        if (fh != 0) $fclose(fh);
        total_errors += errors;
    endtask

    initial begin
        repeat (4) @(posedge clk);
        run_set("clean",  3600, 1);
        run_set("em",     3600, 1);
        run_set("ma",     3600, 1);
        run_set("50hz",   3600, 1);
        run_set("stress",  612, 1);             // overflow / saturation check
        run_set("clean",  3600, 5);             // sparse samples (what a CPU will do)
        if (total_errors == 0) $display("*** ALL TESTS PASSED: RTL == PYTHON, bit-exact ***");
        else                   $display("*** FAILED: %0d total errors ***", total_errors);
        $finish;
    end
endmodule