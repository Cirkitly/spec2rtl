# Icarus Verilog (iverilog) Compatibility Rules

Here are critical rules for writing SystemVerilog that is compatible with the `iverilog` compiler.

1.  **`task` vs. `function` for Time Consumption:**
    *   A `function` must execute in zero time. It CANNOT contain time-consuming statements like delays (`#10`), event controls (`@(posedge clk)`), or `wait` statements. Use functions for immediate calculations.
    *   A `task` is used for procedures that consume time. Any procedure that needs to wait for a clock edge or has a delay MUST be a `task`.

2.  **`for` Loop Variable Declaration:**
    *   DO NOT declare loop variables inside the `for` loop declaration (e.g., `for (int i = 0; ...)`). This is not fully supported.
    *   You MUST declare the loop variable as an `integer` before the loop begins (e.g., `integer i; for (i = 0; ...)`).

3.  **VCD Dumping:**
    *   Use the standard `$dumpfile("filename.vcd");` and `$dumpvars(0, module_instance);` system tasks to create waveform dumps.
