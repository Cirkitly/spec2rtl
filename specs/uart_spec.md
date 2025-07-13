### Module: UART Transmitter

#### High-Level Description
Design a simple Universal Asynchronous Receiver-Transmitter (UART) module that only handles transmission (TX). It should be synthesizable and follow standard UART protocol.

#### Functional Requirements
- **Data Format**: 1 start bit, 8 data bits, 1 stop bit.
- **Data Input**: An 8-bit parallel data input port `i_data`.
- **Transmit Trigger**: A single-cycle pulse on `i_tx_start` should initiate the transmission of the data currently on `i_data`.
- **Output**: A single serial output pin `o_tx_serial`.
- **Status Signal**: An output signal `o_busy` that is high during transmission and low when idle.
- **Reset**: An active-high synchronous reset `i_reset`.

#### Clocking
- The module should operate on a single clock `i_clk`.
- A configurable `BAUD_RATE_DIVIDER` parameter should be used to control the bit rate. For a 50MHz clock and a 9600 baud rate, the divider would be approximately 50,000,000 / 9600 = 5208.
