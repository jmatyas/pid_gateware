from migen import *

from collections import namedtuple

DACParams = namedtuple("DACParams", [
    "t_data",       # amount of clk cycles needed for data to be transmitted succesfully
    "t_ldaclow",    # amount of clk cycles needed for DAC to react on ldac driven low (minimum)
    "t_sync_ldac",  # amount of clk cylces between rising edge of sync and falling edge of ldac (minimum)
    "channels",
])

class DAC(Module):
    def __init__(self, pads, ch):
        self.profile = [Signal(32 + 16 + 16, reset_less=True)
            for i in range(4)]

        self.data = Signal(16)      # 16-bit-wide data to be transferred to DAC
        self.dav = Signal()         # if dav (data valid) is high, data signal is ready to be read
        self.start = Signal()       # triggers outputting data on dac
        
        self.ready = Signal()       # when it's high, module is ready to accept new data

        dataOut = Signal(2+6+16)    # data width + mode width + address width
        mode = Signal (2)
        address = Signal(6)
        group = Signal(3)
        channel =  Signal(3)

        # new clock domain - for SPI purpose clk frequency of max 50 MHz is needed.

        clk_counter = Signal(max=2, reset_less=True)
        clk_tick = Signal()
        clk_toggle = Signal()
        
        count = Signal(max=24*4)       # hardcoded biggest value of the times
        count_done = Signal()
        count_load = Signal.like(count)
        
        ###
        
        self.comb += self.data.eq(self.profile[0][:16])

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

        self.comb += count_done.eq(count == 0)
        self.sync += [
                count.eq(count - 1),
                If(count_done,
                    count.eq(count_load),
                )
        ]

        # concatenating mode, address and data to be sent via SPI
        self.comb += group.eq(1), channel.eq(ch), mode.eq(3)

        self.submodules.fsm = fsm = FSM(reset_state="IDLE")

        self.comb += pads.sclk.eq(clk_toggle)                               # assigning clk_toggle to output clock to the device

        fsm.act ("IDLE",
            self.ready.eq(1),
                If((self.start & self.dav), 
                    count_load.eq(24*4 - 1),                                # load t_data to counter
                    NextState("DATA"),
                    NextValue(dataOut, Cat(self.data, address, mode)),      # latching data to transmit
                    self.ready.eq(0),
                    pads.syncr.eq(0),                                       # chip select needs to be driven low
                )
        )
        fsm.act("DATA",
            pads.syncr.eq(0),
            If(count_done,                                                  # if all bits have been transmitted, change state
                NextState("BUSY"),
                count_load.eq(3-1),                                         # load t_sync_ldac to counter
            ).Else(
                pads.sdi.eq(dataOut[0]),
                If(clk_toggle & clk_tick,
                    NextValue(dataOut, (Cat(dataOut[1:], 0)))
                )
            )
        )
        # here ~pads.busy is needed, but for the purpose of simulation is positive
        fsm.act("BUSY",
            If(count_done,
                count_load.eq(2-1),                                         # load t_ldac to counter
                If(pads.busy,
                    pads.ldac.eq(0),
                    If(count_done,
                        NextState("IDLE")
                    )
                )
            )
        )
