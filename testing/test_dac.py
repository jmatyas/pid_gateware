import logging
import unittest

from migen import *

from artiq.gateware.szservo.dac_ser import DAC, DACParams

class TB(Module):
    def __init__(self):
        self.sdi = Signal()
        self.ldac = Signal(reset = 1)
        self.busy = Signal(reset = 1)
        self.syncr = Signal(reset = 1)
        self.sclk = Signal()

        clk0 = Signal()
        self.sync += clk0.eq(self.sclk)
        sample = Signal()
        self.comb += sample.eq(Cat(self.sclk, clk0) == 0b01)

        self.dac = Record([("data", 16), ("address", 6), ("mode", 2)])

        sr = Signal(len(self.dac))
        self.sync += [
            If(~self.syncr & sample,
                sr.eq(Cat(self.sdi, sr))
            )
        ]

    @passive
    def log(self, data):
        while True:
            v = yield from [(yield getattr(self.dac, k))
                    for k in "data address mode".split()]
            data.append(v)
    
def main():
    tb = TB()
    dac = DAC(tb, 0)
    tb.submodules += dac

    def run(tb):
        dut = dac
        yield dut.profile[0].eq(0xDADA00000000AAAD)
        yield
        yield dut.dav.eq(1)
        yield dut.start.eq(1)
        yield
        yield
        yield dut.start.eq(0)
        yield dut.dav.eq(0)
        yield dut.data.eq(0x0000)
        yield
        yield
        assert not (yield dut.ready)
        # for i in range (10):
        #     yield
        while not (yield dut.ready):
            yield
        yield

    data = []
    run_simulation(tb, run(tb), vcd_name = "dac.vcd")

class DACTest(unittest.TestCase):
    def test_run(self):
        main()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()