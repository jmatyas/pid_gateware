from migen import *

from artiq.gateware.szservo.adc_ser import ADC, ADCParams
from artiq.gateware.szservo.dac_ser import DAC, DACParams
from artiq.gateware.szservo.iir import IIR, IIRWidths
from artiq.gateware.szservo.pgia_ser import PGIA, PGIAParams
from artiq.language.units import us, ns


# T_CYCLE = Servo.t_cycle*8*ns  # Must match gateware Servo.t_cycle.
COEFF_SHIFT = 11
B_NORM = 1 << COEFF_SHIFT + 1
A_NORM = 1 << COEFF_SHIFT
COEFF_WIDTH = 18
COEFF_MAX = 1 << COEFF_WIDTH - 1

t_dac_busy = 188    # 188 * 8ns = 1.5us; 8 ns when sys_clk=125MHz

class Servo(Module):
    def __init__(self, adc_pads, pgia_pads, dac_pads, adc_p, pgia_p, iir_p, dac_p, pgia_init_val, ch_no = None):
        self.submodules.adc = ADC(adc_pads, adc_p)
        self.submodules.iir = IIR(iir_p)
        self.submodules.dac = DAC(dac_pads, dac_p, ch_no)

        self.submodules.pgia = PGIA(pgia_pads, pgia_p, pgia_init_val)

        # assigning paths and signals - adc data to iir.adc and iir.dac to dac.profie
        # adc channels are reversed on Sampler
        for i, j, k, l in zip(reversed(self.adc.data), self.iir.adc,
                self.iir.dds, self.dac.profile):
            self.comb += j.eq(i), l.eq(k)


        t_adc = (adc_p.t_cnvh + adc_p.t_conv + adc_p.t_rtt +
            adc_p.channels*adc_p.width//adc_p.lanes) + 1
        t_iir = ((1 + 4 + 1) << iir_p.channel) + 1
        if ch_no is None:
            t_dac = ((dac_p.data_width*2*dac_p.clk_width + t_dac_busy + 5 + 6)*dac_p.channels)
        else:
            t_dac = dac_p.data_width*2*dac_p.clk_width + t_dac_busy + 5 + 6

        print(t_adc, t_iir, t_dac)
        self.t_cycle = t_cycle = max(t_adc, t_iir, t_dac)


        T_CYCLE = self.t_cycle*8*ns  # Must match gateware Servo.t_cycle.

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
            If(self.dac.start_dac & self.dac.ready,
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
            self.dac.init.eq(self.start & ~self.dac.initialized),
            self.pgia.start.eq(self.start & ~self.pgia.initialized),
            self.adc.start.eq(self.start & cnt_done & self.pgia.initialized & self.dac.initialized),
            self.iir.start.eq(active[0] & self.adc.done),
            self.dac.start_dac.eq(active[1] & (self.iir.shifting | self.iir.done)),
            self.done.eq(self.dac.ready)
        ]

    def set_coeff(self, channel, profile, coeff, value):
        word, addr, mask = self.iir._coeff(channel, profile, coeff)
        
        # print(channel, profile, coeff, value, word, addr, mask, '{0:b}'.format(mask), len('{0:b}'.format(mask)))
        
        w = self.iir.widths
        val = Signal(2*w.coeff)
        # val - data read from memory
        # value - data to set
        self.sync += val.eq(self.iir.m_coeff[addr])
        if word:
            self.comb += val.eq((val & mask) | ((value & mask) << w.coeff))
        else:
            self.comb += val.eq((value & mask) | (val & (mask << w.coeff)))

        self.sync += self.iir.m_coeff[addr].eq(val)
    

def coeff_to_mu(Kp, Ki):
    Kp *=B_NORM
    if Ki == 0:
        # pure P
        a1 = 0
        b1 = 0
        b0 = int(round(Kp))
    else:
        # I or PI
        Ki *= B_NORM*T_CYCLE/2.
        c = 1.
        a1 = A_NORM
        b0 = int(round(Kp + Ki*c))
        b1 = int(round(Ki - 2.*Kp))
        if b1 == -b0:
            raise ValueError("low integrator gain and/or gain limit")

    if (b0 >= COEFF_MAX or b0 < -COEFF_MAX or
            b1 >= COEFF_MAX or b1 < -COEFF_MAX):
        raise ValueError("high gains")
    
    return a1, b0, b1


if __name__ == "__main__":
    print(coeff_to_mu(2, 0))
        