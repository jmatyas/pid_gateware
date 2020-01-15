from migen import *

bit_len = 8

class RW_Mem(Module):
    def __init__(self, addrs, values, words, masks):

        self.start = Signal()

        self.reading = Signal()
        self.writing = Signal()
        self.calculating = Signal()
        self.done_writing = Signal()

        val = Array(Signal(2*bit_len) for i in range(len(addrs)))

        coeff_no = Signal(max=len(addrs))


        self.specials.mem = Memory(width=2*bit_len, depth=10)# << iir_p.profile + iir_p.channel)

        mem = self.mem.get_port(write_capable = True, async_read = True)

        self.specials += mem
        self.submodules.fsm = fsm = FSM("IDLE")

        fsm.act("IDLE",
            # self.done.eq(1),
            If(self.start,
                If(~self.done_writing,
                    NextState("READ"), 
                )
            )
        )
        fsm.act("READ",
            self.reading.eq(1),
            NextState("CALCULATE"),
        )
        fsm.act("CALCULATE",
            self.calculating.eq(1),
            NextState("WRITE"),
        )
        fsm.act("WRITE",
            self.writing.eq(1),
            mem.we.eq(1),
            If((coeff_no == len(addrs) - 1),
                NextState("IDLE"),
            ).Else(
                NextState("READ")
            )
        )

        self.comb += [
            If(self.reading, 
                mem.adr.eq(addrs[coeff_no])
            ).Elif(self.writing,
                mem.adr.eq(addrs[coeff_no]),
                mem.dat_w.eq(val[coeff_no])
            ),
        ]

        self.sync += [
            If(self.reading,
                val[coeff_no].eq(mem.dat_r)
            ),
            If(~self.writing,
                mem.we.eq(0)
            ),
            If(self.calculating,
                If(words[coeff_no],
                    val[coeff_no].eq((val[coeff_no] & masks[coeff_no]) | ((values[coeff_no] & masks[coeff_no]) << bit_len))
                ).Else(
                    val[coeff_no].eq((values[coeff_no] & masks[coeff_no]) | (val[coeff_no] & (masks[coeff_no] << bit_len)))
                )
            ),
            If(fsm.ongoing("WRITE"),
                If( not (coeff_no == len(addrs) - 1),
                    coeff_no.eq(coeff_no+1)
                ).Else(
                    coeff_no.eq(0),
                ),
                If(coeff_no == len(addrs) - 1,
                    self.done_writing.eq(1)
                )
            ),
        ]


    
    
    def test(self):
        yield self.mem[0].eq(0x1BAB)
        yield self.mem[5].eq(0xAA09)
        yield self.mem[7].eq(0x00CF)
        yield self.mem[1].eq(0xEFDC)
        yield self.mem[1].eq(0xA00A)
        yield self.mem[2].eq(0x0980)

        # for i in range (1,4):
        #     yield self.mem[i].eq(i**3+3)

        for i in range(100):
            yield

if __name__ == "__main__":
    
    channel = 0
    profile = 0
    
    length = 8
    addrs = Array(Signal(max = 10) for i in range(length))
    values = Array(Signal(bit_len) for i in range(length))
    words = Array(Signal() for i in range(length))
    masks = Array(Signal(bit_len) for i in range (length))

    # a1, b0, b1 = coeff_to_mu(Kp = 1, Ki = 0)

    m = RW_Mem(addrs, values, words, masks)

    m.comb += [
        addrs[0].eq(0),      # ftw1
        addrs[1].eq(0),      # b1
        addrs[2].eq(5),      # pow
        addrs[3].eq(5),      # cfg
        addrs[4].eq(7),      # offset
        addrs[5].eq(7),      # a1
        addrs[6].eq(1),      # ftw0
        addrs[7].eq(1),      # b0

        values[0].eq(0x5A),
        values[1].eq(10),
        values[2].eq(0xF),
        values[3].eq(0xAB),
        values[4].eq(5),
        values[5].eq(10),
        values[6].eq(0xF),
        values[7].eq(0xAB),

        words[0].eq(0),
        words[1].eq(1),
        words[2].eq(0),
        words[3].eq(1),
        words[4].eq(0),
        words[5].eq(1),
        words[6].eq(0),
        words[7].eq(1),
    
    ]


    for i in range(length):
        m.comb += masks[i].eq(0xFF)

    # coeff = dict(pow=0x0000, offset=0x0000, ftw0=0x1727, ftw1=0x1929,
    #     a1=a1, b0=b0, b1=b1, cfg=0 | (0 << 3))


    # for ks in "pow offset ftw0 ftw1", "a1 b0 b1 cfg":
    #     for k in ks.split():
    #         # self.set_coeff(self.channel, value=coeff[k],
    #         #     profile=self.profile, coeff=k)

    # for i in range(4):
    #     m.comb += addrs[i].eq(i), masks[i].eq(0xFFFF), words[i].eq(i//2)    
    
    m.comb += m.start.eq(1)
    run_simulation(m, m.test(), vcd_name="test.vcd")

    # for ks in "pow offset ftw0 ftw1", "a1 b0 b1 cfg":
    # for k in ks.split():
    #     self.set_coeff(self.channel, value=coeff[k],
    #             profile=self.profile, coeff=k)
