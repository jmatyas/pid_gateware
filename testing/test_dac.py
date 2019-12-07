import logging
import unittest

from migen import *

from artiq.gateware.szservo.dac_ser import DAC, DACParams

class TB(Module):
    def __init__(self, params):
        self.sdi = Signal()
        self.ldac = Signal(reset = 1)
        self.busy = Signal(reset = 1)
        self.syncr = Signal(reset = 1)
        self.sclk = Signal()

        clk0 = Signal()
        self.sync += clk0.eq(self.sclk)
        sample = Signal()
        self.comb += sample.eq(Cat(self.sclk, clk0) == 0b01)

        # sr = Signal(len(self.dac))
        # self.sync += [
        #     If(~self.syncr & sample,
        #         sr.eq(Cat(self.sdi, sr))
        #     )
        # ]

    @passive
    def log(self, data):
        while True:
            v = yield from [(yield getattr(self.dac, k))
                    for k in "data address mode".split()]
            data.append(v)
    
def main():
    params = DACParams(channels=2, data_width = 24, 
        clk_width = 2)
    tb = TB(params)
    dac = DAC(tb, params)
    tb.submodules += dac

    def run(tb):
        dut = dac
        prof0 =0xEACB000000008FF1
        yield dut.profile[0].eq(prof0)
        for i in range (params.channels):
            yield dut.profile[i].eq(prof0 + 0x9000000000000000*i)
        yield dut.start.eq(1)
        yield
        yield dut.start.eq(0)
        for ch in range (params.channels):
            for i in range (params.data_width*2*params.clk_width-1):
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
        # prof0 =0xAB
        # yield dut.profile[0].eq(prof0)
        # for i in range (1, params.channels):
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