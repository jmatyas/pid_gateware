from migen import *
from migen.build.generic_platform import *
from migen.genlib.io import DifferentialOutput

from artiq.gateware.szservo import pads as servo_pads
from artiq.gateware.szservo import servo
from artiq.gateware.rtio.phy import servo as rtservo
from artiq.gateware.rtio.phy import spi2, ad53xx_monitor

def _eem_signal(i):
    n = "d{}".format(i)
    if i == 0:
        n += "_cc"
    return n

def _eem_pin(eem, i, pol):
    return "eem{}:{}_{}".format(eem, _eem_signal(i), pol)

class _EEM:
    @classmethod
    def add_extension (cls, target, eem, *args, **kwargs):
        name = cls.__name__
        target.platform.add_extension(cls.io(eem, *args, **kwargs))
        print("{} (EEM){}) starting at RTIO channel {}"
                .fromat(name, eem, len(target.rtio_channels)))

class DIO(_EEM):
    @staticmethod
    def io(eem, iostandard = "LVDS_25"):
        return [
            ("dio{}".format(eem), i,
                Subsignal("p", Pins(_eem_pin(eem, i, "p"))),
                Subsignal("n", Pins(_eem_pin(eem, i, "n"))),
                IOStandard(iostandard))
                for i in range(8)
        ]

class Sampler(_EEM):
    @staticmethod
    def io(eem, eem_aux, iostandard = "LVDS_25"):
        ios = [
            ("sampler{}_adc_spi_p".format(eem), 0,
                Subsignal("clk", Pins(_eem_pin(eem, 0, "p"))),
                Subsignal("miso", Pins(_eem_pin(eem, 1, "p"))),
                IOStandard(iostandard),
            ),
            ("sampler{}_adc_spi_n".format(eem), 0,
                Subsignal("clk", Pins(_eem_pin(eem, 0, "n"))),
                Subsignal("miso", Pins(_eem_pin(eem, 1, "n"))),
                IOStandard(iostandard),
            ),
            ("sampler{}_pgia_spi_p".format(eem), 0,
                Subsignal("clk", Pins(_eem_pin(eem, 4, "p"))),
                Subsignal("mosi", Pins(_eem_pin(eem, 5, "p"))),
                Subsignal("miso", Pins(_eem_pin(eem, 6, "p"))),
                Subsignal("cs_n", Pins(_eem_pin(eem, 7, "p"))),
                IOStandard(iostandard),
            ),
            ("sampler{}_pgia_spi_n".format(eem), 0,
                Subsignal("clk", Pins(_eem_pin(eem, 4, "n"))),
                Subsignal("mosi", Pins(_eem_pin(eem, 5, "n"))),
                Subsignal("miso", Pins(_eem_pin(eem, 6, "n"))),
                Subsignal("cs_n", Pins(_eem_pin(eem, 7, "n"))),
                IOStandard(iostandard),
            ),
        ] + [
            ("sampler{}_{}".format(eem, sig), 0,
                Subsignal("p", Pins(_eem_pin(j, i, "p"))),
                Subsignal("n", Pins(_eem_pin(j, i, "n"))),
                IOStandard(iostandard)
            ) for i, j, sig in [
                (2, eem, "sdr"),
                (3, eem, "cnv")
            ]
        ]
        if eem_aux is not None:
            ios += [
                ("sampler{}_adc_data_p".format(eem), 0,
                    Subsignal("clkout", Pins(_eem_pin(eem_aux, 0, "p"))),
                    Subsignal("sdoa", Pins(_eem_pin(eem_aux, 1, "p"))),
                    Subsignal("sdob", Pins(_eem_pin(eem_aux, 2, "p"))),
                    Subsignal("sdoc", Pins(_eem_pin(eem_aux, 3, "p"))),
                    Subsignal("sdod", Pins(_eem_pin(eem_aux, 4, "p"))),
                    Misc("DIFF_TERM=TRUE"),
                    IOStandard(iostandard),
                ),
                ("sampler{}_adc_data_n".format(eem), 0,
                    Subsignal("clkout", Pins(_eem_pin(eem_aux, 0, "n"))),
                    Subsignal("sdoa", Pins(_eem_pin(eem_aux, 1, "n"))),
                    Subsignal("sdob", Pins(_eem_pin(eem_aux, 2, "n"))),
                    Subsignal("sdoc", Pins(_eem_pin(eem_aux, 3, "n"))),
                    Subsignal("sdod", Pins(_eem_pin(eem_aux, 4, "n"))),
                    Misc("DIFF_TERM=TRUE"),
                    IOStandard(iostandard),
                ),
            ]
        return ios

class Zotino(_EEM):
    @staticmethod
    def io(eem, iostandard="LVDS_25"):
        return [
            ("zotino{}_spi_p".format(eem), 0,
                Subsignal("clk", Pins(_eem_pin(eem, 0, "p"))),
                Subsignal("mosi", Pins(_eem_pin(eem, 1, "p"))),
                Subsignal("miso", Pins(_eem_pin(eem, 2, "p"))),
                Subsignal("cs_n", Pins(_eem_pin(eem, 3, "p"))),
                IOStandard(iostandard),
            ),
            ("zotino{}_spi_n".format(eem), 0,
                Subsignal("clk", Pins(_eem_pin(eem, 0, "n"))),
                Subsignal("mosi", Pins(_eem_pin(eem, 1, "n"))),
                Subsignal("miso", Pins(_eem_pin(eem, 2, "n"))),
                Subsignal("cs_n", Pins(_eem_pin(eem, 3, "n"))),
                IOStandard(iostandard),
            ),
        ] + [
            ("zotino{}_{}".format(eem, sig), 0,
                Subsignal("p", Pins(_eem_pin(j, i, "p"))),
                Subsignal("n", Pins(_eem_pin(j, i, "n"))),
                IOStandard(iostandard)
            ) for i, j, sig in [
                (5, eem, "ldac_n"),
                (6, eem, "busy"),
                (7, eem, "clr_n"),
            ]
        ]
