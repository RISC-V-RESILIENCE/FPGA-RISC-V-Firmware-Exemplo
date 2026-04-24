##############################################################################
# ColorLight i5/i9 — SoC VexRiscv + Firmware
# Makefile principal
#
# Variáveis:
#   BOARD=i5|i9     — placa alvo (default: i5)
#
# Targets:
#   make gateware   — gera Verilog, sintetiza e produz bitstream
#   make firmware   — compila firmware C (requer gateware primeiro)
#   make all        — gateware + firmware
#   make embed      — gateware + firmware embutido na ROM + reflash
#   make flash      — grava bitstream na FPGA (via OpenOCD/CMSIS-DAP)
#   make load       — carrega firmware via serial (litex_term)
#   make clean      — remove artefatos
#
# Exemplos:
#   make BOARD=i9 gateware   — compila para ColorLight i9
#   make BOARD=i9 embed      — compila + embute firmware + grava (i9)
#   make BOARD=i5 all        — compila tudo para i5 (default)
##############################################################################

BUILD_DIR    := build
BOARD        ?= i9
SYS_CLK_FREQ ?= 65e6
SERIAL_PORT  ?= /dev/ttyACM0
SERIAL_BAUD  ?= 115200

.PHONY: all embed gateware firmware flash flash-persistent load terminal clean verilog

all: gateware firmware

# ---------- Gateware (SoC → Verilog → Netlist → Bitstream + BIOS) ----------

gateware:
	python3 soc.py --board $(BOARD) --sys-clk-freq $(SYS_CLK_FREQ) --build --output-dir $(BUILD_DIR)

verilog:
	python3 soc.py --board $(BOARD) --sys-clk-freq $(SYS_CLK_FREQ) --output-dir $(BUILD_DIR)

prepare-firmware:
	python3 soc.py --board $(BOARD) --sys-clk-freq $(SYS_CLK_FREQ) --build --output-dir $(BUILD_DIR)

# ---------- Firmware customizado (C → ELF → BIN) ----------
# Requer gateware primeiro (gera headers + libs)

firmware: prepare-firmware
	$(MAKE) -C firmware BUILD_DIR=../$(BUILD_DIR)

# ---------- Firmware embutido na ROM ----------
# Compila o firmware customizado e reconstrói o gateware com ele na ROM.
# Usa --firmware do soc.py para injetar via API do LiteX (get_mem_data).
# O BIOS padrão do LiteX NÃO é compilado neste modo.

embed: firmware
	@echo "Reconstruindo gateware com firmware customizado na ROM..."
	python3 soc.py --board $(BOARD) --sys-clk-freq $(SYS_CLK_FREQ) --build --firmware firmware/firmware.bin --output-dir $(BUILD_DIR)
	@echo "Bitstream com firmware embutido pronto em $(BUILD_DIR)/gateware/colorlight_soc.bit"

# ---------- Gravar na FPGA ----------
# A ColorLight i5/i9 (Muse Lab) usa DAPLink CMSIS-DAP para JTAG.
# Docker: requer --privileged -v /dev/bus/usb:/dev/bus/usb
# OpenOCD é preferido pois o openFPGALoader (OSS CAD Suite) não tem hidapi.
#
# JTAG IDCODE: i5 (LFE5U-25F) = 0x41111043, i9 (LFE5U-45F) = 0x41112043

OPENOCD_SCRIPTS ?= /opt/oss-cad-suite/share/openocd/scripts
JTAG_ID_i5      := 0x41111043
JTAG_ID_i9      := 0x41112043
JTAG_ID         := $(JTAG_ID_$(BOARD))
OPENFPGALOADER_BOARD_i5 := colorlight-i5
OPENFPGALOADER_BOARD_i9 := colorlight-i9
OPENFPGALOADER_BOARD    := $(OPENFPGALOADER_BOARD_$(BOARD))

OPENOCD_BASE    := openocd -s $(OPENOCD_SCRIPTS) \
	-f interface/cmsis-dap.cfg \
	-c "adapter speed 1000; transport select jtag" \
	-c "jtag newtap ecp5 tap -irlen 8 -expected-id $(JTAG_ID)"

flash:
	$(OPENOCD_BASE) -c "init; svf -quiet $(BUILD_DIR)/gateware/colorlight_soc.svf; exit"

flash-detect:
	$(OPENOCD_BASE) -c "init; scan_chain; exit"

flash-openFPGALoader:
	openFPGALoader --board $(OPENFPGALOADER_BOARD) $(BUILD_DIR)/gateware/colorlight_soc.bit

flash-persistent:
	openFPGALoader --board $(OPENFPGALOADER_BOARD) --write-flash --verify --reset $(BUILD_DIR)/gateware/colorlight_soc.bit

# ---------- Carregar firmware via serial ----------

load:
	litex_term $(SERIAL_PORT) --speed $(SERIAL_BAUD) --kernel firmware/firmware.bin

terminal:
	litex_term $(SERIAL_PORT) --speed $(SERIAL_BAUD)

# ---------- Limpeza ----------

clean:
	rm -rf $(BUILD_DIR)
	$(MAKE) -C firmware clean
