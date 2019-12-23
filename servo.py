from migen import *

from artiq.gateware.szservo.adc_ser import ADC, ADCParams
from artiq.gateware.szservo.dac_ser import DAC_init, DAC, DACParams
from artiq.gateware.szservo.iir import IIR, IIRWidths
from artiq.gateware.szservo.pgia_ser import PGIA, PGIAParams

class Servo(Module):
    def __init__(self, adc_pads, pgia_pads, dac_pads, adc_p, pgia_p, iir_p, dac_p, dac_init_p, pgia_init_val):
        self.submodules.adc = ADC(adc_pads, adc_p)
        self.submodules.iir = IIR(iir_p)
        self.submodules.dac = DAC(dac_pads, dac_p)

        self.submodules.pgia = PGIA(pgia_pads, pgia_p, pgia_init_val)
        self.submodules.dac_init = DAC_init(dac_pads, dac_init_p)

        # assigning paths and signals - adc data to iir.adc and iir.dac to dac.profie
        # adc channels are reversed on Sampler
        for i, j, k, l in zip(reversed(self.adc.data), self.iir.adc,
                self.iir.dds, self.dac.profile):
            self.comb += j.eq(i), l.eq(k)


        t_adc = (adc_p.t_cnvh + adc_p.t_conv + adc_p.t_rtt +
            adc_p.channels*adc_p.width//adc_p.lanes) + 1
        t_iir = ((1 + 4 + 1) << iir_p.channel) + 1
        t_dac = (24*4 + 2 + 3)

        t_cycle = max(t_adc, t_iir, t_dac)

        self.start = Signal()
        self.done = Signal()

        t_restart = t_cycle - t_adc + 1

        cnt = Signal(max = t_restart)
        cnt_done = Signal()
        active = Signal(3)
        
        self.sync += [
            If(self.dac.ready,
                active[2].eq(0)
            ),
            If(self.dac.start & self.dac.ready,
                active[2].eq(1),
                active[1].eq(0)
            ),
            If(self.iir.start & self.iir.done, 
                active[1].eq(1),
                active[0].eq(0)
            ),
            If(~cnt_done & self.adc.done,
                cnt.eq(cnt - 1)
            ),
            If(self.adc.start & self.adc.done,
                active[0].eq(1),
                cnt.eq(t_restart - 1)
            )
        ]
        

        self.comb += [
            cnt_done.eq(cnt == 0),
            self.dac_init.start.eq(self.start & ~self.dac_init.initialized),
            self.pgia.start.eq(self.start & ~self.pgia.initialized),
            self.adc.start.eq(self.start & cnt_done & self.pgia.initialized & self.dac_init.initialized),
            self.iir.start.eq(active[0] & self.adc.done),
            self.dac.start.eq(active[1] & (self.iir.shifting | self.iir.done)),
            self.done.eq(self.dac.ready)
        ]

        