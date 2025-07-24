# Acme Corp Verilog Coding Style Guide

## General Rules
- Clock signals MUST be named `clk`.
- Reset signals MUST be active-low and named `rst_n`.
- All signal names should be lowercase with underscores (`snake_case`).

## State Machines (FSMs)
- All Finite State Machines (FSMs) MUST use a **one-hot** encoding.
- State parameters should be prefixed with `S_`, for example: `S_IDLE`, `S_DATA`.

## Comments
- Each module should have a header comment explaining its purpose.
- Complex logic blocks should be preceded by a comment.