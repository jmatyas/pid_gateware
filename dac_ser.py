from migen import *

from collections import namedtuple

from . import spi

DACParams = spi.SPIParams

AD53XX_CMD_OFFSET = 2 << 22
AD53XX_SPECIAL_OFS0 = 2 << 16


# class DAC_init(spi.SPI):
#     def __init__(self, pads, params):
#         # it sets DAC config register OFS0 to value 8192. It allows the output of DACs to swing from
#         # 10 to -10 V
#         super().__init__(pads, params)

#         AD53XX_CMD_OFFSET = 2 << 22
#         AD53XX_SPECIAL_OFS0 = 2 << 16
        
#         self.comb += pads.ldac.eq(1), pads.clr.eq(1)
#         self.comb += self.dataSPI.eq(AD53XX_CMD_OFFSET | AD53XX_SPECIAL_OFS0 | 0x2000)


class DAC(spi.SPI):
    def __init__(self, pads, params):
        super().__init__(pads, params)

        self.profile =[Signal(32 + 16 + 16, reset_less=True)    # 64 bit wide data delivered to dac
            for i in range(params.channels)]

        
        data = [Signal(16) 
            for i in range(params.channels)]        # 16-bit-wide data to be transferred to DAC

        mode = Signal (2)           # 2-bit-wide mode signal - hardcoded to "11" - it means that what is being transferred is data
        group = Signal(3)           # hardcoded group to which data is being transferred - in this case "001" which means group 0
        channel =  Signal(3)        # channel number where the data is being trasnferred to (regular number fro 0 to 7 in binary)
        address = [Signal(6) for ch in range(params.channels)]
        dataOut = [Signal(2+6+16) for i in range(params.channels)]      # data width + group width + channel width + mode width

        latch_dataOut = Signal(params.data_width*params.channels)       # latch to latch outgoing data

       
        ###

        self.comb += mode.eq(3), group.eq(1)        # group and mode are hard-coded
        
        # concatanation of latched data + group + channel + mode 
        for ch in range (params.channels):
            self.comb += [
                address[ch][:3].eq(ch), address[ch][3:].eq(group),
                data[ch].eq(Cat(0, 0, self.profile[ch][50:])),
                dataOut[ch].eq(Cat(data[ch], address[ch], mode))
            ]
        self.comb += latch_dataOut.eq(Cat([dataOut[ch] for ch in range(params.channels)]))      # concatenation of data from all of channels, ch0 is the LSB part
        # self.comb += self.dataSPI.eq(latch_dataOut)

        self.comb += [
            If(self.init_latch,
                # it sets DAC config register OFS0 to value 8192. It allows the output of DACs to swing from
                # 10 to -10 V
                pads.ldac.eq(1), pads.clr.eq(1),
                self.dataSPI.eq(AD53XX_CMD_OFFSET | AD53XX_SPECIAL_OFS0 | 0x2000)
            ).Else(
                self.dataSPI.eq(latch_dataOut),
                pads.ldac.eq(0), pads.clr.eq(1),
            )
        ]
