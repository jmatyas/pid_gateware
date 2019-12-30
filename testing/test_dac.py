import logging
import unittest

from migen import *

from artiq.gateware.szservo.dac_ser import DAC, DACParams

t_busy = 188    # 188 * 8ns = 1.5us; 8 ns when sys_clk=125MHz

class TB(Module):
    def __init__(self, dac_p):
        self.sdi = Signal()
        self.sclk = Signal()

        self.ldac = Signal(reset = 1)
        self.busy = Signal(reset = 1)
        self.syncr = Signal(reset = 1)
        self.clr = Signal()

        self.tb_begin = Signal()
        self.tb_done = Signal()



def main():
    dac_p = DACParams(channels=6, data_width = 24, 
        clk_width = 2)
    ch_no = None
    tb = TB(dac_p)
    dac = DAC(tb, dac_p, ch_no)
    tb.submodules += dac


    tb.comb += [
            dac.init.eq(~dac.initialized & tb.tb_begin),
            # dac.start_dac.eq(tb.tb_begin & dac.initialized),
            tb.tb_done.eq(dac.ready)
        ]
    

    def busy(dut):
        
        # for ch in range (dac_p.channels):
        clk_cycles = 0
        while (yield tb.syncr):
                yield        
        
        while not (yield tb.syncr):
            yield
            clk_cycles +=1

        # assert clk_cycles -1 == dac_p.data_width*2*dac_p.clk_width - 1

        # max waiting time between sync rising and busy falling is 42 ns ~ 5 cycles
        for i in range (5):
            yield
        yield dut.busy.eq(0)
        for i in range(t_busy):
            yield
        yield dut.busy.eq(1)

        while not (yield dut.spi_ready):
            yield       

    def init_spi(dut):
        assert (yield dut.ready)

        clk_cycles = 0
        while (yield dut.ready):
            yield
        
        while not (yield tb.syncr):
            yield
            clk_cycles += 1

        # assert clk_cycles -1 == dac_p.data_width*2*dac_p.clk_width-1
        
        # max waiting time between sync rising and busy falling is 42 ns ~ 5 cycles
        for i in range(5):
            yield
        yield dut.busy.eq(0)
        for i in range(t_busy):
            yield
        yield dut.busy.eq(1)
        while not (yield dut.ready):
            yield        
    

    
    def run(tb):
        dut = dac
        prof0 =0x90CB000000008FF1
        prof1 = 0xA011000000008FF1
        
        for i in range (dac_p.channels):
            yield dut.profile[i].eq(prof0 + 0x2000000000000000*i)


        yield
        yield
        yield tb.tb_begin.eq(1)
        yield from init_spi(dut)

        yield
        yield
        yield
        yield dac.start_dac.eq(1)
        yield
        yield
        yield
        yield dac.start_dac.eq(0)
        # for i in range(dac_p.channels):
        while (yield tb.tb_done):
            yield
        while not (yield tb.tb_done):
            yield from busy(dut)
        assert (yield dut.ready)

        # # yield tb.tb_begin.eq(0)
        
        for i in range(100):
            yield
        assert (yield dut.ready)
        
        for i in range (dac_p.channels):
            yield dut.profile[i].eq(prof1 + 0x2000000000000000*i)
        
        yield tb.tb_begin.eq(1)
        yield
        yield
        yield dac.start_dac.eq(1)
        yield
        yield
        yield dac.start_dac.eq(0)
        yield 
        yield tb.tb_begin.eq(0)

        while not (yield tb.tb_done):
            yield from busy(dut)
        assert (yield dut.ready)

        for i in range(100):
            yield


              
       
    run_simulation(tb, run(tb), vcd_name = "dac.vcd")

    

class DACTest(unittest.TestCase):
    def test_run(self):
        main()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()