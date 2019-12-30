from migen import *

from collections import namedtuple

from . import spi

DACParams = spi.SPIParams

# values needed for DAC's initialization
AD53XX_CMD_OFFSET = 2 << 22
AD53XX_SPECIAL_OFS0 = 2 << 16


class DAC(spi.SPI):
    def __init__(self, pads, params, ch_no = None):
        super().__init__(pads, params)

        self.profile =[Signal(32 + 16 + 16, reset_less=True)    # 64 bit wide data delivered to dac
            for i in range(params.channels)]

        self.ready = Signal()           # output signal - it lets the controller know that it's transmitted all the data
        self.start_dac = Signal()

        data = [Signal(16) 
            for i in range(params.channels)]        # 16-bit-wide data to be transferred to DAC (ASF from profile + "00")

        mode = Signal (2)           # 2-bit-wide mode signal - hardcoded to "11" - it means that what is being transferred is data
        group = Signal(3)           # hardcoded group to which data is being transferred - in this case "001" which means group 0
        channel =  Signal(3)        # channel number where the data is being trasnferred to (regular number fro 0 to 7 in binary)
        address = [Signal(6) for ch in range(params.channels)]
        dataOut = [Signal(2+6+16) for i in range(params.channels)]      # data width + group width + channel width + mode width

        # signals needed to control the behaviour of data sent to DAC
        word_count = Signal(max=params.channels)
        word_cnt_done = Signal()
        active = Signal(2)

        # if ch_no is not specified all of 'params.channels' channels are sent sequentially to DAC board,
        # otherwise only ch_no's channel is being sent - it allows to improve DAC's update frequency
        if ch_no is None:
            dac_words = Signal(params.data_width*params.channels)       # all words to dac concatenated
            words_amount = params.channels
        else:
            dac_words = Signal(params.data_width)
            words_amount = 1
        
        sr_dac_words = Signal.like(dac_words)           # shift register for words sent to dac; it shifts its content every time data is sent do SPI
        single_dac_word = Signal(params.data_width)     # single word to send to dac - it's equal to 'params.data_width's' LSB


        
        ###

        if ch_no is None:
            self.comb += dac_words.eq(Cat([dataOut[ch] for ch in range(params.channels)]))
        else:
            self.comb += dac_words.eq(dataOut[ch_no])

        
        self.sync += [
            If(self.start_dac,
                active[1].eq(1),            # lagging one cycle to send latched data
                sr_dac_words.eq(dac_words),
            ),
            If(self.spi_ready & self.initialized,
                active[0].eq(1)
            ),
            If(self.spi_ready & self.spi_start,
                active[0].eq(0),
                # active[0].eq(1)
            ),
            # # delaying start of the SPI module for 1 clock cycle to gain some time to latch data properly
            # If(active[1],
            #     active[0].eq(1)
            # ),
            # If(active[0],
            #     active[0].eq(0),
            # ),
            # # latch incoming data
            # If(self.start_dac,
            #     sr_dac_words.eq(dac_words)
            # ),            
            # # # deactivate start flag when every word has been sent and when spi_ready and start has been set
            If(word_cnt_done & ~active[0],
                active[1].eq(0)
            ),
            # # shift data inside the SR when there are words left and when
            If(~word_cnt_done & self.spi_ready & self.initialized & ~active[0],
                sr_dac_words.eq(Cat(sr_dac_words[params.data_width:], Replicate(0, params.data_width))),
            ),
            If(word_cnt_done & self.start_dac,
                If(self.spi_ready & self.initialized,
                    word_count.eq(words_amount - 1)
                )
            ).Elif(~word_cnt_done & self.spi_ready & self.initialized & ~active[0],
                word_count.eq(word_count - 1)
            ),
        ]

        self.comb += [
            word_cnt_done.eq(word_count == 0),

            # word to send to dac always equals to first 'data_width' bits of SR
            single_dac_word.eq(sr_dac_words[:params.data_width]),       
            # trigger SPI module only if dac_start has been set and when both events occured: SPI has been already initailized and SPI is ready
            self.spi_start.eq(active[0] & active[1]),                  
            self.ready.eq((self.spi_ready & ~self.initialized) | 
                (self.initialized & self.spi_ready & ~active[1])),

            If(self.init_latch,
                # it sets DAC config register OFS0 to value 8192. It allows the output of DACs to swing from
                # 10 to -10 V
                pads.ldac.eq(1), pads.clr.eq(1),
                self.dataSPI.eq(AD53XX_CMD_OFFSET | AD53XX_SPECIAL_OFS0 | 0x2000)
                # self.dataSPI.eq(0x6)
            ).Else(
                self.dataSPI.eq(single_dac_word),
                pads.ldac.eq(0), pads.clr.eq(1),
            )
        ]
        
        self.comb += mode.eq(3), group.eq(1)        # group and mode are hard-coded - only first group may be used and only data registers may be updated
        
        # concatanation of latched data + group + channel + mode 
        for ch in range (params.channels):
            self.comb += [
                address[ch][:3].eq(ch), address[ch][3:].eq(group),
                data[ch].eq(Cat(0, 0, self.profile[ch][50:])),
                dataOut[ch].eq(Cat(data[ch], address[ch], mode))
            ]
        

