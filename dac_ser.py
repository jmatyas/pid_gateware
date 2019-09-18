from migen import *

from collections import namedtuple


class DAC(Module):
    def __init__(self, pads, ch):
        
        self.data = Signal(16)      # 16-bit-wide data to be transferred to DAC
        self.dav = Signal()         # if dav (data valid) is high, data signal is ready to be read
        self.start = Signal()       # triggers outputting data on dac
        
        self.ready = Signal()       # when it's high, module is ready to accept new data

        dataOut = Signal(2+6+16)    # data width + mode width + address width
        mode = Signal (2)
        address = Signal(6)
        group = Signal(3)
        channel =  Signal(3)

        ldac_duration = Signal(2)   # duration of ldac signal is needed to be longer than just a duration of state
        bits_amount = Signal(max=2+6+16)   # counting bits left to transmit

        # new clock domain - for SPI purpose clk frequency of max 50 MHz is needed.

        clk_counter = Signal(max=2, reset_less=True)
        clk_tick = Signal()
        clk_toggle = Signal()
        
        ###
        
        # new clock domain
        self.comb += clk_tick.eq(clk_counter == 0)
        self.sync += [
            If(clk_counter == 0,
                clk_counter.eq(2 - 1),
                clk_toggle.eq(~clk_toggle)
            ).Else(
                clk_counter.eq(clk_counter - 1)
            )            
        ]

        # concatenating mode, address and data to be sent via SPI
        self.comb += group.eq(1), channel.eq(ch), mode.eq(3)

        self.submodules.fsm = fsm = FSM(reset_state="IDLE")

        self.comb += pads.sclk.eq(clk_toggle)       # assigning clk_toggle to output clock to the device

        fsm.act ("IDLE",
            self.ready.eq(1),
                If((self.start & self.dav), 
                    NextState("DATA"),
                    NextValue(dataOut, Cat(self.data, address, mode)),      # latching data to transmit
                    NextValue(bits_amount, 23),
                    self.ready.eq(0),
                    pads.syncr.eq(0),       # chip select needs to be driven low
                )
        )
        fsm.act("DATA",
            pads.syncr.eq(0),
            If(clk_tick & clk_toggle,
                If(bits_amount == 0,        # if all bits have been transmitted, change state
                    NextState("BUSY"),
                    NextValue(ldac_duration, 2)
                ).Else(
                    NextValue(bits_amount, bits_amount - 1),
                    NextValue(pads.sdi, dataOut[0]),
                    NextValue(dataOut, Cat(dataOut[1:], 0))
                )
            )
        )
        # here not pads busy is needed, but for the purpose of simulation is positive
        fsm.act("BUSY",
            If(pads.busy,
                pads.ldac.eq(0),
                If(ldac_duration == 0,
                    NextState("IDLE")
                ).Else(
                    NextValue(ldac_duration, ldac_duration - 1)
                )
            )
        )

