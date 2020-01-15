from migen import *

class Cos(Module):
    def __init__(self, addrs, values, words, masks):

        self.start = Signal()

        self.reading = Signal()
        self.writing = Signal()
        self.calculating = Signal()
        self.done_writing = Signal()

        val = Array(Signal(2*8) for i in range(4))

        cnt = Signal(max =len(addrs))
        cnt_done = Signal()
        cnt_load = Signal(max = len(addrs))

        no = Signal(max=len(addrs))


        self.specials.mem = Memory(width=2*8, depth=4)# << iir_p.profile + iir_p.channel)

        mem = self.mem.get_port(write_capable = True, async_read = True)

        self.specials += mem
        self.submodules.fsm = fsm = FSM("IDLE")

        fsm.act("IDLE",
            # self.done.eq(1),
            If(self.start,
                If(~self.done_writing,
                    NextState("READ"), 
                    cnt_load.eq(len(addrs) - 1),
                )
            )
        )

        fsm.act("READ",
            self.reading.eq(1),
            If(cnt_done,
                NextState("CALCULATE"),
                cnt_load.eq(len(addrs) - 1)
            )
        )

        fsm.act("CALCULATE",
            self.calculating.eq(1),
            If(cnt_done,
                NextState("WRITE"),
                cnt_load.eq(len(addrs) - 1),
            )
        )

        fsm.act("WRITE",
            self.writing.eq(1),
            mem.we.eq(1),
            If(cnt_done,
                NextState("IDLE")
            )
        )

        # self.sync += [
        #     # If(self.reading,
        #     #     val[no].eq(mem.dat_r)
        #     # ),
        #     # If(fsm.before_leaving("WRITE"),
        #     #     self.done_writing.eq(1)
        #     # )
        #     # If(self.writing,
        #     #     mem.dat_w.eq(val[no])
        #     # )
        # ]
        
        self.comb += [
            cnt_done.eq(cnt == 0),

            If(self.reading, 
                mem.adr.eq(addrs[no])
            ).Elif(self.writing,
                mem.adr.eq(addrs[no]),
                mem.dat_w.eq(val[no])
            ),
        ]

        self.sync += [
            If(cnt_done,
                If(cnt_load,
                    cnt.eq(cnt_load)
                )
            ).Else(
                cnt.eq(cnt - 1)
            ),
            If(self.reading,
                no.eq(no + 1),
                val[no].eq(mem.dat_r)
            ),
            If(self.calculating,
                no.eq(no+1)
            ),
            If(self.writing,
                no.eq(no+1),
            ).Else(
                mem.we.eq(0)
            ),
            If(self.calculating,
                If(words[no],
                    val[no].eq((val[no] & masks[no]) | ((values[no] & masks[no]) << 8))
                ).Else(
                    val[no].eq((values[no] & masks[no]) | (val[no] & (masks[no] << 8)))
                )
            ),
            If(fsm.before_leaving("WRITE"),
                self.done_writing.eq(1)
            )

        ]


    
    
    def test(self):
        yield self.mem[0].eq(0x50AB)
        yield self.mem[1].eq(0xAA09)
        yield self.mem[2].eq(0x00CF)
        yield self.mem[3].eq(0xEFDC)

        # for i in range (1,4):
        #     yield self.mem[i].eq(i**3+3)

        for i in range(100):
            yield

if __name__ == "__main__":
    # iir_p = iir_p = IIRWidths(state=25, coeff=18, adc=16, asf=14, word=16,
    #         accu=48, shift=11, channel=2, profile=1)

    # iir = IIR(iir_p)
    
    channel = 0
    profile = 0
    
    addrs = Array(Signal(max = 4) for i in range(4))
    values = Array(Signal(2*8) for i in range(4))
    words = Array(Signal() for i in range(4))
    masks = Array(Signal(8) for i in range (4))

    # a1, b0, b1 = coeff_to_mu(Kp = 1, Ki = 0)

    m = Cos(addrs, values, words, masks)

    # # m.comb += [
    # #     addr[0].eq(0),
    # #     addr[1].eq(1),
    # #     addr[2].eq(2),
    # #     addr[3].eq(3),
    # #     values[0].eq(5),
    # #     values[1].eq(10),
    # #     values[2].eq(0xF),
    # #     values[3].eq(0xAB)
    # # ]

    # coeff = dict(pow=0x0000, offset=0x0000, ftw0=0x1727, ftw1=0x1929,
    #     a1=a1, b0=b0, b1=b1, cfg=0 | (0 << 3))


    # for ks in "pow offset ftw0 ftw1", "a1 b0 b1 cfg":
    #     for k in ks.split():
    #         # self.set_coeff(self.channel, value=coeff[k],
    #         #     profile=self.profile, coeff=k)

    word = 1
    addr = 2
    mask = 4

    # word, addr, mask = iir._coeff(channel, profile, "a1")
    # print(word, addr, mask)
    m.comb += addrs[0].eq(2), words[0].eq(word), masks[0].eq(0xFFFF)

    m.comb += addrs[1].eq(1), addrs[2].eq(0), addrs[3].eq(3), values[0].eq(0x88), values[2].eq(0x2020)

    m.comb += masks[1].eq(0xFFFF), masks[2].eq(0xFFFF), masks[3].eq(0xFFFF)
        
        
        #     w = iir.widths
        #     val = Signal(2*w.coeff)
        # # # val - data read from memory
        # # # value - data to set
        # # self.sync += val.eq(self.iir.m_coeff[addr])
        # if word:
        #     self.comb += val.eq((val & mask) | ((value & mask) << w.coeff))
        # else:
        #     self.comb += val.eq((value & mask) | (val & (mask << w.coeff)))

        # # self.sync += self.iir.m_coeff[addr].eq(val)




    m.comb += m.start.eq(1)
    run_simulation(m, m.test(), vcd_name="test.vcd")

    # for ks in "pow offset ftw0 ftw1", "a1 b0 b1 cfg":
    # for k in ks.split():
    #     self.set_coeff(self.channel, value=coeff[k],
    #             profile=self.profile, coeff=k)
