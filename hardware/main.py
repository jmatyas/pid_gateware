from migen import *
from migen.build.platforms.sinara import kasli

# from math import log2, ceil

# from artiq.gateware.szservo.adc_ser import ADC, ADCParams
# from artiq.gateware.szservo.dac_ser import DAC_init, DAC, DACParams
# from artiq.gateware.szservo.iir import IIR, IIRWidths
# from artiq.gateware.szservo.pgia_ser import PGIA, PGIAParams
from artiq.gateware.szservo import servo
from artiq.gateware.szservo.pads import ZotinoPads, SamplerPads, pgiaPads
from .eem2 import *

plat = kasli.Platform(hw_rev="v1.1")

sampler_conn = 3
sampler_aux = 2
zotino_conn = 4

adc_io = Sampler.io(sampler_conn, sampler_aux)
dac_io = Zotino.io(zotino_conn)

plat.add_extension(adc_io)
plat.add_extension(dac_io)

adc_eem = adc_io[sampler_aux][0].split("_")[0]
pgia_eem = adc_io[2][0].split("_")[0]
dac_eem = dac_io[zotino_conn][0].split("_")[0]

adc_pads = SamplerPads(plat, adc_eem)
pgia_pads = pgiaPads(plat, pgia_eem)
dac_pads = ZotinoPads(plat, dac_eem)

adc_p = servo.ADCParams(width=16, channels=2, lanes=1,
                t_cnvh=4, t_conv=57 - 4, t_rtt=4 + 4)
iir_p = servo.IIRWidths(state=25, coeff=18, adc=16, asf=14, word=16,
                accu=48, shift=11, channel=4, profile=1)
dac_p = servo.DACParams(data_width = 24, clk_width = 2,
                channels=adc_p.channels)
pgia_p = servo.PGIAParams(data_width = 16, clk_width = 2)

pgia_init_val = 0x0000


m = servo.Servo(adc_pads, pgia_pads, dac_pads, adc_p, pgia_p, iir_p, dac_p,
            pgia_init_val)

m.submodules += adc_pads, pgia_pads, dac_pads

m.comb += m.start.eq(1)
m.comb += [
    [plat.request("user_led").eq(i) for i in [m.dac.initialized, m.pgia.initialized, m.iir.done_writing]]
    # led2.eq(m.init),

]


clk_signal = Signal()
clk125 = plat.request("clk125_gtp")

m.specials += [
    Instance("IBUFDS_GTE2", i_I = clk125.p, i_IB = clk125.n, o_O = clk_signal),
    Instance("BUFG", i_I = clk_signal, o_O = m.cd_sys.clk)
]

plat.build(m, run=True, build_dir = "building/servo/2ch_kp1_z_forem_30us_lag_with_offset/pgia0000", build_name = "top")
