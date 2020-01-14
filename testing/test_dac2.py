import logging
import unittest

from migen import *

from artiq.gateware.szservo.dac_ser2 import DAC, DACParams

t_busy = 188    # 188 * 8ns = 1.5us; 8 ns when sys_clk=125MHz

class TB(Module):
    def __init__(self, dac_p):
        self.sdi = Signal()
        self.sclk = Signal()

        self.ldac = Signal(reset = 1)
        # self.busy = Signal(reset = 1)
        self.syncr = Signal(reset = 1)
        # self.clr = Signal()



def main():
    dac_p = DACParams(channels=8, data_width = 24, 
        clk_width = 2)
    ch_no = None
    tb = TB(dac_p)
    dac = DAC(tb, dac_p)
    tb.submodules += dac

    # t_cycle =  (dac_p.data_width*2*dac_p.clk_width + 6)*2
    # else:
    t_cycle =  (dac_p.data_width*2*dac_p.clk_width + 6)*dac_p.channels + 1

    tb_cnt_done = Signal()
    tb_cnt = Signal(max=t_cycle + 1)
    load_cnt = Signal()

    tb.comb += tb_cnt_done.eq(tb_cnt == 0)
    tb.sync += [
        If(tb_cnt_done,
            If(load_cnt,
                tb_cnt.eq(t_cycle - 1)
            )
        ).Else(
            tb_cnt.eq(tb_cnt - 1)
        )
    ]

    tb.comb += [
            dac.dac_init.eq(~dac.initialized),
            dac.dac_start.eq(dac.initialized & (tb_cnt_done | (tb_cnt == t_cycle - 1))),#  | (tb_cnt == t_cycle - 2))),
            load_cnt.eq(dac.dac_start),
        ]
        



    def run(tb):
        dut = dac
        prof0 =0x90CB000000008FF1
        prof1 = 0xA011000000008FF1
        
        for i in range (dac_p.channels):
            yield dut.profile[i].eq(prof0 + 0x2000000000000000*i)


        # yield dac.dac_init.eq(1)
        yield
        yield
        # yield dac.dac_init.eq(0)
        while not (yield dac.initialized):
            yield
        yield
        # yield dac.dac_start.eq(1)
        yield
        yield
        # yield dac.dac_start.eq(0)
        while not (yield dac.dac_ready):
            yield
        yield
        for i in range(100):
            yield


              
       
    run_simulation(tb, run(tb), vcd_name = "dac_next.vcd")

    

class DACTest(unittest.TestCase):
    def test_run(self):
        main()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()