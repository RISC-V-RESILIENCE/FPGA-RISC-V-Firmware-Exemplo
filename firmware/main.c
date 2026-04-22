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

#include <irq.h>
#include <libbase/uart.h>
#include <libbase/console.h>
#include <generated/csr.h>
#include <generated/soc.h>

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
    "  ||    Laboratorio de Desenvolvimento de Software                ||",
    "  ||                  Equipe RISC-V                               ||",
    "  ||                  IFCE -- iREDE                               ||",
    "  ||                                                              ||",
    "  ||  SoC: LiteX + VexRiscv (RV32IM)                              ||",
    "  ||  FPGA: ColorLight i5 (Lattice ECP5 LFE5U-25F)                ||",
    "  ||                                                              ||",
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

static void print_banner(void)
{
    const char **line = ascii_art;
    while (*line) {
        printf("%s\n", *line);
        line++;
    }
    printf("  Clock: %lu MHz | UART: 115200 bps\n", get_build_clock_hz() / 1000000);
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
/* Prompt interativo                                                          */
/* ========================================================================= */

static void prompt_loop(void)
{
    char buf[128];

    printf("\nComandos disponíveis:\n");
    printf("  banner   — imprime ASCII art novamente\n");
    printf("  info     — informações do SoC\n");
    printf("  led      — alterna LED\n");
    printf("  help     — esta mensagem\n");
    printf("  reboot   — reinicia o SoC\n");
    printf("\n");

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
            printf("ROM:   32 KiB\n");
            printf("SRAM:  8 KiB\n");
            printf("UART:  115200 bps\n");
            print_build_info();
        } else if (strcmp(buf, "led") == 0) {
            led_toggle();
            printf("LED alternado.\n");
        } else if (strcmp(buf, "help") == 0) {
            printf("  banner  info  led  help  reboot\n");
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
    printf("Firmware inicializado. Digite 'help' para comandos.\n");

    prompt_loop();

    return 0;
}
