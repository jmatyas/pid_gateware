from migen import *
from collections import namedtuple


SPIParams = namedtuple("DACParams", [
    "channels",     # amount of channels in use
    "data_width",   # width of one portion of data to be transferred
    "clk_width",    # clock half cycle width
])

class SPI(Module):
    def __init__(self, pads, params):
        
        self.dataSPI = Signal(params.data_width*params.channels, reset_less=True)

        sr_data = Signal.like(self.dataSPI)    # shift register with input data latched in it


        self.start = Signal()           # triggers outputting data on dac
        self.ready = Signal()           # when it's high, module is ready to accept new data
        self.busy = Signal(reset = 1)   # for testing purpose - for using it should be deleted and all occurances should be replaced with pads.busy

        clk_counter = Signal(max=params.clk_width)
        clk_cnt_done = Signal()
        
        bits = Signal(max = params.data_width*params.channels + 1)
        
        cnt_load = Signal()
        cnt_done = Signal()

        data_load = Signal()

        word_counter = Signal(max = params.channels + 1) 
        
        ###

        assert params.clk_width >= 1

        # new clock domain - for SPI's purpose clk freq of max 50MHz is needed
        self.comb += clk_cnt_done.eq(clk_counter == 0)
        self.sync += [
            If(clk_cnt_done, 
                If(cnt_load,
                    clk_counter.eq(params.clk_width - 1),
                )
            ).Else(
                clk_counter.eq(clk_counter-1)
            )
        ]

        self.submodules.fsm = fsm = CEInserter()(FSM("IDLE"))
        self.comb += fsm.ce.eq(clk_cnt_done)
        
        self.comb += pads.ldac.eq(0)                # ldac driven constantly to 0
        self.comb += pads.sdi.eq(sr_data[0])       # output data - LSB first
        # self.comb += pads.sdi.eq(sr_data[-1])       # output data - MSB first
        
        fsm.act("IDLE",
            self.ready.eq(1),       
            pads.syncr.eq(1),
            If(self.start,
                cnt_load.eq(1),         # enables sclk
                NextState("SETUP"),
                data_load.eq(1)         # signalling to latch the input data in the shift register
            )
        )
        fsm.act("SETUP",
            pads.syncr.eq(0),           # chip select driven low
            cnt_load.eq(1),             
            pads.sclk.eq(1),            # gives clock signal on the output pin; when it enters SETUP state the sclk is driven high
                                        # and when it enters HOLD, sclk is driven low - that's when the DAC reads the data - on the falling edge

            If(bits == 0,               # if the whole word (in this case 24 bits) has been transmitter, got o DELAY
                NextState("DELAY")
            ).Else(
                NextState("HOLD")
            )
        )
        fsm.act("HOLD",
            pads.syncr.eq(0),
            cnt_load.eq(1),
            NextState("SETUP"),
        )

        # DELAY state is needed in order to delay syncr being driven high by one SCLK cycle
        fsm.act("DELAY",                
            pads.syncr.eq(0),
            NextState("BUSY_LOW")
        )

        fsm.act("BUSY_LOW",             # chip select driven high and waitng for BUSY bein driven low 
            pads.syncr.eq(1),
            If(~self.busy,
                NextState("BUSY_HIGH")
            )
        )

        # waiting for busy being driven high again - 
        # this means the DAC chip accepted data and is ready for next transmission
        fsm.act("BUSY_HIGH",
            If((self.busy & (word_counter == 0)),   
                NextState("IDLE")
            ).Elif(self.busy,
                NextState("SETUP"),
                cnt_load.eq(1)
            )
        )


        self.sync += [
            If(fsm.ce,
                # counts down how many bits are left to be transmitted 
                # and shifts output register by one bit to the left
                If(fsm.before_leaving("HOLD"),
                    bits.eq(bits - 1),
                    # sr_data[1:].eq(sr_data),
                    sr_data.eq(Cat(sr_data[1:], 0))         # LSB first
                    # sr_data.eq(Cat(0, sr_data[:-1]))         # MSB first
                ),
                # word counter is needed because DAC chip requires controller to set SYNC high after
                # every sent 24 bits. That's how it knows whether is there any word/bit left to be sent.
                # Word coutner is the number of channels used by ADC and IIR
                If(fsm.ongoing("IDLE"),
                    bits.eq(params.data_width-1),
                    word_counter.eq(params.channels)
                ),
                If(fsm.before_leaving("BUSY_HIGH"),
                    bits.eq(params.data_width-1),
                ),
                # Shiftin data is needed for multi-word transmissions
                If(fsm.ongoing("DELAY"),
                    word_counter.eq(word_counter - 1),
                    sr_data.eq(Cat(sr_data[1:], 0))         # LSB first
                    # sr_data.eq(Cat(0, sr_data[:-1]))         # MSB first
                ),
                If(data_load,
                    sr_data.eq(self.dataSPI)
                )
            )
        ]
