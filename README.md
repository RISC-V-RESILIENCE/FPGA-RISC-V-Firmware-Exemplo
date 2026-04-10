![visitors](https://visitor-badge.laobi.icu/badge?page_id=LDS-RISC-V.projeto-riscv-lds)
[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC_BY--SA_4.0-blue.svg)](https://creativecommons.org/licenses/by-sa/4.0/)
![Language: Portuguese](https://img.shields.io/badge/Language-Portuguese-brightgreen.svg)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![FPGA](https://img.shields.io/badge/FPGA-ECP5%20LFE5U--25F-blue)
![LiteX](https://img.shields.io/badge/LiteX-VexRiscv%20RV32IM-green)
![Status](https://img.shields.io/badge/Status-Desenvolvimento-brightgreen)
![Repository Size](https://img.shields.io/github/repo-size/LDS-RISC-V/projeto-riscv-lds)
![Last Commit](https://img.shields.io/github/last-commit/LDS-RISC-V/projeto-riscv-lds)

<!-- Animated Header -->

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f172a,50:1a56db,100:10b981&height=220&section=header&text=Projeto%20RISC-V%20LDS&fontSize=42&fontColor=ffffff&animation=fadeIn&fontAlignY=35&desc=SoC%20VexRiscv%20para%20ColorLight%20i5%20%E2%80%94%20Tutorial%20Completo&descSize=18&descAlignY=55&descColor=94a3b8" width="100%" alt="Projeto RISC-V LDS Header"/>
</p>

# Projeto RISC-V LDS — SoC VexRiscv para ColorLight i5

Este projeto implementa um System-on-Chip (SoC) RISC-V completo na placa ColorLight i5 (Lattice ECP5 LFE5U-25F) utilizando o framework LiteX e o soft-core VexRiscv. O firmware de exemplo imprime um banner ASCII art "RISC-V LDS" via UART e oferece um prompt interativo para controlar o LED e exibir informações do sistema. Toda a cadeia de ferramentas é open-source e roda dentro de um container Docker, garantindo reprodutibilidade total do ambiente.

## Estrutura do Projeto

```
projeto-riscv-lds/
├── soc.py              Definição do SoC (plataforma, CRG, CPU, periféricos)
├── Makefile            Build principal (gateware + firmware + flash)
├── firmware/
│   ├── main.c          Firmware C — ASCII art + prompt interativo
│   └── Makefile        Compilação do firmware com toolchain RISC-V
└── README.md           Este tutorial
```

Após o build, a pasta `build/` é criada com a seguinte estrutura:

```
build/
├── gateware/
│   ├── colorlight_soc.v          Verilog do SoC completo (~73 KB)
│   ├── colorlight_soc.ys         Script de síntese Yosys
│   ├── colorlight_soc.lpf        Constraints de pinos
│   ├── colorlight_soc.json       Netlist sintetizado (~15 MB)
│   ├── colorlight_soc.config     Place & route (nextpnr)
│   └── colorlight_soc.bit        Bitstream para gravação
└── software/
    └── include/generated/
        ├── csr.h                 Mapa de registradores CSR
        ├── soc.h                 Constantes do SoC
        ├── mem.h                 Mapa de memória
        └── variables.mak         Variáveis para Makefiles
```

## Arquitetura do SoC

```
                    ┌─────────────────────────────────────┐
                    │        ColorLight i5 (ECP5)         │
                    │                                     │
  25 MHz ──────────►│  CRG ──► clk_sys                    │
                    │            │                        │
                    │    ┌───────┴────────┐               │
                    │    │   VexRiscv     │               │
                    │    │   RV32IM       │               │
                    │    │   (standard)   │               │
                    │    └───────┬────────┘               │
                    │            │ Wishbone Bus            │
                    │    ┌───┬──┴──┬──────┬──────┐       │
                    │    │   │     │      │      │       │
                    │  ┌─┴┐┌─┴─┐┌──┴──┐┌──┴──┐┌─┴──┐   │
                    │  │ROM││SRAM││UART ││Timer││LED │   │
                    │  │32K││ 8K ││115.2││     ││    │   │
                    │  └──┘└────┘└──┬──┘└─────┘└──┬─┘   │
                    │               │              │      │
  Serial TX/RX ◄───┤───────────────┘              └──────┤──► LED
                    │                                     │
                    └─────────────────────────────────────┘
```

- **CPU**: VexRiscv RV32IM (variant `standard`), 25 MHz
- **ROM**: 32 KiB — firmware embutido, endereço `0x00000000`
- **SRAM**: 8 KiB — stack e heap, endereço `0x10000000`
- **UART**: 115200 bps, TX=pino J17, RX=pino H18
- **Timer**: temporizador de uso geral com interrupção
- **LED**: GPIO mapeado no pino U16 (LED onboard, active-low)
- **Clock**: 25 MHz no pino P3
- **Reset**: botão no pino K18 (com pull-up)
- **CSR**: registradores de controle em `0xF0000000`

## Pré-requisitos

Somente a imagem Docker `carlosdelfino/colorlight-risc-v` é necessária. Pode ser obtida do Docker Hub ou construída localmente:

```bash
# Obter do Docker Hub
docker pull carlosdelfino/colorlight-risc-v:latest

# Ou construir localmente
cd docker
./docker-manage.sh build
```

Para gravação na FPGA, a placa ColorLight i5 (Muse Lab) já inclui um programador **DAPLink CMSIS-DAP** acessível via USB. O bitstream é gravado via **OpenOCD** com o protocolo JTAG.

## Tutorial Passo a Passo

### Passo 1 — Iniciar o container

Para **compilação apenas** (sem acesso à FPGA):

```bash
docker run -it --rm \
    -v $(pwd):/home/developer/projeto \
    -w /home/developer/projeto/projeto-riscv-lds \
    carlosdelfino/colorlight-risc-v
```

Para **compilação + gravação na FPGA** (requer acesso USB ao DAPLink CMSIS-DAP):

```bash
docker run -it --rm \
    --privileged \
    -v /dev/bus/usb:/dev/bus/usb \
    --device=/dev/ttyACM0 \
    -v $(pwd):/home/developer/projeto \
    -w /home/developer/projeto/projeto-riscv-lds \
    carlosdelfino/colorlight-risc-v
```

O `--privileged` e `-v /dev/bus/usb:/dev/bus/usb` são necessários para que o OpenOCD acesse o programador JTAG (DAPLink) via USB/HID. O `--device=/dev/ttyACM0` é necessário para o terminal serial.

### Passo 2 — Verificar o ambiente

```bash
fpga-check
```

Todos os itens devem aparecer como `OK`. Se algum falhar, a imagem precisa ser reconstruída.

### Passo 3 — Gerar o SoC (apenas Verilog + headers)

```bash
python3 soc.py
```

Este comando gera o Verilog do SoC (`build/gateware/colorlight_soc.v`), os constraints de pinos (`.lpf`), o script de síntese (`.ys`) e os headers C para o firmware (`build/software/include/generated/`). Não executa a síntese — é útil para inspecionar o design ou compilar o firmware antes de sintetizar.

### Passo 4 — Compilar tudo (SoC + síntese + bitstream)

```bash
make gateware
```

Este comando executa a cadeia completa: geração de Verilog → síntese Yosys → place & route nextpnr-ecp5 → bitstream ecppack. O resultado final é `build/gateware/colorlight_soc.bit`.

O processo leva entre 2 e 10 minutos dependendo da máquina. Durante a síntese, o Yosys processa o VexRiscv (~15 MB de netlist), depois o nextpnr otimiza o roteamento para o FPGA ECP5, e por fim o ecppack gera o bitstream binário.

### Passo 5 — Compilar o firmware

```bash
make firmware
```

Este comando compila `firmware/main.c` usando o cross-compiler RISC-V (`riscv64-linux-gnu-gcc`) com os headers gerados no Passo 3. O resultado é `firmware/firmware.bin`.

Para embutir o firmware diretamente na ROM do SoC (sem necessidade de carregamento via serial), copie o binário para o diretório de build e reconstrua:

```bash
cp firmware/firmware.bin build/gateware/colorlight_soc_rom.init
make gateware
```

### Passo 6 — Gravar na FPGA

Conecte a ColorLight i5 via USB (o DAPLink CMSIS-DAP é detectado automaticamente). Primeiro, verifique a conexão JTAG:

```bash
make flash-detect
```

Se o scan chain retornar o IDCODE `0x41111043` (ECP5 LFE5U-25F), grave o bitstream:

```bash
make flash
```

Isso usa o **OpenOCD** com CMSIS-DAP para enviar o arquivo SVF via JTAG. Alternativa com `openFPGALoader` (requer versão com suporte hidapi):

```bash
make flash-openFPGALoader
```

**Nota:** Se o scan chain retornar "all ones", verifique que o módulo i5 está bem encaixado no conector SODIMM e que o LED vermelho de alimentação está aceso.

### Passo 7 — Conectar via serial

A UART do SoC está nos pinos J17 (TX) e H18 (RX) do módulo i5, acessíveis via SODIMM. Se a placa Muse Lab roteia a serial para o DAPLink, use:

```bash
make terminal
```

Ou diretamente:

```bash
litex_term /dev/ttyACM0 --speed 115200
```

Ao iniciar, o SoC imprime o banner ASCII art e apresenta o prompt interativo:

```
  ======================================================
  ||                                                  ||
  ||   ____  ___ ____   ____     __     __  _     ____||
  ||  |  _ \|_ _/ ___| / ___|    \ \   / / | |   |  _ \
  ||  | |_) || |\___ \| |   _____\ \ / /  | |   | | | |
  ||  |  _ < | | ___) | |__|_____|\   /   | |___| |_| |
  ||  |_| \_\___|____/ \____|      \_/    |_____|____/||
  ||                                                  ||
  ||          Laboratorio de Design de Sistemas       ||
  ||                  Equipe RISC-V                   ||
  ||                                                  ||
  ||  SoC: LiteX + VexRiscv (RV32IM)                 ||
  ||  FPGA: ColorLight i5 (Lattice ECP5 LFE5U-25F)   ||
  ||  Clock: 25 MHz | UART: 115200 bps               ||
  ||                                                  ||
  ======================================================

Firmware inicializado. Digite 'help' para comandos.

LDS-RISCV> help
  banner  info  led  help  reboot

LDS-RISCV>
```

### Passo 8 — Carregar firmware via serial (alternativo)

Ao invés de embutir o firmware na ROM, é possível carregá-lo dinamicamente via serial usando o BIOS do LiteX:

```bash
make load
```

Isso transfere `firmware/firmware.bin` pela serial e o executa na RAM do SoC. Este método é mais rápido durante o desenvolvimento, pois não requer recompilação do gateware.

## Como Escrever Novo Firmware

### Criando um novo arquivo C

Crie um arquivo `.c` na pasta `firmware/`. O ponto de entrada é a função `main()`. Os headers disponíveis são:

| Header                  | Conteúdo                                                          |
| ----------------------- | ------------------------------------------------------------------ |
| `<generated/csr.h>`   | Funções de acesso aos registradores CSR (UART, Timer, LED, etc.) |
| `<generated/mem.h>`   | Endereços de memória (ROM, SRAM, CSR base)                       |
| `<generated/soc.h>`   | Constantes do SoC (`CONFIG_CLOCK_FREQUENCY`, etc.)               |
| `<libbase/uart.h>`    | `uart_init()`, `uart_write()`, `uart_read()`                 |
| `<libbase/console.h>` | `readchar()`, `printf()`                                       |
| `<irq.h>`             | `irq_setmask()`, `irq_setie()`                                 |

### Exemplo: "Hello World" personalizado

```c
#include <stdio.h>
#include <libbase/uart.h>
#include <generated/csr.h>

int main(void)
{
    uart_init();
    printf("Ola do VexRiscv na ColorLight i5!\n");
    printf("Clock: %d MHz\n", CONFIG_CLOCK_FREQUENCY / 1000000);

    while (1) {
        /* Loop infinito — o SoC não tem sistema operacional */
    }
    return 0;
}
```

### Exemplo: Piscar LED

```c
#include <generated/csr.h>

static void delay(volatile unsigned int count)
{
    while (count--);
}

int main(void)
{
    while (1) {
        leds_out_write(1);
        delay(5000000);
        leds_out_write(0);
        delay(5000000);
    }
    return 0;
}
```

### Exemplo: Ler botão e enviar pela serial

```c
#include <stdio.h>
#include <libbase/uart.h>
#include <generated/csr.h>

int main(void)
{
    uart_init();
    unsigned int prev = 0;

    while (1) {
        /* Supondo um GPIO de entrada configurado no SoC */
        unsigned int curr = /* gpio_in_read() */ 0;
        if (curr != prev) {
            printf("GPIO mudou: %d -> %d\n", prev, curr);
            prev = curr;
        }
    }
    return 0;
}
```

### Compilar e testar

```bash
# 1. Compilar firmware
make firmware

# 2. Testar via serial (sem recompilar gateware)
make load

# 3. Ou embutir na ROM e regravar a FPGA
cp firmware/firmware.bin build/gateware/colorlight_soc_rom.init
make gateware
make flash
```

## Mapa de Memória

| Região | Endereço Início | Tamanho | Permissões                    |
| ------- | ----------------- | ------- | ------------------------------ |
| ROM     | `0x00000000`    | 32 KiB  | RX (read + execute)            |
| SRAM    | `0x10000000`    | 8 KiB   | RWX (read + write + execute)   |
| CSR     | `0xF0000000`    | 64 KiB  | RW (registradores de controle) |

## Registradores CSR Principais

| Periférico | CSR              | Função                      |
| ----------- | ---------------- | ----------------------------- |
| UART        | `uart_rxtx`    | Leitura/escrita de caractere  |
| UART        | `uart_txfull`  | 1 = buffer TX cheio, aguardar |
| UART        | `uart_rxempty` | 1 = nada recebido             |
| Timer       | `timer0_load`  | Valor inicial do contador     |
| Timer       | `timer0_value` | Valor atual do contador       |
| Timer       | `timer0_en`    | 1 = timer ativo               |
| LED         | `leds_out`     | Controle direto do LED        |
| Ctrl        | `ctrl_reset`   | 1 = reinicia o SoC            |

Todos os acessos são via funções geradas: `uart_rxtx_read()`, `uart_rxtx_write(val)`, `timer0_en_write(1)`, etc.

## Solução de Problemas

**Síntese falha com "VexRiscv module not found"**: O pacote `pythondata-cpu-vexriscv` não está instalado. Execute `pip3 install git+https://github.com/litex-hub/pythondata-cpu-vexriscv.git`.

**Erro "No default clock domain"**: O CRG não foi adicionado ao SoC. Verifique que `self.crg = _CRG(platform, sys_clk_freq)` está no `__init__` do `ColorLightSoC`.

**UART não funciona**: Verifique que a plataforma define os pinos `serial` (TX=J17 e RX=H18). O `SoCCore` adiciona UART automaticamente quando encontra esse recurso.

**"CPU not supported"**: O pacote `pythondata-cpu-vexriscv` está ausente ou corrompido. Reinstale com `pip3 install --force-reinstall git+https://github.com/litex-hub/pythondata-cpu-vexriscv.git`.

**Firmware não cabe na ROM**: A ROM tem 32 KiB. Se o firmware exceder esse tamanho, aumente `integrated_rom_size` no `soc.py` (por exemplo, `0x10000` para 64 KiB).

**JTAG retorna "all ones"**: O FPGA não está respondendo. Verifique: (1) módulo i5 bem encaixado no SODIMM, (2) LED vermelho de alimentação aceso, (3) cabo USB conectado.

**"cmsis-dap not found" no openFPGALoader**: O binário do OSS CAD Suite não inclui suporte hidapi. Use `make flash` (que utiliza OpenOCD) em vez de `make flash-openFPGALoader`.

**Permissão negada no JTAG (hidraw)**: O container Docker precisa de `--privileged -v /dev/bus/usb:/dev/bus/usb` para acessar o DAPLink via USB/HID.

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:10b981,50:1a56db,100:0f172a&height=120&section=footer" width="100%" alt="Footer"/>
</p>

---

**Resumo:** Este tutorial documenta o projeto de SoC RISC-V (LiteX + VexRiscv) para a placa ColorLight i5, incluindo geração de gateware, compilação de firmware C, gravação na FPGA e desenvolvimento de novas aplicações bare-metal.
**Data de Criação:** 2025-10-15
