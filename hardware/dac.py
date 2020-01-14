from migen import *
from migen.build.platforms.sinara import kasli

from migen.genlib.io import DifferentialOutput, DifferentialInput, DDROutput


from artiq.gateware.szservo.dac_ser2 import DAC, DACParams
from artiq.gateware.szservo.pads import ZotinoPads
from .eem2 import *


dac_p = DACParams(channels=8, data_width = 24, 
        clk_width = 2)

eem_no = 4
ch_no = None

plat = kasli.Platform(hw_rev="v1.1")
zotino_io = Zotino.io(eem_no)
plat.add_extension(zotino_io)
zotino_eem = zotino_io[0][0].split("_")[0]


pads = ZotinoPads(plat, zotino_eem)
m = DAC(pads, dac_p)
m.submodules += pads

# if ch_no == None:
#     t_cycle =  (dac_p.data_width*2*dac_p.clk_width + 6)*2
# else:
t_cycle =  (dac_p.data_width*2*dac_p.clk_width + 6)*dac_p.channels + 1

cnt_done = Signal()
cnt = Signal(max=t_cycle + 1)
load_cnt = Signal()

m.comb += cnt_done.eq(cnt == 0)
m.sync += [
    If(cnt_done,
        If(load_cnt,
            cnt.eq(t_cycle - 1)
        )
    ).Else(
        cnt.eq(cnt - 1)
    )
]

for i in range (3, dac_p.channels):
    m.comb += m.profile[i].eq(0x8000000000000000)

m.comb += m.profile[0].eq(0xFFFF000000000000), m.profile[1].eq(0x0000000000000000), m.profile[2].eq(0x1000000000000000)

m.comb += [
    m.dac_init.eq(~m.initialized),
    m.dac_start.eq(m.initialized & (cnt_done | (cnt == t_cycle - 1))),
    load_cnt.eq(m.dac_start),
    [plat.request("user_led").eq(i) for i in [m.initialized, m.dac_start]]
    # led2.eq(m.init),

]


clk_signal = Signal()
clk125 = plat.request("clk125_gtp")

m.specials += [
    Instance("IBUFDS_GTE2", i_I = clk125.p, i_IB = clk125.n, o_O = clk_signal),
    Instance("BUFG", i_I = clk_signal, o_O = m.cd_sys.clk)
]

plat.build(m, run=True, build_dir = "building/dac2_4eem", build_name = "top")