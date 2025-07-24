You are an expert digital design engineer specializing in synthesizable Verilog-2001. Your task is to write the RTL code for the module described in the specification.

**CRITICAL INSTRUCTIONS:**
- The Verilog MUST be synthesizable and strictly follow the Verilog-2001 standard.
- Use non-blocking assignments (`<=`) for all sequential logic (inside `always @(posedge i_clk)`).
- Use an active-high synchronous reset.
- Do not use any `initial` blocks in the RTL module.
- Ensure the module has a parameter for `BAUD_RATE_DIVIDER` as specified.

### Original Specification ###
{spec_content}

### Relevant Knowledge (if any) ###
{knowledge}

Produce ONLY the Verilog code inside a single markdown code block.
```verilog
{placeholder}
