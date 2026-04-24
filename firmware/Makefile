##############################################################################
# firmware/Makefile - Compilação firmware com modelo TensorFlow Lite
##############################################################################

BUILD_DIR ?= ../build-soc-tflite

-include $(BUILD_DIR)/software/include/generated/variables.mak
-include $(SOC_DIRECTORY)/software/common.mak

SW_ABS := $(abspath $(BUILDINC_DIRECTORY)/..)

# =============================================================================
# TensorFlow Lite Micro integration
# =============================================================================
# Ativa/desativa integração TFLM (0 = usa apenas caminho int8 manual).
USE_TFLM ?= 1

TFLM_ROOT   := tflm
TFLM_LIBDIR := $(TFLM_ROOT)/gen/riscv32_generic_riscv32_micro_gcc/lib
TFLM_LIB    := $(TFLM_LIBDIR)/libtensorflow-microlite.a
TFLM_TOOLCHAIN_BIN := $(TFLM_ROOT)/tensorflow/lite/micro/tools/make/downloads/riscv_toolchain/bin
TFLM_CXX    := $(TFLM_TOOLCHAIN_BIN)/riscv64-unknown-elf-g++
TFLM_AR     := $(TFLM_TOOLCHAIN_BIN)/riscv64-unknown-elf-ar

TFLM_INCLUDES := \
	-I$(TFLM_ROOT) \
	-I$(TFLM_ROOT)/tensorflow/lite/micro/tools/make/downloads \
	-I$(TFLM_ROOT)/tensorflow/lite/micro/tools/make/downloads/flatbuffers/include \
	-I$(TFLM_ROOT)/tensorflow/lite/micro/tools/make/downloads/gemmlowp \
	-I$(TFLM_ROOT)/tensorflow/lite/micro/tools/make/downloads/ruy

# NOTA (2026-04): -flto removido dos flags do TFLM para contornar ICE
# 'lto1: internal compiler error: compressed stream: data error' no GCC 8.1.0
# do toolchain SiFive baixado pelo TFLM. A libtensorflow-microlite.a é
# construída SEM LTO (confirmado por readelf: ausência de seções
# .gnu.lto_*) e misturar objetos LTO com o archive faz o LTO plugin do
# linker falhar. Mantemos as demais otimizações (-Os + gc-sections).
TFLM_CXXFLAGS := -march=rv32im -mabi=ilp32 -mcmodel=medany \
	-Os -g -ffunction-sections -fdata-sections \
	-fno-exceptions -fno-rtti -fno-threadsafe-statics -fno-use-cxa-atexit \
	-DTF_LITE_STATIC_MEMORY -DTF_LITE_MCU_DEBUG_LOG \
	-DTF_LITE_USE_GLOBAL_MIN -DTF_LITE_USE_GLOBAL_MAX \
	-DTF_LITE_USE_GLOBAL_CMATH_FUNCTIONS \
	-fpermissive -std=c++17 -funsigned-char \
	-fno-builtin -fno-common -fmerge-constants -fno-unwind-tables -fno-asynchronous-unwind-tables

ifeq ($(USE_TFLM),1)
OBJECTS := crt0.o main.o neural_fixedpoint.o tflm_runner.o
else
OBJECTS := crt0.o main.o neural_fixedpoint.o
endif

all: firmware.bin
	@echo "=== Code Size Analysis ==="
	$(TARGET_PREFIX)size firmware.elf
	@echo "=========================="
	@echo "Memory usage:" 
	@$(TARGET_PREFIX)size -A firmware.elf | grep -E '\.(text|data|bss)'
	@echo "=========================="

firmware.bin: firmware.elf
	$(OBJCOPY) -O binary $< $@

ifeq ($(USE_TFLM),1)
# Linker: usa g++ do toolchain SiFive (mesmo usado para compilar o libmicrolite)
# para garantir consistência de libstdc++/libsupc++ e evitar conflitos de ABI.
firmware.elf: $(OBJECTS) $(TFLM_LIB)
	$(TFLM_CXX) -march=rv32im -mabi=ilp32 -mcmodel=medany -nostartfiles \
		-T $(SOC_DIRECTORY)/software/bios/linker.ld -N \
		-L$(BUILDINC_DIRECTORY) \
		-Wl,--gc-sections -Wl,--no-relax -Wl,--strip-all -Wl,--print-memory-usage \
		-fno-lto \
		-DUSE_TFLM=1 \
		-o $@ $(OBJECTS) \
		-L$(SW_ABS)/libbase \
		-L$(SW_ABS)/libcompiler_rt \
		-L$(SW_ABS)/libc \
		-Wl,--start-group -lbase -lcompiler_rt -lc $(TFLM_LIB) -lstdc++ -lsupc++ -lm -lgcc -Wl,--end-group
else
firmware.elf: $(OBJECTS)
	$(CC) $(LDFLAGS) -Os -flto -T $(SOC_DIRECTORY)/software/bios/linker.ld -N \
		-Wl,--gc-sections -Wl,--strip-all -Wl,--print-memory-usage \
		-o $@ $(OBJECTS) \
		-L$(SW_ABS)/libbase \
		-L$(SW_ABS)/libcompiler_rt \
		-L$(SW_ABS)/libc \
		-Wl,--start-group -lbase -lcompiler_rt -lc -Wl,--end-group
endif

$(TFLM_LIB):
	@echo "[TFLM] Biblioteca ausente em $(TFLM_LIB); execute ./build_tflm_lib.sh"
	@test -f $(TFLM_LIB)

# Regra explícita para compilar o wrapper C++ com o toolchain do TFLM.
tflm_runner.o: tflm_runner.cc tflm_runner.h
	$(TFLM_CXX) $(TFLM_CXXFLAGS) $(TFLM_INCLUDES) \
		-I$(BUILDINC_DIRECTORY) -I$(BUILDINC_DIRECTORY)/../libc \
		-DUSE_TFLM=1 -c $< -o $@

# Ao compilar neural_fixedpoint.c com USE_TFLM=1, define o macro para ativar
# o caminho TFLM no código (o de ponto fixo manual fica como fallback).
# -flto condicional: desabilitado no modo TFLM (USE_TFLM=1) porque o link
# final com libtensorflow-microlite.a (não-LTO) provoca ICE no GCC 8.1.0.
# Para o build sem TFLM mantemos LTO, onde o linker trabalha apenas com
# nossos próprios objetos e a libbase do LiteX.
LTO_FLAG_$(USE_TFLM) := $(if $(filter 1,$(USE_TFLM)),,-flto)
LTO_FLAG := $(LTO_FLAG_$(USE_TFLM))

neural_fixedpoint.o: neural_fixedpoint.c neural_fixedpoint.h neural_model.h tflm_runner.h
	$(CC) -c $(CFLAGS) -Os -ffunction-sections -fdata-sections $(LTO_FLAG) -fno-builtin -fmerge-constants -DUSE_TFLM=$(USE_TFLM) $< -o $@

crt0.o: $(CPU_DIRECTORY)/crt0.S
	$(assemble)

main.o: main.c neural_fixedpoint.h
	$(CC) -c $(CFLAGS) -Os -ffunction-sections -fdata-sections $(LTO_FLAG) -fno-builtin -fmerge-constants $< -o $@

%.o: %.c
	$(CC) -c $(CFLAGS) -Os -ffunction-sections -fdata-sections $(LTO_FLAG) -fno-builtin -fmerge-constants $< -o $@

clean:
	rm -f *.o *.d *.elf *.bin

.PHONY: all clean
