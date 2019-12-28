import logging
import unittest

from migen import *

from artiq.gateware.szservo.dac_ser import DAC, DACParams

class TB(Module):
    def __init__(self, dac_p):
        self.sdi = Signal()
        self.sclk = Signal()

        self.ldac = Signal(reset = 1)
        self.busy = Signal(reset = 1)
        self.syncr = Signal(reset = 1)
        self.clr = Signal()

        clk0 = Signal()
        self.sync += clk0.eq(self.sclk)
        sample = Signal()
        self.comb += sample.eq(Cat(self.sclk, clk0) == 0b10)

        self.dacs = []
        for i in range(dac_p.channels):
            dac = Record([("mode", 2), ("address", 6), ("data", 16)])
            sr = Signal(len(dac))
            self.sync += [
                    If(~self.clr & sample,
                        sr.eq(Cat(self.sdi, sr))
                    ),
                    If(self.syncr,
                        dac.raw_bits().eq(sr)
                    )
            ]
            self.dacs.append(dac)


def main():
    dac_p = DACParams(channels=4, data_width = 4, 
        clk_width = 2)
    tb = TB(dac_p)
    dac = DAC(tb, dac_p)
    tb.submodules += dac


    def busy(dut):

        yield
        yield dut.start.eq(0)
        for ch in range (dac_p.channels):
            for i in range (dac_p.data_width*2*dac_p.clk_width-1):
                yield
            yield
            yield dut.busy.eq(0)
            for i in range(3):
                yield
            yield dut.busy.eq(1)
            yield
        while not (yield dut.ready):
            yield     
        yield
    
    def init_spi(dut):
        assert (yield dut.ready)

        yield dut.init.eq(1)
        yield dut.start.eq(1)
        yield
        while (yield dut.ready):
            yield
        yield dut.start.eq(0)
        yield dut.init.eq(0)
        for i in range (dac_p.data_width*2*dac_p.clk_width-1):
            yield
        yield
        yield dut.busy.eq(0)
        for i in range(3):
            yield
        yield dut.busy.eq(1)
        yield
        while not (yield dut.ready):
            yield        
        yield
    

    
    def run(tb):
        dut = dac
        prof0 =0xEACB000000008FF1
        profiles = list()

        for i in range (dac_p.channels):
            profiles.append(prof0 + 0x9000000000000000*i)
            yield dut.profile[i].eq(prof0 + 0x9000000000000000*i)


        yield
        yield from init_spi(dut)
        yield dut.start.eq(1)
        yield from busy(dut)
       
        # yield from test_channels(dut)
        # prof0 =0xEACB000000008FF1
        # yield dut.init.eq(1)
        # yield dut.profile[0].eq(prof0)
        # for i in range (dac_p.channels):
        #     yield dut.profile[i].eq(prof0 + 0x9000000000000000*i)
        # yield dut.start.eq(1)
        # yield
        # yield dut.start.eq(0)
        # while (yield dut.ready):
        #     yield
        # yield dut.init.eq(0)
        # for ch in range (dac_p.channels):
        #     for i in range (dac_p.data_width*2*dac_p.clk_width-1):
        #         yield
        #     yield
        #     yield dut.busy.eq(0)
        #     for i in range(3):
        #         yield
        #     yield dut.busy.eq(1)
        #     yield
        # while not (yield dut.ready):
        #     yield
        # yield
        # prof0 =0xAB
        # yield dut.profile[0].eq(prof0)
        # for i in range (1, dac_p.channels):
        #     yield dut.profile[i].eq(prof0 + 0x01*i)
        # yield
        # yield dut.start.eq(1)
        # yield
        # yield
        # yield dut.start.eq(0)
        # yield dut.profile[0].eq(0x0000)
        # yield
        # yield
        # assert not (yield dut.ready)
        # # for i in range (10):
        # #     yield
        # while not (yield dut.ready):
        #     yield
        # yield
        # while not (yield dut.ready):
        #     yield
        # yield

    # data = []
    run_simulation(tb, run(tb), vcd_name = "dac.vcd")

    

class DACTest(unittest.TestCase):
    def test_run(self):
        main()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()