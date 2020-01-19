import logging
import unittest

from migen import *

from artiq.gateware.szservo.dac_ser2 import DAC, DACParams
from artiq.language.units import us, ns


start_delay = 5
dac_p = DACParams(channels=8, data_width = 24, 
    clk_width = 2)

t_cycle =  (dac_p.data_width*2*dac_p.clk_width + 3 + 1 + 2)*dac_p.channels + 1


class TB(Module):
    def __init__(self, dac_p):
        self.sdi = Signal()
        self.sclk = Signal()

        self.ldac = Signal(reset = 1)
        # self.busy = Signal(reset = 1)
        self.syncr = Signal(reset = 1)
        self.clr = Signal()



class DACSim(DAC):
    def __init__(self):
    
        self.submodules.dac_tb = TB(dac_p)
    
        self.submodules.dac = DAC(self.dac_tb, dac_p)

        cnt_done = Signal()
        cnt = Signal(max=t_cycle + 1)
        load_cnt = Signal()

        assert start_delay <= 50 - 3
        start_cnt = Signal(max=50 + 1, reset = start_delay + 3)
        start_done = Signal()

        self.comb += [
             cnt_done.eq(cnt == 0), 

             start_done.eq((start_cnt == 2) | (start_cnt == 1) | (start_cnt == 0))
        ]

        self.sync += [
            If(start_done,
                If(cnt_done,
                    If(load_cnt,
                        cnt.eq(t_cycle - 1)
                    )
                ).Else(
                    cnt.eq(cnt - 1)
                ),
            ).Else(
                start_cnt.eq(start_cnt - 1)
            ) 
        ]

        self.comb += [
            self.dac.dac_init.eq(~self.dac.initialized & ((cnt == 1) | (cnt_done)) & start_done),
            self.dac.dac_start.eq(self.dac.initialized & (cnt_done | (cnt == 1))),
            load_cnt.eq(self.dac.dac_start),
        ]

    def test(self):
        dut = self.dac
        prof0 =0x90CB000000008FF1
        prof1 = 0xA011000000008FF1
        

        for i in range (dac_p.channels):
            yield dut.profile[i].eq(prof0 + 0x2000000000000000*i)

        for i in range(start_delay + 3):
            yield

        while not (yield dut.initialized):
            yield
        yield
        yield
        yield
        while not (yield dut.dac_ready):
            yield
        yield

        for i in range(100):
            yield        

def main():
    dac = DACSim()
    run_simulation(dac, dac.test(), vcd_name = "dac_next.vcd")

    
if __name__ == "__main__":
    print(t_cycle)
    print(t_cycle*8*ns)

    print((t_cycle - 1)/dac_p.channels)
    print(((t_cycle - 1)/dac_p.channels)*8*ns)    

    logging.basicConfig(level=logging.DEBUG)
    main()