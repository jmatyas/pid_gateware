from migen import *
import unittest

from artiq.gateware.szservo.spi import SPI, SPIParams


AD53XX_CMD_OFFSET = 2 << 22
AD53XX_SPECIAL_OFS0 = 2 << 16


class TB(Module):
    def __init__(self, params):
        self.sclk = Signal()
        self.sdi = Signal()

        self.syncr = Signal(reset=1)
        self.ldac = Signal(reset = 1)
        self.busy = Signal(reset = 1)
        self.clr = Signal(reset=1)

class SPISim(SPI):
    def __init__(self):
        self.spi_p = spi_p = SPIParams(channels=4, data_width = 4, 
            clk_width = 2)
        
        self.submodules.spi_tb = TB(spi_p)
        
        self.begin = Signal()
        self.done = Signal()

        self.submodules.spi = SPI(self.spi_tb, spi_p)

        self.input1 = Signal(spi_p.data_width)
        self.input2 = Signal(spi_p.data_width)
        self.input3 = Signal(spi_p.data_width)

        t_cycle = spi_p.channels*spi_p.data_width*spi_p.clk_width*2
        cnt_done = Signal()
        cnt = Signal(max = t_cycle)

        self.sync += [
            If(~cnt_done,
                cnt.eq(cnt - 1)
            ).Else(
                cnt.eq(t_cycle - 1)
            )
        ]

        self.comb+= [
            If(self.spi.init_latch,
                self.spi_tb.ldac.eq(1), self.spi_tb.clr.eq(1),
                self.spi.dataSPI.eq(self.input1)
            ).Else(
                self.spi_tb.ldac.eq(0), self.spi_tb.clr.eq(1),
                self.spi.dataSPI.eq(self.input2 << spi_p.data_width | self.input3)
            )
        ]

        self.comb += [
            cnt_done.eq(cnt == 0),
            self.spi.init.eq(~self.spi.initialized & self.begin),
            self.spi.start.eq(self.begin),
            self.done.eq(self.spi.ready & self.spi.initialized)
        ]
    
    def test(self):
        yield
        yield
        yield self.input1.eq(0xE)
        yield self.input2.eq(0xA)
        # yield self.input1.eq(AD53XX_CMD_OFFSET | AD53XX_SPECIAL_OFS0 | 0x2000) #(0x822000)
        # yield self.input2.eq(0xEACB000000008FF1)
        yield self.begin.eq(1)
        yield
        yield self.input2.eq(0xC)
        yield self.input3.eq(0x2)
        yield from self.busy_init()
        yield from self.busy()
        yield self.begin.eq(1)
        yield self.input2.eq(0xA)
        yield self.input3.eq(0xF)
        yield from self.busy()
        while not (yield self.done):
            yield     
        yield


        # yield self.input2.eq(0xCE)
        # yield self.input3.eq(0x07)
        # yield from self.busy_init()
        # yield from self.busy()
        # while not (yield self.done):
        #     yield     

        # self.input1.eq(AD53XX_CMD_OFFSET | AD53XX_SPECIAL_OFS0 | 0x2000)
        # yield from self.init_spi()
        # yield from self.send()

    def busy(self):
        dut = self.spi

        yield
        yield self.begin.eq(0)
        for ch in range (self.spi_p.channels):
            for i in range (self.spi_p.data_width*2*self.spi_p.clk_width-1):
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

    def busy_init(self):
        dut = self.spi
        
        yield
        # yield self.begin.eq(0)
        for i in range (self.spi_p.data_width*2*self.spi_p.clk_width-1):
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

    def init_spi(self):
        dut = self.spi
        assert (yield dut.ready)

        yield dut.init.eq(1)
        yield dut.start.eq(1)
        # yield dut.dataSPI.eq(0xA0)
        yield
        while (yield dut.ready):
            yield
        yield dut.start.eq(0)
        # yield dut.init.eq(0)
        # for ch in range (self.spi_pp.channels):
        for i in range (self.spi_p.data_width*2*self.spi_p.clk_width-1):
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
    
    def send(self):
        dut = self.spi
        assert (yield dut.ready)

        yield dut.init.eq(0)
        yield dut.start.eq(1)
        yield
        while (yield dut.ready):
            yield
        yield dut.start.eq(0)
        # yield dut.init.eq(0)
        for ch in range (self.spi_p.channels):
            for i in range (self.spi_p.data_width*2*self.spi_p.clk_width-1):
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


def main():
    spi = SPISim()
    run_simulation(spi, spi.test(), vcd_name="spi.vcd")


class SPITest(unittest.TestCase):
    def test_run(self):
        main()
    
    
if __name__ == "__main__":
    main()