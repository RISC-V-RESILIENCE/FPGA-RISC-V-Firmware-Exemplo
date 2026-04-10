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

from migen import Signal, ClockDomain, Module, Instance, Cat
from litex.gen import LiteXModule
from litex.soc.integration.soc_core import SoCCore
from litex.soc.integration.builder import Builder
from litex.soc.integration.common import get_mem_data
from litex.soc.cores.led import LedChaser
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

# =============================================================================
# CRG — Clock Reset Generator (25 MHz direto, sem PLL)
# =============================================================================
class _CRG(LiteXModule):
    def __init__(self, platform, sys_clk_freq):
        self.rst = Signal()
        self.cd_sys = ClockDomain("sys")

        clk25 = platform.request("clk25")
        self.comb += self.cd_sys.clk.eq(clk25)
        self.comb += self.cd_sys.rst.eq(self.rst)
        platform.add_period_constraint(clk25, 1e9 / sys_clk_freq)

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
    args = parser.parse_args()

    # Plataforma
    cfg = BOARD_CONFIG[args.board]
    print(f"Placa: {cfg['desc']}")
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
    soc = ColorLightSoC(platform, **kwargs)

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
            os.system(f"openFPGALoader --board colorlight-i5 {bitstream}")
        else:
            print(f"\nERRO: Bitstream não encontrado: {bitstream}")
            print("Execute com --build primeiro.")
            sys.exit(1)

    print("\nConcluído.")

if __name__ == "__main__":
    main()
