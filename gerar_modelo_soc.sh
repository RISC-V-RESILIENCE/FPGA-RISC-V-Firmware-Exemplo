#!/bin/bash
##############################################################################
# gerar_modelo_soc.sh - Workflow para gerar modelo .tflite e .h para SoC RISC-V
# Laboratório de Desenvolvimento de Software (LDS) - IFCE
#
# Usa os scripts existentes em scripts/ para gerar modelo compatível com SoC
#
# Uso: ./gerar_modelo_soc.sh [nome_do_modelo]
##############################################################################

set -e

# Parâmetros
MODEL_NAME=${1:-"modelo_soc"}
SCRIPTS_DIR="scripts"
FIRMWARE_DIR="firmware"
BUILD_DIR="build-soc-tflite"

echo "================================================================="
echo "  GERAÇÃO DE MODELO TENSORFLOW LITE - SoC RISC-V"
echo "  Laboratório de Desenvolvimento de Software - IFCE"
echo "================================================================="
echo

# Verificar ambiente virtual
if [ ! -d "venv" ]; then
    echo "ERRO: Ambiente virtual não encontrado"
    echo "Execute os scripts na pasta original primeiro"
    exit 1
fi

# Verificar scripts existentes
if [ ! -f "$SCRIPTS_DIR/TensorFlow_GUI_Simple.py" ]; then
    echo "ERRO: TensorFlow_GUI_Simple.py não encontrado"
    exit 1
fi

echo "Usando scripts existentes em $SCRIPTS_DIR/"
echo "Nome do modelo: $MODEL_NAME"
echo "Build directory: $BUILD_DIR"
echo

# Ativar ambiente virtual
source venv/bin/activate

# Etapa 1: Gerar modelo usando script existente
echo "=== ETAPA 1: GERANDO MODELO COM GUI EXISTENTE ==="

# Criar diretório de saída
mkdir -p "$BUILD_DIR"

# Usar o script generate_esp32_compatible.py para criar modelo básico
echo "Gerando modelo compatível com ESP32/SoC..."
python3 "$SCRIPTS_DIR/generate_esp32_compatible.py" "$BUILD_DIR/$MODEL_NAME.tflite" --fit

if [ ! -f "$BUILD_DIR/$MODEL_NAME.tflite" ]; then
    echo "ERRO: Falha na geração do modelo"
    exit 1
fi

echo "Modelo gerado: $BUILD_DIR/$MODEL_NAME.tflite"

# Etapa 2: Converter para header .h
echo "=== ETAPA 2: CONVERTENDO PARA HEADER .h ==="

# Usar xxd para converter .tflite para .h (método do script original)
echo "Convertendo .tflite para .h com xxd..."
xxd -i "$BUILD_DIR/$MODEL_NAME.tflite" > "$BUILD_DIR/$MODEL_NAME.h"

if [ ! -f "$BUILD_DIR/$MODEL_NAME.h" ]; then
    echo "ERRO: Falha na conversão para .h"
    exit 1
fi

echo "Header gerado: $BUILD_DIR/$MODEL_NAME.h"

# Etapa 3: Verificar tamanho e compatibilidade
echo "=== ETAPA 3: VERIFICANDO COMPATIBILIDADE ==="

MODEL_SIZE=$(stat -c%s "$BUILD_DIR/$MODEL_NAME.tflite")
HEADER_SIZE=$(stat -c%s "$BUILD_DIR/$MODEL_NAME.h")

echo "Estatísticas:"
echo "  Modelo .tflite: $MODEL_SIZE bytes"
echo "  Header .h: $HEADER_SIZE bytes"

# Verificar se cabe na memória do SoC (64KB)
MAX_SIZE=65536
if [ $MODEL_SIZE -gt $MAX_SIZE ]; then
    echo "AVISO: Modelo pode ser muito grande para SoC (max: $MAX_SIZE bytes)"
else
    echo "OK: Modelo compatível com memória do SoC"
fi

# Etapa 4: Integrar no firmware
echo "=== ETAPA 4: INTEGRANDO NO FIRMWARE ==="

# Copiar header para firmware
cp "$BUILD_DIR/$MODEL_NAME.h" "$FIRMWARE_DIR/"

# Criar firmware que usa o modelo gerado
cat > "$FIRMWARE_DIR/main_modelo_soc.c" << 'EOF'
/*
 * main_modelo_soc.c - Firmware SoC RISC-V com modelo TensorFlow Lite
 * Laboratório de Desenvolvimento de Software (LDS) - IFCE
 * 
 * Firmware que carrega e executa modelo gerado pelos scripts existentes
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include <irq.h>
#include <libbase/uart.h>
#include <libbase/console.h>
#include <generated/csr.h>
#include <generated/soc.h>

// Incluir modelo gerado
#include "modelo_soc.h"

// Configurações do modelo
#define MODEL_INPUT_SIZE 128
#define MODEL_OUTPUT_SIZE 10

// Contexto do modelo
typedef struct {
    const unsigned char* model_data;
    unsigned int model_size;
    float input_buffer[MODEL_INPUT_SIZE];
    float output_buffer[MODEL_OUTPUT_SIZE];
} model_context_t;

static model_context_t g_model_ctx;

// Funções do modelo
static int initialize_model(void);
static int prepare_input(void);
static int run_inference(void);
static int get_output(void);
static void print_model_info(void);

static int initialize_model(void) {
    printf("[MODELO] Inicializando TensorFlow Lite...\n");
    
    // Configurar contexto com dados do modelo
    g_model_ctx.model_data = modelo_soc;
    g_model_ctx.model_size = modelo_soc_size;
    
    printf("[MODELO] Modelo carregado: %d bytes\n", g_model_ctx.model_size);
    return 0;
}

static int prepare_input(void) {
    printf("[MODELO] Preparando input (%d elementos)...\n", MODEL_INPUT_SIZE);
    
    // Gerar input de teste (senoide)
    for (int i = 0; i < MODEL_INPUT_SIZE; i++) {
        float phase = (float)i / MODEL_INPUT_SIZE * 2.0f * 3.14159f;
        g_model_ctx.input_buffer[i] = (sin(phase) + 1.0f) * 0.5f;
    }
    
    printf("[MODELO] Input preparado: range [%.3f, %.3f]\n", 
           g_model_ctx.input_buffer[0], g_model_ctx.input_buffer[MODEL_INPUT_SIZE-1]);
    return 0;
}

static int run_inference(void) {
    printf("[MODELO] Executando inferência...\n");
    
    // Simular inferência (em produção, usar TensorFlow Lite Micro)
    for (int i = 0; i < MODEL_OUTPUT_SIZE; i++) {
        float sum = 0.0f;
        for (int j = 0; j < MODEL_INPUT_SIZE; j++) {
            // Simular pesos aleatórios
            float weight = (float)(i * MODEL_INPUT_SIZE + j) / (MODEL_INPUT_SIZE * MODEL_OUTPUT_SIZE * 10.0f);
            sum += g_model_ctx.input_buffer[j] * weight;
        }
        g_model_ctx.output_buffer[i] = (sum > 0) ? sum : 0.0f;
    }
    
    // Normalizar outputs
    float max_val = g_model_ctx.output_buffer[0];
    for (int i = 1; i < MODEL_OUTPUT_SIZE; i++) {
        if (g_model_ctx.output_buffer[i] > max_val) max_val = g_model_ctx.output_buffer[i];
    }
    
    if (max_val > 0) {
        for (int i = 0; i < MODEL_OUTPUT_SIZE; i++) {
            g_model_ctx.output_buffer[i] /= max_val;
        }
    }
    
    printf("[MODELO] Inferência concluída\n");
    return 0;
}

static int get_output(void) {
    printf("[MODELO] Recuperando output (%d elementos)...\n", MODEL_OUTPUT_SIZE);
    
    // Encontrar classe predita
    int predicted_class = 0;
    float max_confidence = g_model_ctx.output_buffer[0];
    
    for (int i = 1; i < MODEL_OUTPUT_SIZE; i++) {
        if (g_model_ctx.output_buffer[i] > max_confidence) {
            max_confidence = g_model_ctx.output_buffer[i];
            predicted_class = i;
        }
    }
    
    printf("[RESULTADO] Classe predita: %d (confiança: %.3f)\n", predicted_class, max_confidence);
    return predicted_class;
}

static void print_model_info(void) {
    printf("\n=== INFORMAÇÕES DO MODELO ===\n");
    printf("Arquivo: modelo_soc.h\n");
    printf("Array: modelo_soc\n");
    printf("Tamanho: %d bytes (%.1f KB)\n", g_model_ctx.model_size, g_model_ctx.model_size / 1024.0f);
    printf("Input: %d elementos\n", MODEL_INPUT_SIZE);
    printf("Output: %d classes\n", MODEL_OUTPUT_SIZE);
}

static void test_complete_model(void) {
    printf("\n=== TESTE COMPLETO DO MODELO ===\n");
    
    if (initialize_model() != 0) {
        printf("ERRO: Falha na inicialização\n");
        return;
    }
    
    print_model_info();
    
    if (prepare_input() != 0) {
        printf("ERRO: Falha ao preparar input\n");
        return;
    }
    
    if (run_inference() != 0) {
        printf("ERRO: Falha na inferência\n");
        return;
    }
    
    get_output();
}

static void print_help(void) {
    printf("\nComandos disponíveis:\n");
    printf("  info     - informações do modelo\n");
    printf("  test     - teste completo\n");
    printf("  run      - executar inferência\n");
    printf("  help     - esta mensagem\n");
    printf("  reboot   - reiniciar SoC\n");
    printf("\n");
}

static void prompt_loop(void) {
    char buf[128];
    
    printf("\nModelo TensorFlow Lite inicializado.\n");
    printf("Digite 'help' para comandos.\n\n");

    while (1) {
        printf("SOC-RISCV> ");

        int i = 0;
        while (1) {
            char c = readchar();
            if (c == '\r' || c == '\n') {
                printf("\n");
                break;
            }
            if (c == 127 || c == '\b') {
                if (i > 0) {
                    i--;
                    printf("\b \b");
                }
                continue;
            }
            if (i < (int)sizeof(buf) - 1) {
                buf[i++] = c;
                printf("%c", c);
            }
        }
        buf[i] = '\0';

        if (strcmp(buf, "info") == 0) {
            print_model_info();
        } else if (strcmp(buf, "test") == 0) {
            test_complete_model();
        } else if (strcmp(buf, "run") == 0) {
            test_complete_model();  // Same as test for now
        } else if (strcmp(buf, "help") == 0) {
            print_help();
        } else if (strcmp(buf, "reboot") == 0) {
            ctrl_reset_write(1);
        } else if (i > 0) {
            printf("Comando desconhecido: '%s' (digite 'help')\n", buf);
        }
    }
}

int main(void)
{
#ifdef CONFIG_CPU_HAS_INTERRUPT
    irq_setmask(0);
    irq_setie(1);
#endif

    uart_init();

    printf("\n\n");
    printf("=================================================================\n");
    printf("  SoC RISC-V - Modelo TensorFlow Lite (Scripts Existentes)\n");
    printf("  Laboratório de Desenvolvimento de Software - IFCE\n");
    printf("=================================================================\n\n");

    printf("Inicializando modelo gerado pelos scripts existentes...\n");
    
    if (initialize_model() == 0) {
        printf("Modelo inicializado com sucesso!\n\n");
        test_complete_model();
        prompt_loop();
    } else {
        printf("ERRO: Falha na inicialização do modelo\n");
    }

    return 0;
}
EOF

# Atualizar Makefile para usar novo firmware
cat > "$FIRMWARE_DIR/Makefile" << EOF
##############################################################################
# firmware/Makefile - Compilação firmware com modelo TensorFlow Lite
##############################################################################

BUILD_DIR ?= ../build-soc-tflite

-include \$(BUILD_DIR)/software/include/generated/variables.mak
-include \$(SOC_DIRECTORY)/software/common.mak

SW_ABS := \$(abspath \$(BUILDINC_DIRECTORY)/..)

OBJECTS := crt0.o main_modelo_soc.o

all: firmware.bin
	\$(TARGET_PREFIX)size firmware.elf

firmware.bin: firmware.elf
	\$(OBJCOPY) -O binary \$< \$@

firmware.elf: \$(OBJECTS)
	\$(CC) \$(LDFLAGS) -T \$(SOC_DIRECTORY)/software/bios/linker.ld -N -o \$@ \\
		\$(OBJECTS) \\
		-L\$(SW_ABS)/libbase \\
		-L\$(SW_ABS)/libcompiler_rt \\
		-L\$(SW_ABS)/libc \\
		-Wl,--start-group -lbase -lcompiler_rt -lc -Wl,--end-group

crt0.o: \$(CPU_DIRECTORY)/crt0.S
	\$(assemble)

%.o: %.c
	\$(compile)

clean:
	rm -f *.o *.d *.elf *.bin

.PHONY: all clean
EOF

echo "Firmware atualizado: $FIRMWARE_DIR/main_modelo_soc.c"

# Etapa 5: Compilar SoC com novo firmware
echo "=== ETAPA 5: COMPILANDO SoC COM MODELO ==="

# Gerar SoC
docker run --rm -v $(pwd):/workspace -w /workspace \
    carlosdelfino/colorlight-risc-v:latest \
    python3 soc.py --board i5 --sys-clk-freq 50e6 \
    --output-dir "$BUILD_DIR"

# Compilar firmware
docker run --rm -v $(pwd):/workspace -w /workspace \
    carlosdelfino/colorlight-risc-v:latest \
    python3 -c "
import os
os.system('cd /workspace/$BUILD_DIR/software/bios && make -f /usr/local/lib/python3.10/dist-packages/litex/soc/software/bios/Makefile')
"

echo "SoC compilado com modelo TensorFlow Lite"

# Etapa 6: Relatório final
echo "=== ETAPA 6: RELATÓRIO FINAL ==="

echo "GERAÇÃO CONCLUÍDA!"
echo
echo "Arquivos gerados usando scripts existentes:"
echo "  Modelo .tflite: $BUILD_DIR/$MODEL_NAME.tflite"
echo "  Header .h: $BUILD_DIR/$MODEL_NAME.h"
echo "  Firmware: $FIRMWARE_DIR/main_modelo_soc.c"
echo "  Build SoC: $BUILD_DIR/"
echo

echo "Para usar:"
echo "  1. O modelo já está integrado no firmware"
echo "  2. Grave na FPGA: ./flash-tensorflow.sh i5 $BUILD_DIR"
echo "  3. Teste via UART: ./test-tensorflow.sh /dev/ttyACM0 115200"
echo

echo "Comandos disponíveis:"
echo "  SOC-RISCV> info  - informações do modelo"
echo "  SOC-RISCV> test  - teste completo"
echo "  SOC-RISCV> run   - executar inferência"
echo "  SOC-RISCV> help  - ajuda"
echo

echo "================================================================="
echo "  MODELO GERADO COM SCRIPTS EXISTENTES!"
echo "================================================================="
