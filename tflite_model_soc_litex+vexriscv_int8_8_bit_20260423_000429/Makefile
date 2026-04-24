##############################################################################
# Makefile para firmware SoC LiteX+VexRiscv com TensorFlow Lite
# Laboratório de Desenvolvimento de Software (LDS) - IFCE
##############################################################################

BUILD_DIR ?= ../build-soc-tflite

-include $(BUILD_DIR)/software/include/generated/variables.mak
-include $(SOC_DIRECTORY)/software/common.mak

SW_ABS := $(abspath $(BUILDINC_DIRECTORY)/..)

OBJECTS := crt0.o soc_tensorflow_model.o

all: firmware.bin
	$(TARGET_PREFIX)size firmware.elf

firmware.bin: firmware.elf
	$(OBJCOPY) -O binary $< $@

firmware.elf: $(OBJECTS)
	$(CC) $(LDFLAGS) -T $(SOC_DIRECTORY)/software/bios/linker.ld -N -o $@ \
		$(OBJECTS) \
		-L$(SW_ABS)/libbase \
		-L$(SW_ABS)/libcompiler_rt \
		-L$(SW_ABS)/libc \
		-Wl,--start-group -lbase -lcompiler_rt -lc -Wl,--end-group

crt0.o: $(CPU_DIRECTORY)/crt0.S
	$(assemble)

soc_tensorflow_model.o: soc_tensorflow_model.c
	$(compile)

clean:
	rm -f *.o *.d *.elf *.bin

.PHONY: all clean

# Comandos úteis:
# make -C firmware BUILD_DIR=../build-soc-tflite
# docker run --rm -v $(pwd):/workspace -w /workspace carlosdelfino/colorlight-risc-v:latest \
#   python3 soc.py --board i5 --sys-clk-freq 50e6 --build --output-dir build-soc-tflite
