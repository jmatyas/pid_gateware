from migen import *
from migen.build.platforms.sinara import kasli


from artiq.gateware.szservo.dac_ser import DAC_init, DACParams
from artiq.gateware.szservo.pads import ZotinoPads
from .eem2 import *


dac_init_p = DACParams(channels=1, data_width = 24, 
        clk_width = 2, init_seq = 1)


plat = kasli.Platform(hw_rev="v1.1")
zotino_io = Zotino.io(0)
plat.add_extension(zotino_io)
zotino_eem = zotino_io[0][0].split("_")[0]


pads = ZotinoPads(plat, zotino_eem)
m = DAC_init(pads, dac_init_p)
m.submodules += pads

m.clock_domains.cd_sys = ClockDomain("sys")

clk_signal = Signal()
clk125 = plat.request("clk125_gtp")

m.specials += [
    Instance("IBUFDS_GTE2", i_I = clk125.p, i_IB = clk125.n, o_O = clk_signal),
    Instance("BUFG", i_I = clk_signal, o_O = m.cd_sys.clk)
]

plat.build(m, run=True, build_dir = "artiq/gateware/szservo/hardware/build_dac_init", build_name = "dac_init")