/*
 * firmware/main.c — Firmware para SoC VexRiscv na ColorLight i5
 * Equipe RISC-V — Laboratório de Design de Sistemas (LDS)
 *
 * Imprime ASCII art "RISC-V LDS" via UART a 115200 bps e pisca o LED.
 *
 * Compilação:  make -C firmware/
 * Dependência: headers gerados pelo LiteX em build/software/include/
 */

#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include <irq.h>
#include <libbase/uart.h>
#include <libbase/console.h>
#include <generated/csr.h>
#include <generated/soc.h>
#include <generated/mem.h>

#include "neural_fixedpoint.h"

/* ---------------------------------------------------------------------------
 * Símbolos exportados pelo linker script do LiteX (software/bios/linker.ld).
 * Usados para inferir o consumo real de ROM/SRAM do firmware em runtime:
 *   _ftext..._etext        -> seção .text (código, vive na ROM)
 *   _frodata..._erodata    -> seção .rodata (constantes, vive na ROM)
 *   _fdata..._edata        -> seção .data (inicializada, copiada ROM->SRAM)
 *   _fbss..._ebss          -> seção .bss (zerada em SRAM)
 *   _end                   -> fim estático do uso de SRAM (antes do heap)
 * Os nomes seguem a convenção histórica do BIOS do LiteX; caso uma seção não
 * exista (p.ex. .rodata vazia), o linker ainda emite os símbolos coincidentes.
 * --------------------------------------------------------------------------- */
extern char _ftext, _etext;
extern char _frodata, _erodata;
extern char _fdata,  _edata;
extern char _fbss,   _ebss;
extern char _end;

/* ========================================================================= */
/* ASCII Art                                                                  */
/* ========================================================================= */
static const char *ascii_art[] = {
    "",
    "  ==================================================================",
    "  ||                                                              ||",
    "  ||  ░▒▓███████▓▒░░▒▓█▓▒░░▒▓███████▓▒░░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░ ||",
    "  ||  ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ ||",
    "  ||  ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░       ░▒▓█▓▒▒▓█▓▒░  ||",
    "  ||  ░▒▓███████▓▒░░▒▓█▓▒░░▒▓██████▓▒░░▒▓█▓▒░       ░▒▓█▓▒▒▓█▓▒░  ||",
    "  ||  ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒░        ░▒▓█▓▓█▓▒░   ||",
    "  ||  ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▓█▓▒░   ||",
    "  ||  ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░▒▓███████▓▒░ ░▒▓██████▓▒░   ░▒▓██▓▒░    ||",
    "  ||                                                              ||",
    "  ||         Laboratorio de Desenvolvimento de Software           ||",
    "  ||                      Equipe RISC-V                           ||",
    "  ||                      IFCE -- iREDE                           ||",
    "  ||                                                              ||",
    "  ||  SoC: LiteX + VexRiscv (RV32IM)                              ||",
    /* Linha da FPGA é emitida dinamicamente em print_banner() a partir dos
     * metadados gravados no CSR build_info (preenchido em soc.py com a placa
     * efetivamente selecionada via BOARD=... no make). */
    "  ==================================================================",
    "",
    NULL,
};

/* ========================================================================= */
/* Funções auxiliares                                                         */
/* ========================================================================= */

static void print_packed_text_word(unsigned int word);

static unsigned long get_build_clock_hz(void)
{
#ifdef CSR_BUILD_INFO_BASE
    return (unsigned long)build_info_clock_hz_read();
#else
    return (unsigned long)CONFIG_CLOCK_FREQUENCY;
#endif
}

/* ---------------------------------------------------------------------------
 * Metadados da placa alvo (reconstruídos a partir do CSR build_info).
 * A descrição é empacotada em até 16 palavras little-endian pelo soc.py
 * (BuildInfo.BOARD_DESC_WORDS) e aqui remontada como uma string ASCII.
 * --------------------------------------------------------------------------- */
#ifdef CSR_BUILD_INFO_BASE
#define BOARD_DESC_BUF_SIZE 68  /* 16 words * 4 bytes + terminador */

static void read_board_desc(char *buf, size_t len)
{
    /* Acessores gerados pelo LiteX são funções nomeadas individualmente,
     * então materializamos a leitura em uma tabela compacta para iterar. */
    typedef uint32_t (*csr_rd_fn)(void);
    static const csr_rd_fn readers[] = {
        build_info_board_desc0_read,  build_info_board_desc1_read,
        build_info_board_desc2_read,  build_info_board_desc3_read,
        build_info_board_desc4_read,  build_info_board_desc5_read,
        build_info_board_desc6_read,  build_info_board_desc7_read,
        build_info_board_desc8_read,  build_info_board_desc9_read,
        build_info_board_desc10_read, build_info_board_desc11_read,
        build_info_board_desc12_read, build_info_board_desc13_read,
        build_info_board_desc14_read, build_info_board_desc15_read,
    };
    const size_t nwords = sizeof(readers) / sizeof(readers[0]);
    size_t pos = 0;
    for (size_t w = 0; w < nwords && pos + 1 < len; w++) {
        uint32_t v = readers[w]();
        for (int i = 0; i < 4 && pos + 1 < len; i++) {
            char c = (char)((v >> (8 * i)) & 0xff);
            if (c == '\0') {
                buf[pos] = '\0';
                return;
            }
            buf[pos++] = c;
        }
    }
    buf[pos < len ? pos : len - 1] = '\0';
}

static void read_board_id(char out[5])
{
    uint32_t v = build_info_board_id_read();
    int i;
    for (i = 0; i < 4; i++) {
        char c = (char)((v >> (8 * i)) & 0xff);
        if (c == '\0') break;
        out[i] = c;
    }
    out[i] = '\0';
}
#endif /* CSR_BUILD_INFO_BASE */

/* ---------------------------------------------------------------------------
 * Consumo de memória do firmware, derivado dos símbolos do linker.
 *   ROM_used  = .text + .rodata + .data (imagem gravada na ROM)
 *   SRAM_used = .data + .bss            (ocupação estática em SRAM)
 * Observação: não inclui pilha nem heap (alocados dinamicamente no topo).
 * --------------------------------------------------------------------------- */
static unsigned long fw_text_size(void)   { return (unsigned long)(&_etext   - &_ftext); }
static unsigned long fw_rodata_size(void) { return (unsigned long)(&_erodata - &_frodata); }
static unsigned long fw_data_size(void)   { return (unsigned long)(&_edata   - &_fdata); }
static unsigned long fw_bss_size(void)    { return (unsigned long)(&_ebss    - &_fbss); }

static unsigned long fw_rom_used(void)
{
    return fw_text_size() + fw_rodata_size() + fw_data_size();
}

static unsigned long fw_sram_used(void)
{
    return fw_data_size() + fw_bss_size();
}

static unsigned long soc_rom_size(void)
{
#ifdef CSR_BUILD_INFO_BASE
    return (unsigned long)build_info_rom_size_read();
#elif defined(ROM_SIZE)
    return (unsigned long)ROM_SIZE;
#else
    return 0;
#endif
}

static unsigned long soc_sram_size(void)
{
#ifdef CSR_BUILD_INFO_BASE
    return (unsigned long)build_info_sram_size_read();
#elif defined(SRAM_SIZE)
    return (unsigned long)SRAM_SIZE;
#else
    return 0;
#endif
}

static void print_memory_usage(const char *prefix)
{
    unsigned long rom_total = soc_rom_size();
    unsigned long sram_total = soc_sram_size();
    unsigned long rom_used  = fw_rom_used();
    unsigned long sram_used = fw_sram_used();

    printf("%sROM : %6lu / %6lu bytes usados (%lu KiB total, livre=%ld)\n",
           prefix, rom_used, rom_total, rom_total / 1024,
           (long)rom_total - (long)rom_used);
    printf("%sSRAM: %6lu / %6lu bytes usados (%lu KiB total, livre=%ld)\n",
           prefix, sram_used, sram_total, sram_total / 1024,
           (long)sram_total - (long)sram_used);
    printf("%s      .text=%lu  .rodata=%lu  .data=%lu  .bss=%lu\n",
           prefix, fw_text_size(), fw_rodata_size(),
           fw_data_size(), fw_bss_size());
}

static void print_banner(void)
{
    const char **line = ascii_art;
    while (*line) {
        printf("%s\n", *line);
        line++;
    }

    /* Linha dinâmica da FPGA: lê a descrição gravada no CSR build_info pelo
     * soc.py no momento em que o gateware foi sintetizado (valor de BOARD
     * repassado via Makefile). Cai em um rótulo genérico caso o CSR não
     * esteja disponível (ex.: build antigo sem BuildInfo.board_desc*). */
#ifdef CSR_BUILD_INFO_BASE
    char desc[BOARD_DESC_BUF_SIZE];
    char bid[5] = {0};
    read_board_desc(desc, sizeof(desc));
    read_board_id(bid);
    if (desc[0] != '\0') {
        printf("  FPGA : %s\n", desc);
    } else {
        printf("  FPGA : (descrição indisponível)\n");
    }
    if (bid[0] != '\0') {
        printf("  BOARD: %s\n", bid);
    }
#else
    printf("  FPGA : ColorLight (build sem CSR build_info)\n");
#endif

    printf("  Clock: %lu MHz | UART: 115200 bps\n", get_build_clock_hz() / 1000000);
    print_memory_usage("  ");

#ifdef CSR_BUILD_INFO_BASE
    printf("  Build mode: ");
    print_packed_text_word(build_info_mode_read());
    printf(" | Build date: ");
    print_packed_text_word(build_info_date0_read());
    print_packed_text_word(build_info_date1_read());
    print_packed_text_word(build_info_date2_read());
    print_packed_text_word(build_info_date3_read());
    print_packed_text_word(build_info_date4_read());
    printf("\n");
#endif
    printf("\n");
}

static void print_packed_text_word(unsigned int word)
{
    int i;
    for (i = 0; i < 4; i++) {
        char c = (char)((word >> (8 * i)) & 0xff);
        if (c == '\0') {
            break;
        }
        printf("%c", c);
    }
}

static void print_build_info(void)
{
#ifdef CSR_BUILD_INFO_BASE
    printf("Build clock: %lu Hz\n", get_build_clock_hz());
    printf("Build mode: ");
    print_packed_text_word(build_info_mode_read());
    printf("\n");
    printf("Build org: ");
    print_packed_text_word(build_info_org0_read());
    print_packed_text_word(build_info_org1_read());
    print_packed_text_word(build_info_org2_read());
    print_packed_text_word(build_info_org3_read());
    printf("\n");
    printf("Build date: ");
    print_packed_text_word(build_info_date0_read());
    print_packed_text_word(build_info_date1_read());
    print_packed_text_word(build_info_date2_read());
    print_packed_text_word(build_info_date3_read());
    print_packed_text_word(build_info_date4_read());
    printf("\n");
#endif
}

static int uart_char_available(void)
{
#ifdef CSR_UART_RXEMPTY_ADDR
    return uart_rxempty_read() == 0;
#else
    return 1;
#endif
}

static char uart_read_char_nowait(void)
{
    return (char)uart_rxtx_read();
}

static void wait_for_serial_banner_trigger(void)
{
    char c;

    while (!uart_char_available()) {
    }

    c = uart_read_char_nowait();
    if (c != '\r' && c != '\n') {
        while (uart_char_available()) {
            c = uart_read_char_nowait();
            if (c == '\r' || c == '\n') {
                break;
            }
        }
    }
}

static void led_toggle(void)
{
#ifdef CSR_LEDS_BASE
    static unsigned int state = 0;
    state ^= 1;
    leds_out_write(state);
#endif
}

/* ========================================================================= */
/* Exibe o Help completo                                                      */
/* ========================================================================= */

print_help(){
    printf("\nComandos disponíveis:\n");
    printf("  banner   — imprime ASCII art novamente\n");
    printf("  info     — informações do SoC\n");
    printf("  led      — alterna LED\n");
    printf("  run <r>  — executa predição neural (ruído <r>)\n");
    printf("             r: white, pink, brown/browian,\n");
    printf("                sine/near, chirp/blue/violet/grey\n");
    printf("  help     — esta mensagem\n");
    printf("  reboot   — reinicia o SoC\n");
    printf("\n");
}
/* ========================================================================= */
/* Prompt interativo                                                          */
/* ========================================================================= */

static void prompt_loop(void)
{
    char buf[128];

    print_help();

    while (1) {
        printf("LDS-RISCV> ");

        /* Ler linha da serial */
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

        /* Interpretar comando */
        if (strcmp(buf, "banner") == 0) {
            print_banner();
        } else if (strcmp(buf, "info") == 0) {
            printf("CPU:   VexRiscv RV32IM (standard)\n");
            printf("Clock: %lu MHz\n", get_build_clock_hz() / 1000000);
#ifdef CSR_BUILD_INFO_BASE
            {
                char desc[BOARD_DESC_BUF_SIZE];
                char bid[5] = {0};
                read_board_desc(desc, sizeof(desc));
                read_board_id(bid);
                printf("Board: %s (id=%s)\n",
                       desc[0] ? desc : "(desconhecida)",
                       bid[0] ? bid  : "?");
            }
#endif
            /* Relatório de memória: totais vindos do SoC, uso real extraído
             * dos símbolos do linker. Evita divergência com a imagem atual. */
            print_memory_usage("");
            printf("UART:  115200 bps\n");
            print_build_info();
        } else if (strcmp(buf, "led") == 0) {
            led_toggle();
            printf("LED alternado.\n");
        } else if (strncmp(buf, "run", 3) == 0 && (buf[3] == '\0' || buf[3] == ' ')) {
            const char *arg = (buf[3] == ' ') ? &buf[4] : "white";
            while (*arg == ' ') arg++;
            if (neural_run_by_name(arg) < 0) {
                printf("Ruído desconhecido: '%s'. Use white|pink|brown|sine|chirp.\n", arg);
            }
        } else if (strcmp(buf, "help") == 0) {
            print_help();
        } else if (strcmp(buf, "reboot") == 0) {
            ctrl_reset_write(1);
        } else if (i > 0) {
            printf("Comando desconhecido: '%s' (digite 'help')\n", buf);
        }
    }
}

/* ========================================================================= */
/* Main                                                                       */
/* ==========================================r=============================== */

int main(void)
{
#ifdef CONFIG_CPU_HAS_INTERRUPT
    irq_setmask(0);
    irq_setie(1);
#endif

    uart_init();

    wait_for_serial_banner_trigger();

    printf("\n\n");
    print_banner();
    neural_init();
    printf("Firmware inicializado. Digite 'help' para comandos.\n");

    prompt_loop();

    return 0;
}
