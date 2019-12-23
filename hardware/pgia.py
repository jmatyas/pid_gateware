from migen import *
from migen.build.platforms.sinara import kasli


from artiq.gateware.szservo.pgia_ser import PGIA, PGIAParams
from artiq.gateware.szservo.pads import pgiaPads
from .eem2 import *


pgia_p = PGIAParams(data_width = 16, clk_width = 2)


plat = kasli.Platform(hw_rev="v1.1")
sampler_io = Sampler.io(1, 2)
plat.add_extension(sampler_io)

sampler_eem = sampler_io[2][0].split("_")[0]

pads = pgiaPads(plat, sampler_eem)
m = PGIA(pads, pgia_p, 0x5555)
m.submodules += pads

m.clock_domains.cd_sys = ClockDomain("sys")

clk_signal = Signal()
clk125 = plat.request("clk125_gtp")

m.specials += [
    Instance("IBUFDS_GTE2", i_I = clk125.p, i_IB = clk125.n, o_O = clk_signal),
    Instance("BUFG", i_I = clk_signal, o_O = m.cd_sys.clk)
]

plat.build(m, run=True, build_dir = "artiq/gateware/szservo/hardware/build_pgia", build_name = "pgia")