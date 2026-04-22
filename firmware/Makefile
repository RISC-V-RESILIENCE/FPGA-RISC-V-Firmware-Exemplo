##############################################################################
# firmware/Makefile — Compilação standalone do firmware customizado
#
# Requer que o SoC tenha sido gerado antes (python3 soc.py --build)
# para que os headers e libs existam em BUILD_DIR/software/
#
# Uso:  make -C firmware BUILD_DIR=$(pwd)/build
##############################################################################

BUILD_DIR ?= ../build

-include $(BUILD_DIR)/software/include/generated/variables.mak
-include $(SOC_DIRECTORY)/software/common.mak

# Diretório de software (absoluto, derivado de BUILDINC_DIRECTORY)
SW_ABS := $(abspath $(BUILDINC_DIRECTORY)/..)

OBJECTS := crt0.o main.o

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

%.o: %.c
	$(compile)

clean:
	rm -f *.o *.d *.elf *.bin

.PHONY: all clean
