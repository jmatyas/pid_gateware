from migen import *

from artiq.gateware.szservo.spi import SPI, SPIParams

class TB(Module):
    def __init__(self, params):
        self.sclk = Signal()
        self.sdi = Signal()

        self.syncr = Signal(reset=1)
        self.ldac = Signal(reset = 1)
        self.busy = Signal(reset = 1)

        clk0 = Signal()
        self.sync += clk0.eq(self.sclk)
        sample = Signal()
        self.comb += sample.eq(Cat(self.sclk, clk0) == 0b01)


def main():
    params = SPIParams(channels=2, data_width = 8, 
        clk_width = 2)
    tb = TB(params)
    spi = SPI(tb, params)

    tb.submodules += spi

    def run(tb):
        dut = spi
        yield dut.start.eq(1)
        yield dut.dataSPI.eq(0xA9A942AB)
        yield
        yield dut.start.eq(0)
        # yield dut.data.eq(0)
        for ch in range (params.channels):
            for i in range (params.data_width*2*params.clk_width-1):
                yield
            yield
            yield dut.busy.eq(0)
            for i in range(3):
                yield
            yield dut.busy.eq(1)
            yield
        # for i in range (params.data_width*2*params.clk_width-1):
        #     yield
        # yield
        # yield dut.busy.eq(0)
        # for i in range(3):
        #     yield
        # yield
        # yield dut.busy.eq(1)
        while not (yield dut.ready):
            yield
        yield
        
    run_simulation(tb, run(tb), vcd_name= "spi.vcd")

if __name__ == "__main__":
    main()