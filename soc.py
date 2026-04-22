#!/usr/bin/env python3
"""
ColorLight i5/i9 — SoC VexRiscv completo
Equipe RISC-V, Laboratório de Design de Sistemas (LDS)

Gera um SoC RISC-V com:
  - CPU VexRiscv (RV32IM, variant standard)
  - 32 KiB ROM (firmware embutido)
  - 8 KiB SRAM
  - UART 115200 bps
  - Timer
  - LED GPIO

Plataformas suportadas:
  - ColorLight i5 v7.0 — ECP5 LFE5U-25F (24K LUT)
  - ColorLight i9 v7.2 — ECP5 LFE5U-45F (44K LUT)

Uso:
  python3 soc.py                                   # i5, só gera Verilog + headers
  python3 soc.py --board i9                        # i9, só gera Verilog + headers
  python3 soc.py --build                           # gera + sintetiza (BIOS padrão)
  python3 soc.py --build --firmware fw/firmware.bin # gera + sintetiza (firmware custom)
  python3 soc.py --build --flash                   # gera + sintetiza + grava na FPGA
"""

import os
import sys
import argparse
from datetime import datetime

from migen import Signal, ClockDomain
from litex.gen import LiteXModule
from litex.soc.integration.soc_core import SoCCore
from litex.soc.integration.builder import Builder
from litex.soc.integration.common import get_mem_data
from litex.soc.cores.clock import ECP5PLL
from litex.soc.cores.led import LedChaser
from litex.soc.interconnect.csr import AutoCSR, CSRStatus
from litex.build.lattice import LatticePlatform
from litex.build.generic_platform import Pins, Subsignal, IOStandard, Misc

# =============================================================================
# Definição de IOs — ColorLight i5 v7.0 e i9 v7.2
# Fonte: litex-boards (documentado por @smunaut)
# =============================================================================

# --- IOs comuns (clock, serial, reset) ---
_io_common = [
    # Clock 25 MHz
    ("clk25", 0, Pins("P3"), IOStandard("LVCMOS33")),

    # Botão de reset
    ("cpu_reset_n", 0, Pins("K18"), IOStandard("LVCMOS33"), Misc("PULLMODE=UP")),

    # UART (usada automaticamente pelo SoCCore)
    ("serial", 0,
        Subsignal("tx", Pins("J17")),
        Subsignal("rx", Pins("H18")),
        IOStandard("LVCMOS33"),
    ),
]

# --- i5 v7.0: LED no pino U16 ---
_io_i5 = _io_common + [
    ("user_led_n", 0, Pins("U16"), IOStandard("LVCMOS33")),
]

# --- i9 v7.2: LED no pino L2 ---
_io_i9 = _io_common + [
    ("user_led_n", 0, Pins("L2"), IOStandard("LVCMOS33")),
]

# Mapa de configuração por placa
BOARD_CONFIG = {
    "i5": {
        "device": "LFE5U-25F-6BG381C",
        "io":     _io_i5,
        "desc":   "ColorLight i5 v7.0 (ECP5 LFE5U-25F, 24K LUT)",
    },
    "i9": {
        "device": "LFE5U-45F-6BG381C",
        "io":     _io_i9,
        "desc":   "ColorLight i9 v7.2 (ECP5 LFE5U-45F, 44K LUT)",
    },
}

OPENFPGALOADER_BOARD = {
    "i5": "colorlight-i5",
    "i9": "colorlight-i9",
}

CLOCK_PRESETS = {
    "25": 25e6,
    "25mhz": 25e6,
    "50": 50e6,
    "50mhz": 50e6,
    "100": 100e6,
    "100mhz": 100e6,
}

def parse_sys_clk_freq(value):
    text = str(value).strip().lower().replace("_", "")
    if text in CLOCK_PRESETS:
        return float(CLOCK_PRESETS[text])
    multiplier = 1.0
    if text.endswith("mhz"):
        multiplier = 1e6
        text = text[:-3]
    elif text.endswith("khz"):
        multiplier = 1e3
        text = text[:-3]
    elif text.endswith("hz"):
        text = text[:-2]
    freq = float(text) * multiplier
    if multiplier == 1.0 and freq < 1e5:
        freq *= 1e6
    if freq <= 0:
        raise argparse.ArgumentTypeError("A frequência deve ser maior que zero.")
    return float(freq)

def format_sys_clk_freq(freq):
    freq = float(freq)
    if freq >= 1e6:
        return f"{freq / 1e6:g} MHz"
    if freq >= 1e3:
        return f"{freq / 1e3:g} kHz"
    return f"{freq:g} Hz"

def pack_text_words(text, min_words=1):
    data = text.encode("ascii", errors="ignore") + b"\0"
    if len(data) % 4:
        data += b"\0" * (4 - (len(data) % 4))
    words = [int.from_bytes(data[i:i + 4], byteorder="little") for i in range(0, len(data), 4)]
    while len(words) < min_words:
        words.append(0)
    return words

class BuildInfo(LiteXModule, AutoCSR):
    def __init__(self, sys_clk_freq):
        build_dt = datetime.now()
        build_text = build_dt.strftime("%Y-%m-%d %H:%M:%S")
        mode_text = "PLL" if int(float(sys_clk_freq)) != int(25e6) else "DIR"
        org_words = pack_text_words("LDS|IRede|IFCE", min_words=4)
        date_words = pack_text_words(build_text, min_words=5)

        self.clock_hz = CSRStatus(32, reset=int(sys_clk_freq), name="clock_hz")
        self.build_unix = CSRStatus(32, reset=int(build_dt.timestamp()), name="build_unix")
        self.mode = CSRStatus(32, reset=pack_text_words(mode_text, min_words=1)[0], name="mode")
        self.org0 = CSRStatus(32, reset=org_words[0], name="org0")
        self.org1 = CSRStatus(32, reset=org_words[1], name="org1")
        self.org2 = CSRStatus(32, reset=org_words[2], name="org2")
        self.org3 = CSRStatus(32, reset=org_words[3], name="org3")
        self.date_len = CSRStatus(32, reset=len(build_text), name="date_len")
        self.date0 = CSRStatus(32, reset=date_words[0], name="date0")
        self.date1 = CSRStatus(32, reset=date_words[1], name="date1")
        self.date2 = CSRStatus(32, reset=date_words[2], name="date2")
        self.date3 = CSRStatus(32, reset=date_words[3], name="date3")
        self.date4 = CSRStatus(32, reset=date_words[4], name="date4")

# =============================================================================
# CRG — Clock Reset Generator (25 MHz direto, sem PLL)
# =============================================================================
class _CRG(LiteXModule):
    def __init__(self, platform, sys_clk_freq):
        self.rst = Signal()
        self.cd_sys = ClockDomain("sys")

        clk25 = platform.request("clk25")
        rst_n = platform.request("cpu_reset_n")
        use_pll = int(float(sys_clk_freq)) != int(25e6)

        platform.add_period_constraint(clk25, 1e9 / 25e6)

        if use_pll:
            self.pll = ECP5PLL()
            self.comb += self.pll.reset.eq((~rst_n) | self.rst)
            self.pll.register_clkin(clk25, 25e6)
            self.pll.create_clkout(self.cd_sys, sys_clk_freq)
            platform.add_period_constraint(self.cd_sys.clk, 1e9 / sys_clk_freq)
        else:
            self.comb += self.cd_sys.clk.eq(clk25)
            self.comb += self.cd_sys.rst.eq((~rst_n) | self.rst)

# =============================================================================
# SoC ColorLight i5/i9
# =============================================================================
class ColorLightSoC(SoCCore):
    def __init__(self, platform, sys_clk_freq=25e6, **kwargs):
        SoCCore.__init__(self, platform,
            clk_freq            = sys_clk_freq,
            cpu_type            = "vexriscv",
            cpu_variant         = "standard",
            integrated_rom_size = 0x8000,   # 32 KiB — firmware embutido aqui
            integrated_sram_size= 0x2000,   # 8 KiB — SRAM para stack/heap
            uart_baudrate       = 115200,
            **kwargs,
        )

        # CRG
        self.crg = _CRG(platform, sys_clk_freq)

        # LED piscante (1 Hz) — prova visual de que o SoC está rodando
        self.leds = LedChaser(
            pads = platform.request_all("user_led_n"),
            sys_clk_freq = sys_clk_freq,
        )

        self.build_info = BuildInfo(sys_clk_freq)
        self.add_csr("build_info")

# =============================================================================
# Main
# =============================================================================
def main():
    boards_list = ", ".join(BOARD_CONFIG.keys())
    parser = argparse.ArgumentParser(description="ColorLight i5/i9 — SoC VexRiscv")
    parser.add_argument("--board",  default="i5", choices=BOARD_CONFIG.keys(),
                        help=f"Placa alvo ({boards_list}, default: i5)")
    parser.add_argument("--build",    action="store_true", help="Sintetizar e gerar bitstream")
    parser.add_argument("--firmware",  default=None,        help="Firmware .bin para embutir na ROM (substitui BIOS)")
    parser.add_argument("--flash",    action="store_true", help="Gravar bitstream na FPGA")
    parser.add_argument("--output-dir", default="build",   help="Diretório de saída (default: build)")
    parser.add_argument("--sys-clk-freq", type=parse_sys_clk_freq, default=25e6, help="Frequência do clock do sistema (padrão: 25 MHz)")
    args = parser.parse_args()

    # Plataforma
    cfg = BOARD_CONFIG[args.board]
    print(f"Placa: {cfg['desc']}")
    print(f"Clock do sistema: {format_sys_clk_freq(args.sys_clk_freq)}")
    print(f"Modo de clock: {'PLL ECP5' if int(float(args.sys_clk_freq)) != int(25e6) else 'Direto 25 MHz'}")
    platform = LatticePlatform(cfg["device"], cfg["io"], toolchain="trellis")

    # Firmware customizado: carregar binario e injetar na ROM
    rom_init = []
    if args.firmware:
        if not os.path.exists(args.firmware):
            print(f"ERRO: Firmware não encontrado: {args.firmware}")
            sys.exit(1)
        fw_size = os.path.getsize(args.firmware)
        print(f"Firmware customizado: {args.firmware} ({fw_size:,} bytes)")
        rom_init = get_mem_data(args.firmware, endianness="little")
        print(f"ROM init: {len(rom_init)} palavras de 32 bits ({len(rom_init)*4:,} bytes)")

    # SoC
    kwargs = {}
    if rom_init:
        kwargs["integrated_rom_init"] = rom_init
    soc = ColorLightSoC(platform, sys_clk_freq=args.sys_clk_freq, **kwargs)

    # Builder
    # Se firmware customizado, não compilar software (BIOS) do LiteX
    compile_sw = args.build and (args.firmware is None)
    builder = Builder(soc,
        output_dir       = args.output_dir,
        compile_gateware = args.build,
        compile_software = compile_sw,
    )

    builder.build(build_name="colorlight_soc")

    # Listar artefatos gerados
    gw_dir = os.path.join(args.output_dir, "gateware")
    sw_dir = os.path.join(args.output_dir, "software")

    print("\n" + "=" * 60)
    print("Artefatos gerados:")
    print("=" * 60)
    for d in [gw_dir, sw_dir]:
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                fp = os.path.join(d, f)
                if os.path.isfile(fp):
                    sz = os.path.getsize(fp)
                    print(f"  {os.path.relpath(fp, args.output_dir):50s} {sz:>10,} bytes")

    # Flash
    if args.flash:
        bitstream = os.path.join(gw_dir, "colorlight_soc.bit")
        if os.path.exists(bitstream):
            print(f"\nGravando {bitstream} na FPGA...")
            os.system(f"openFPGALoader --board {OPENFPGALOADER_BOARD[args.board]} {bitstream}")
        else:
            print(f"\nERRO: Bitstream não encontrado: {bitstream}")
            print("Execute com --build primeiro.")
            sys.exit(1)

    print("\nConcluído.")

if __name__ == "__main__":
    main()
