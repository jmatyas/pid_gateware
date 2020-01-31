from migen import *
from migen.build.platforms.sinara import kasli

from artiq.gateware.szservo import servo
from artiq.gateware.szservo.pads import ZotinoPads, SamplerPads, PGIAPads
from .eem2 import *

# number of channels used for control
channels_no = 2

# lists of PI controller's coefficients in the continuous-frequency domain;
Kps = [2 for i in range(channels_no)]
Kis = [0 for i in range(channels_no)]


plat = kasli.Platform(hw_rev="v1.1")

# numbers of EEM extentions to which particular boards are connected
sampler_conn = 3
sampler_aux = 2
zotino_conn = 4

# getting EEM extentions' and theirs subsignals' names
adc_io = Sampler.io(sampler_conn, sampler_aux)
dac_io = Zotino.io(zotino_conn)

# mapping EEM extensions' signals to physical pins
plat.add_extension(adc_io)
plat.add_extension(dac_io)

# extracting name used by other functions
adc_eem = adc_io[sampler_aux][0].split("_")[0]
pgia_eem = adc_io[2][0].split("_")[0]
dac_eem = dac_io[zotino_conn][0].split("_")[0]

# creating pads wrapper
adc_pads = SamplerPads(plat, adc_eem)
pgia_pads = PGIAPads(plat, pgia_eem)
dac_pads = ZotinoPads(plat, dac_eem)


# creating params used by each of the modules used by Servo
adc_p = servo.ADCParams(width=16, channels=channels_no, lanes=int(channels_no/2),
                t_cnvh=4, t_conv=57 - 4, t_rtt=4 + 4)
iir_p = servo.IIRWidths(state=25, coeff=18, adc=16, asf=16, word=16,
                accu=48, shift=11, channel=3, profile=1)
dac_p = servo.DACParams(data_width = 24, clk_width = 2,
                channels=adc_p.channels)
pgia_p = servo.PGIAParams(data_width = 16, clk_width = 2)

# initial values of PGIAs' gains - for every amplifier there are two bits of inromation; all of them 
# are concatenated into 16-bits-wide vector
pgia_init_val = 0x0000


# creating an instance of Servo class
m = servo.Servo(adc_pads, pgia_pads, dac_pads, adc_p, pgia_p, iir_p, dac_p,
            pgia_init_val, Kps, Kis)

m.submodules += adc_pads, pgia_pads, dac_pads

# the Servo's tie pin is tied to the high value
m.comb += m.start.eq(1)

# requesting for the clock signal available on the target board
clk_signal = Signal()
clk125 = plat.request("clk125_gtp")

m.specials += [
    Instance("IBUFDS_GTE2", i_I = clk125.p, i_IB = clk125.n, o_O = clk_signal),
    Instance("BUFG", i_I = clk_signal, o_O = m.cd_sys.clk)
]

# begin desing building and place it in the directory 'dir'
plat.build(m, run=True, build_dir = "building/{}ch/pgia{}/Kp_{}_Ki_{}".format(channels_no, pgia_init_val, Kps[0], Kis[0]), build_name = "top")
