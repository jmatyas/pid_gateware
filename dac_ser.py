from migen import *

from collections import namedtuple

from . import spi

DACParams = spi.SPIParams

# konfiguracja urzadzenia nastepuje przez komendy software'owe z poziomy phy/rtio. do wiadomosci trzeba dokleic adresy

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
        self.comb += latch_dataOut.eq(Cat([dataOut[ch] for ch in range(params.channels)]))      # concatenation of data from all of channels
        self.comb += self.dataSPI.eq(latch_dataOut)
