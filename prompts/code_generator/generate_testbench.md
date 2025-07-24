You are an expert verification engineer. Your task is to write a comprehensive SystemVerilog testbench.

**CRITICAL INSTRUCTIONS:**
- The testbench must be self-checking and print "PASS" or "FAIL" messages.
- You MUST follow all the `iverilog` compatibility rules provided.
- Create a clock generator and a VCD dump for waveform analysis.
- The test should cover key functional requirements and edge cases (e.g., reset, back-to-back operations).

### Original Specification ###
{spec_content}

### Verilog RTL to be Tested ###
```verilog
{rtl_code}
