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

/* ========================================================================= */
/* ASCII Art                                                                  */
/* ========================================================================= */
static const char *ascii_art[] = {
    "",
    "  ======================================================",
    "  ||                                                  ||",
    "  ||   ____  ___ ____   ____     __     __  _         ||",
    "  ||  |  _ \\|_ _/ ___| / ___|    \\ \\   / /         ||",
    "  ||  | |_) || |\\___ \\| |   _____\\ \\ / /          ||",
    "  ||  |  _ < | | ___) | |__|_____|\\   /              ||",
    "  ||  |_| \\_\\___|____/ \\____|      \\_/            ||",
    "  ||                                                  ||",
    "  ||    Laboratorio de Desenvolvimento de Software    ||",
    "  ||                  Equipe RISC-V                   ||",
    "  ||                  IFCE -- iREDE                   ||",
    "  ||                                                  ||",
    "  ||  SoC: LiteX + VexRiscv (RV32IM)                  ||",
    "  ||  FPGA: ColorLight i5 (Lattice ECP5 LFE5U-25F)    ||",
    "  ||  Clock: 25 MHz | UART: 115200 bps                ||",
    "  ||                                                  ||",
    "  ======================================================",
    "",
    NULL,
};

/* ========================================================================= */
/* Funções auxiliares                                                         */
/* ========================================================================= */

static void print_banner(void)
{
    const char **line = ascii_art;
    while (*line) {
        printf("%s\n", *line);
        line++;
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
            printf("Clock: %d MHz\n", CONFIG_CLOCK_FREQUENCY / 1000000);
            printf("ROM:   32 KiB\n");
            printf("SRAM:  8 KiB\n");
            printf("UART:  115200 bps\n");
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

    printf("\n\n");
    print_banner();
    printf("Firmware inicializado. Digite 'help' para comandos.\n");

    prompt_loop();

    return 0;
}
