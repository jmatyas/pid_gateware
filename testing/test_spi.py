from migen import *
import unittest

from artiq.gateware.szservo.spi import SPI, SPIParams


AD53XX_CMD_OFFSET = 2 << 22
AD53XX_SPECIAL_OFS0 = 2 << 16

t_busy = 188    # 188 * 8ns = 1.5us; 8 ns when sys_clk=125MHz


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
        self.spi_p = spi_p = SPIParams(channels=4, data_width = 24, 
            clk_width = 2)
        
        self.submodules.spi_tb = TB(spi_p)
        
        self.begin = Signal()
        self.done = Signal()

        self.submodules.spi = SPI(self.spi_tb, spi_p)

        self.input1 = Signal(spi_p.data_width)
        self.input2 = Signal(spi_p.data_width)

        self.comb+= [
            If(self.spi.init_latch,
                self.spi_tb.ldac.eq(1), self.spi_tb.clr.eq(1),
                self.spi.dataSPI.eq(self.input1)
            ).Else(
                self.spi_tb.ldac.eq(0), self.spi_tb.clr.eq(1),
                self.spi.dataSPI.eq(self.input2)
            )
        ]

        self.comb += [
            self.spi.init.eq(~self.spi.initialized & self.begin),
            self.spi.spi_start.eq(self.begin & self.spi.spi_ready),
            self.done.eq(self.spi.spi_ready)
        ]
    
    def test(self):
        dut = self.spi

        yield self.input1.eq(0x9)
        yield self.input2.eq(0xA)
        yield
        yield
        yield self.input1.eq(AD53XX_CMD_OFFSET | AD53XX_SPECIAL_OFS0 | 0x2000) #(0x822000)
        yield self.begin.eq(1)
        data = 0xEACB000000008FF1
        yield self.input2.eq(data)      # data to assign for the next SPI iteration - it's gonna be latched in SPI module when it's ready

        yield from self.busy(data)
        
        for i in range(self.spi_p.channels):
            yield self.input2.eq(data + i + 1)      # data to assign for the next SPI iteration - it's gonna be latched in SPI module when it's ready
            yield from self.busy(data)
            if i == 2:
                yield self.begin.eq(0)

        while not (yield self.done):
           yield

        for i in range(60):
            yield
   

    def busy(self, data):
        dut = self.spi

        clk_cycles = 0
        while (yield self.spi_tb.syncr):
                yield        
        
        while not (yield self.spi_tb.syncr):
            yield
            clk_cycles +=1

        assert clk_cycles -1 == self.spi_p.data_width*2*self.spi_p.clk_width - 1
        
        # max waiting time between sync rising and busy falling is 42 ns ~ 5 cycles
        for i in range (5):
            yield
        yield dut.busy.eq(0)
        for i in range(t_busy):
            yield
        yield dut.busy.eq(1)

        while not (yield dut.spi_ready):
            yield       

def main():
    spi = SPISim()
    run_simulation(spi, spi.test(), vcd_name="spi.vcd")


class SPITest(unittest.TestCase):
    def test_run(self):
        main()
    
    
if __name__ == "__main__":
    main()