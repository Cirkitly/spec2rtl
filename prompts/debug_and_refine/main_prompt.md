You are an expert Verilog engineer. Your previous code generation attempt failed with the following feedback. Your task is to regenerate ALL artifacts (RTL, Testbench, etc.) in a single YAML block, fully addressing the feedback.

### Original Specification ###
{spec}

### Feedback to Address ###
{feedback}

### Previous Faulty Code ###
{artifacts}

Now, provide the complete, corrected set of artifacts. CRITICAL: Your entire response must start with ```yaml and end with ```.

Example of the required YAML format:
```yaml
generate_rtl: |
  module ...
  endmodule
generate_testbench: |
  module ...
  endmodule
