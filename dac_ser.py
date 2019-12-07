from migen import *

from collections import namedtuple

from . import spi

DACParams = spi.SPIParams

# konfiguracja urzadzenia nastepuje przez komendy software'owe z poziomy phy/rtio. do wiadomosci trzeba dokleic adresy

class DAC(spi.SPI):
    def __init__(self, pads, params):
        super().__init__(pads, params)

        self.profile =[Signal(32 + 16 + 16, reset_less=True)
            for i in range(params.channels)]

        
        data = [Signal(16) 
            for i in range(params.channels)]        # 16-bit-wide data to be transferred to DAC

        mode = Signal (2)           # 2-bit-wide mode signal - hardcoded to "11" - it means that what is being transferred is data
        group = Signal(3)           # hardcoded group to which data is being transferred - in this case "001" which means group 0
        channel =  Signal(3)        # channel number where the data is being trasnferred to (regular number fro 0 to 7 in binary)
        address = [Signal(6) for ch in range(params.channels)]
        dataOut = [Signal(2+6+16) for i in range(params.channels)]    # data width + group width + channel width + mode width

        sr_datOut = Signal(params.data_width*params.channels)

       
        ###
        
        self.comb += mode.eq(3), group.eq(1)
        # self.comb += data[0].eq(Cat(0, 0, self.profile[0][50:]))
        for ch in range (params.channels):
            self.comb += [
                address[ch][:3].eq(ch), address[ch][3:].eq(group),
                data[ch].eq(Cat(0, 0, self.profile[ch][50:])),
                dataOut[ch].eq(Cat(data[ch], address[ch], mode))
            ]
        self.comb += sr_datOut.eq(Cat([dataOut[ch] for ch in range(params.channels)]))
        self.comb += self.dataSPI.eq(sr_datOut)

        # for channel in range (params.channels):
        #     self.comb += \
        #         [
        #             dataOut[channel].eq(Cat(self.profile[channel][50:], 00, group, channel, mode))
        #         ]
        # self.comb += dataOut[0].eq(Cat(self.profile[0][50:], 00, group, channel, mode))


        # self.comb += count_done.eq(count == 0)
        # self.sync += [
        #     count.eq(count - 1),
        #     If(count_done,
        #         count.eq(count_load),
        #     )
        # ]
        

        # # concatenating mode, address and data to be sent via SPI
        # # self.comb += group.eq(1), channel.eq(params.channels), mode.eq(3)

        # self.submodules.fsm = fsm = FSM(reset_state="IDLE")

        # self.comb += pads.sclk.eq(clk_toggle)                               # assigning clk_toggle to output clock to the device

        # fsm.act ("IDLE",
        #     self.ready.eq(1),
        #         If((self.start), # & self.dav), 
        #             count_load.eq(24*4 - 1),                                # load t_data to counter
        #             NextState("DATA"),
        #             # [NextValue(dataOut[ch], Cat(data[ch], address[ch], mode))
        #             #     for ch in range (params.channels)],      # latching data to transmit
        #             NextValue(sr_datOut, Cat([dataOut[ch] for ch in range(params.channels)])),
        #             self.ready.eq(0),
        #             pads.syncr.eq(0),                                       # chip select needs to be driven low
        #         )
        # )
        # fsm.act("DATA",
        #     pads.syncr.eq(0),
        #     If(count_done,                                                  # if all bits have been transmitted, change state
        #         NextState("BUSY"),
        #         count_load.eq(3-1),                                         # load t_sync_ldac to counter
        #     ).Else(
        #         pads.sdi.eq(sr_datOut[-1]),
        #         If(clk_toggle & clk_tick,
        #             NextValue(sr_datOut, (Cat(0, sr_datOut[:-1]))),

        #             # [NextValue(dataOut[ch], (Cat(0, dataOut[ch][:-1])))
        #             #     for ch in range(params.channels)],
        #         )
        #         # pads.sdi.eq(dataOut[0][-1]),
        #         # If(clk_toggle & clk_tick,
        #         #     NextValue(dataOut[0], (Cat(0, dataOut[0][:-1]))),

        #         #     # [NextValue(dataOut[ch], (Cat(0, dataOut[ch][:-1])))
        #         #     #     for ch in range(params.channels)],
        #         # )
        #     )
        # )
        # # here ~pads.busy is needed, but for the purpose of simulation is positive
        # fsm.act("BUSY",
        #     If(count_done,
        #         count_load.eq(2-1),                                         # load t_ldac to counter
        #         If(pads.busy,
        #             pads.ldac.eq(0),
        #             NextState("IDLE"),
        #         )
        #     )
        # )
