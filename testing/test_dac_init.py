from migen import *

from artiq.gateware.szservo.dac_ser import DAC_init, DACParams

class TB(Module):
    def __init__(self, p):
        self.sdi = Signal()
        self.ldac = Signal(reset = 1)
        self.busy = Signal(reset = 1)
        self.syncr = Signal(reset = 1)
        self.sclk = Signal()
        self.clr = Signal()

def main():
    p = DACParams(channels = 1, data_width = 24, clk_width = 2, init_seq = 1)
    tb = TB(p)
    dac_init = DAC_init(tb, p)
    tb.submodules += dac_init

    def run(tb):
        dut = dac_init
        yield dut.start.eq(1)
        yield
        yield dut.start.eq(0)
        for ch in range (p.channels):
            for i in range (p.data_width*2*p.clk_width-1):
                yield
            yield
            yield dut.busy.eq(0)
            for i in range(3):
                yield
            yield dut.busy.eq(1)
            yield
        while not (yield dut.initialized):
            yield
        yield
    
    run_simulation(tb, run(tb), vcd_name="dac_init.vcd")

if __name__ == "__main__":
    main()