from migen import *

from collections import namedtuple

from . import spi2

DACParams = spi2.SPIParams

# values needed for DAC's initialization
AD53XX_SPECIAL_OFS0 = 2 << 16
AD53XX_SPECIAL_OFS1 = 3 << 16
ZOTINO_OFFSET = 8192
AD53XX_CMD_OFFSET = 2<<22

class DAC(spi2.SPI2):
    def __init__(self, pads, params):
        super().__init__(pads, params)

        self.profile =[Signal(32 + 16 + 16, reset_less=True)    # 64 bit wide data delivered to dac
            for i in range(params.channels)]

        self.dac_ready = Signal()           # output signal - it lets the controller know that it's transmitted all the data
        self.dac_start = Signal()
        self.dac_init = Signal()

        self.initialized = Signal()

        data = [Signal(16) 
            for i in range(params.channels)]        # 16-bit-wide data to be transferred to DAC (ASF from profile + "00")

        mode = Signal (2)           # 2-bit-wide mode signal - hardcoded to "11" - it means that what is being transferred is data
        group = Signal(3)           # hardcoded group to which data is being transferred - in this case "001" which means group 0
        channel =  Signal(3)        # channel number where the data is being trasnferred to (regular number fro 0 to 7 in binary)
        address = [Signal(6) for ch in range(params.channels)]
        dataOut = [Signal(2+6+16) for i in range(params.channels)]      # data width + group width + channel width + mode width

        # signals needed to control the behaviour of data sent to DAC
        words = Signal(max = params.channels + 1)       # all words to dac concatenated

        sr_words = Signal(params.data_width*params.channels)          # shift register for words sent to dac; it shifts its content every time data is sent do SPI
        single_word = Signal(params.data_width)     # single word to send to dac - it's equal to 'params.data_width's' LSB

        # signals used as an edge detector
        current_spi = Signal()
        old_spi = Signal()
        

        ###

        self.submodules.fsm_dac = fsm_dac = FSM("IDLE")

        fsm_dac.act("IDLE",
            self.dac_ready.eq(1),       # when in IDLE, device is ready to accept new data
            # if controller issues dac_init and devices has not yet been initialized, 
            # whith next rising edge initailizing sequence is latched into //single_word// vector 
            # and spi communication is began
            If(self.dac_init & ~self.initialized,
                NextValue(single_word, (Cat((AD53XX_SPECIAL_OFS0 | ZOTINO_OFFSET), Replicate(0, 6)))),
                NextValue(self.spi_start, 1),
                NextState("INIT")
            # if controller issues a start event, a number of words is latched into the counter and data 
            # from //profiles// is calculated and latched also
            ).Elif(self.dac_start,
                NextValue(words, params.channels),
                NextValue(sr_words, Cat([dataOut[ch] for ch in range(params.channels)])),

                NextState("DATA")
            )
        )           

        fsm_dac.act("INIT",
            If(self.fsm.ce,
                NextValue(self.spi_start, 0),            
            ),
            # if //spi_ready// changes its state to HIGH, device may be considered initialized
            If(((~old_spi) & current_spi),
                NextValue(self.initialized, 1),
                NextState("IDLE")
            )
        )


        fsm_dac.act("DATA",
            # with every rising edge of //spi_ready// word counter is diminished; 
            # when it is equal to 0, all words has been already sent; otherwise, words are shifted inside
            # the words shift register by value of the single word data width.
            # in other case, first word from the word shift register is latched into //single_word// and tranmission
            # via SPI begins
            If(words == 0,
                NextState("IDLE"),
            ).Elif(((~old_spi) & current_spi),
                NextValue(words, words - 1),
                NextValue(sr_words, (Cat(sr_words[params.data_width:], Replicate(0, params.data_width)))),
            ).Else(
                NextValue(single_word, sr_words[:params.data_width]),
                NextValue(self.spi_start, 1),
                If(~self.spi_ready,
                    NextValue(self.spi_start, 0)
                ),
            )

        )

        # SPI module is always supplied with the data from the //single_word//
        self.comb += self.dataSPI.eq(single_word)

        self.sync += old_spi.eq(current_spi)
        self.comb += current_spi.eq(self.spi_ready)

        self.comb += mode.eq(3), group.eq(1)        # group and mode are hard-coded - only first group may be used and only data registers may be updated
        
        # concatanation of latched data + group + channel + mode 
        for ch in range (params.channels):
            self.comb += [
                address[ch][:3].eq(ch), address[ch][3:].eq(group),
                data[ch].eq(Cat(0, 0, self.profile[ch][50:])),
                dataOut[ch].eq(Cat(data[ch], address[ch], mode))            
                ]