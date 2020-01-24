from migen import *
from migen.build.platforms.sinara import kasli

from artiq.gateware.szservo import servo
from artiq.gateware.szservo.pads import ZotinoPads, SamplerPads, pgiaPads
from .eem2 import *

# number of channels used for control
channels_no = 2

# lists of PI controller's coefficients in S-plane domain;
# Kps = [i+1 for i in range(channels_no)]
Kps = [4, 0]
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
pgia_pads = pgiaPads(plat, pgia_eem)
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

m.comb += m.start.eq(1)
m.comb += [
    [plat.request("user_led").eq(i) for i in [m.dac.initialized, m.pgia.initialized, m.iir.done_writing]]
]


clk_signal = Signal()
clk125 = plat.request("clk125_gtp")

m.specials += [
    Instance("IBUFDS_GTE2", i_I = clk125.p, i_IB = clk125.n, o_O = clk_signal),
    Instance("BUFG", i_I = clk_signal, o_O = m.cd_sys.clk)
]

plat.add_platform_command("create_debug_core u_ila_0 ila\n\
set_property C_CLK_INPUT_FREQ_HZ 113281000 [get_debug_cores dbg_hub]\n\
set_property C_DATA_DEPTH 4096 [get_debug_cores u_ila_0]\n\
set_property C_TRIGIN_EN false [get_debug_cores u_ila_0]\n\
set_property C_TRIGOUT_EN false [get_debug_cores u_ila_0]\n\
set_property C_ADV_TRIGGER false [get_debug_cores u_ila_0]\n\
set_property C_INPUT_PIPE_STAGES 0 [get_debug_cores u_ila_0]\n\
set_property C_EN_STRG_QUAL false [get_debug_cores u_ila_0]\n\
set_property ALL_PROBE_SAME_MU true [get_debug_cores u_ila_0]\n\
set_property ALL_PROBE_SAME_MU_CNT 1 [get_debug_cores u_ila_0]\n\
startgroup \n\
set_property C_EN_STRG_QUAL true [get_debug_cores u_ila_0 ]\n\
set_property C_ADV_TRIGGER true [get_debug_cores u_ila_0 ]\n\
set_property ALL_PROBE_SAME_MU true [get_debug_cores u_ila_0 ]\n\
set_property ALL_PROBE_SAME_MU_CNT 4 [get_debug_cores u_ila_0 ]\n\
endgroup\n\
set_property port_width 1 [get_debug_ports u_ila_0/clk]\n\
connect_debug_port u_ila_0/clk [get_nets [list sys_clk ]]\n\
set_property port_width 16 [get_debug_ports u_ila_0/probe0]\n\
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe0]\n\
connect_debug_port u_ila_0/probe0 [get_nets [list {{data_dac_0[0]}} {{data_dac_0[1]}} {{data_dac_0[2]}} {{data_dac_0[3]}} {{data_dac_0[4]}} {{data_dac_0[5]}} {{data_dac_0[6]}} {{data_dac_0[7]}} {{data_dac_0[8]}} {{data_dac_0[9]}} {{data_dac_0[10]}} {{data_dac_0[11]}} {{data_dac_0[12]}} {{data_dac_0[13]}} {{data_dac_0[14]}} {{data_dac_0[15]}} ]]\n\
create_debug_port u_ila_0 probe\n\
set_property port_width 16 [get_debug_ports u_ila_0/probe1]\n\
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe1]\n\
connect_debug_port u_ila_0/probe1 [get_nets [list {{data_dac_1[0]}} {{data_dac_1[1]}} {{data_dac_1[2]}} {{data_dac_1[3]}} {{data_dac_1[4]}} {{data_dac_1[5]}} {{data_dac_1[6]}} {{data_dac_1[7]}} {{data_dac_1[8]}} {{data_dac_1[9]}} {{data_dac_1[10]}} {{data_dac_1[11]}} {{data_dac_1[12]}} {{data_dac_1[13]}} {{data_dac_1[14]}} {{data_dac_1[15]}} ]]\n\
create_debug_port u_ila_0 probe\n\
set_property port_width 18 [get_debug_ports u_ila_0/probe2]\n\
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe2]\n\
connect_debug_port u_ila_0/probe2 [get_nets [list {{iir_coef[0]}} {{iir_coef[1]}} {{iir_coef[2]}} {{iir_coef[3]}} {{iir_coef[4]}} {{iir_coef[5]}} {{iir_coef[6]}} {{iir_coef[7]}} {{iir_coef[8]}} {{iir_coef[9]}} {{iir_coef[10]}} {{iir_coef[11]}} {{iir_coef[12]}} {{iir_coef[13]}} {{iir_coef[14]}} {{iir_coef[15]}} {{iir_coef[16]}} {{iir_coef[17]}} ]]\n\
create_debug_port u_ila_0 probe\n\
set_property port_width 25 [get_debug_ports u_ila_0/probe3]\n\
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe3]\n\
connect_debug_port u_ila_0/probe3 [get_nets [list {{iir_out[0]}} {{iir_out[1]}} {{iir_out[2]}} {{iir_out[3]}} {{iir_out[4]}} {{iir_out[5]}} {{iir_out[6]}} {{iir_out[7]}} {{iir_out[8]}} {{iir_out[9]}} {{iir_out[10]}} {{iir_out[11]}} {{iir_out[12]}} {{iir_out[13]}} {{iir_out[14]}} {{iir_out[15]}} {{iir_out[16]}} {{iir_out[17]}} {{iir_out[18]}} {{iir_out[19]}} {{iir_out[20]}} {{iir_out[21]}} {{iir_out[22]}} {{iir_out[23]}} {{iir_out[24]}}  ]]\n\
create_debug_port u_ila_0 probe\n\
set_property port_width 1 [get_debug_ports u_ila_0/probe4]\n\
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe4]\n\
connect_debug_port u_ila_0/probe4 [get_nets [list iir_clip]]\n\
create_debug_port u_ila_0 probe\n\
set_property port_width 48 [get_debug_ports u_ila_0/probe5]\n\
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe5]\n\
connect_debug_port u_ila_0/probe5 [get_nets [list {{iir_p[0]}} {{iir_p[1]}} {{iir_p[2]}} {{iir_p[3]}} {{iir_p[4]}} {{iir_p[5]}} {{iir_p[6]}} {{iir_p[7]}} {{iir_p[8]}} {{iir_p[9]}} {{iir_p[10]}} {{iir_p[11]}} {{iir_p[12]}} {{iir_p[13]}} {{iir_p[14]}} {{iir_p[15]}} {{iir_p[16]}} {{iir_p[17]}} {{iir_p[18]}} {{iir_p[19]}} {{iir_p[20]}} {{iir_p[21]}} {{iir_p[22]}} {{iir_p[23]}} {{iir_p[24]}} {{iir_p[25]}} {{iir_p[26]}} {{iir_p[27]}} {{iir_p[28]}} {{iir_p[29]}} {{iir_p[30]}} {{iir_p[31]}} {{iir_p[32]}} {{iir_p[33]}} {{iir_p[34]}} {{iir_p[35]}} {{iir_p[36]}} {{iir_p[37]}} {{iir_p[38]}} {{iir_p[39]}} {{iir_p[40]}} {{iir_p[41]}} {{iir_p[42]}} {{iir_p[43]}} {{iir_p[44]}} {{iir_p[45]}} {{iir_p[46]}} {{iir_p[47]}}]]\n\
create_debug_port u_ila_0 probe\n\
set_property port_width 25 [get_debug_ports u_ila_0/probe6]\n\
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe6]\n\
connect_debug_port u_ila_0/probe6 [get_nets [list {{iir_a[0]}} {{iir_a[1]}} {{iir_a[2]}} {{iir_a[3]}} {{iir_a[4]}} {{iir_a[5]}} {{iir_a[6]}} {{iir_a[7]}} {{iir_a[8]}} {{iir_a[9]}} {{iir_a[10]}} {{iir_a[11]}} {{iir_a[12]}} {{iir_a[13]}} {{iir_a[14]}} {{iir_a[15]}} {{iir_a[16]}} {{iir_a[17]}} {{iir_a[18]}} {{iir_a[19]}} {{iir_a[20]}} {{iir_a[21]}} {{iir_a[22]}} {{iir_a[23]}} {{iir_a[24]}}]]\n\
create_debug_port u_ila_0 probe\n\
set_property port_width 16 [get_debug_ports u_ila_0/probe7]\n\
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe7]\n\
connect_debug_port u_ila_0/probe7 [get_nets [list {{adc1[0]}} {{adc1[1]}} {{adc1[2]}} {{adc1[3]}} {{adc1[4]}} {{adc1[5]}} {{adc1[6]}} {{adc1[7]}} {{adc1[8]}} {{adc1[9]}} {{adc1[10]}} {{adc1[11]}} {{adc1[12]}} {{adc1[13]}} {{adc1[14]}} {{adc1[15]}} ]]\n\
create_debug_port u_ila_0 probe\n\
set_property port_width 16 [get_debug_ports u_ila_0/probe8]\n\
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe8]\n\
connect_debug_port u_ila_0/probe8 [get_nets [list {{adc0[0]}} {{adc0[1]}} {{adc0[2]}} {{adc0[3]}} {{adc0[4]}} {{adc0[5]}} {{adc0[6]}} {{adc0[7]}} {{adc0[8]}} {{adc0[9]}} {{adc0[10]}} {{adc0[11]}} {{adc0[12]}} {{adc0[13]}} {{adc0[14]}} {{adc0[15]}} ]]\n\
create_debug_port u_ila_0 probe\n\
set_property port_width 16 [get_debug_ports u_ila_0/probe9]\n\
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe9]\n\
connect_debug_port u_ila_0/probe9 [get_nets [list {{profile0[48]}} {{profile0[49]}} {{profile0[50]}} {{profile0[51]}} {{profile0[52]}} {{profile0[53]}} {{profile0[54]}} {{profile0[55]}} {{profile0[56]}} {{profile0[57]}} {{profile0[58]}} {{profile0[59]}} {{profile0[60]}} {{profile0[61]}} {{profile0[62]}} {{profile0[63]}} ]]\n\
create_debug_port u_ila_0 probe\n\
set_property port_width 16 [get_debug_ports u_ila_0/probe10]\n\
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe10]\n\
connect_debug_port u_ila_0/probe10 [get_nets [list {{profile1[48]}} {{profile1[49]}} {{profile1[50]}} {{profile1[51]}} {{profile1[52]}} {{profile1[53]}} {{profile1[54]}} {{profile1[55]}} {{profile1[56]}} {{profile1[57]}} {{profile1[58]}} {{profile1[59]}} {{profile1[60]}} {{profile1[61]}} {{profile1[62]}} {{profile1[63]}} ]]")





plat.build(m, run=True, build_dir = "building/pid/debugging/{}ch/pgia{:0>4x}".format(channels_no, pgia_init_val), build_name = "top")
