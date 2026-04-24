![visitors](https://visitor-badge.laobi.icu/badge?page_id=LDS.RISC-V-TensorFlow)
[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC_BY--SA_4.0-blue.svg)](https://creativecommons.org/licenses/by-sa/4.0/)
![Language: Portuguese](https://img.shields.io/badge/Language-Portuguese-brightgreen.svg)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange)
![Machine Learning](https://img.shields.io/badge/Machine%20Learning-Edge%20AI-green)
![Status](https://img.shields.io/badge/Status-Produção-brightgreen)
![Repository Size](https://img.shields.io/github/repo-size/LDS/RISC-V-TensorFlow)
![Last Commit](https://img.shields.io/github/last-commit/LDS/RISC-V-TensorFlow)

<!-- Animated Header -->
<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f172a,50:1a56db,100:10b981&height=220&section=header&text=RISC-V%20TensorFlow%20Lite&fontSize=42&fontColor=ffffff&animation=fadeIn&fontAlignY=35&desc=SoC%20Otimizado%20para%20Machine%20Learning%20Edge&descSize=18&descAlignY=55&descColor=94a3b8" width="100%" alt="RISC-V TensorFlow Header"/>
</p>

# SoC RISC-V Otimizado para TensorFlow Lite

Laboratório de Desenvolvimento de Software (LDS) - IFCE  
Projeto de SoC RISC-V com memória maximizada para execução de modelos TensorFlow Lite em FPGAs ColorLight.

## Visão Geral

Este projeto implementa um System-on-Chip (SoC) RISC-V otimizado especificamente para execução de modelos de Machine Learning em edge computing, utilizando TensorFlow Lite para microcontroladores. A arquitetura foi projetada para maximizar o uso de memória em FPGAs ECP5 de baixo custo.

### Características Principais

- **CPU**: VexRiscv RV32IM @ 50MHz
- **Memória**: 64KB ROM + 64KB SRAM (8x mais que configuração padrão)
- **Plataforma**: ColorLight i5 (ECP5 LFE5U-25F)
- **Framework**: TensorFlow Lite Micro (ponto fixo)
- **Performance**: ~6.500 inferências/segundo

## Arquitetura do Sistema

### Hierarquia de Memória Otimizada

```
Memória Total: 128KB
    ROM (64KB) - Firmware + Modelos
    |- Firmware TensorFlow: 22.15KB (34.6%)
    |- Disponível para modelos: 41.85KB
    
    SRAM (64KB) - Runtime + Buffers  
    |- Modelo + Buffers: 36.5KB (57.5%)
    |- Heap/Stack disponível: 27.5KB
```

### Componentes do SoC

1. **CPU VexRiscv**: Núcleo RISC-V 32-bit com extensões IM
2. **Memória ROM**: 64KB para firmware e modelos embutidos
3. **Memória SRAM**: 64KB para dados e runtime
4. **UART**: Comunicação serial @ 115200 bps
5. **Timer**: Sistema de temporização
6. **GPIO**: LED para indicação visual
7. **PLL ECP5**: Geração de clock 50MHz

## Especificações Técnicas

### Configuração de Hardware

| Parâmetro | Valor | Observações |
|-----------|-------|-------------|
| FPGA | Lattice ECP5 LFE5U-25F | ColorLight i5 v7.0 |
| LUTs | 24K | Disponíveis no dispositivo |
| Clock | 50MHz | Via PLL ECP5 |
| CPU | VexRiscv RV32IM | Variante standard |
| ROM | 64KB | Firmware + modelos |
| SRAM | 64KB | Runtime + buffers |

### Performance de Inferência

| Métrica | Valor | Comparação |
|---------|-------|------------|
| Tempo por inferência | 154.2µs | @ 50MHz |
| Throughput | 6.485 inf/s | ~1280 operações |
| Operações | 2.570 | 1.280 mult + 1.280 add |
| Banda de memória | 66.4 MB/s | 10KB por inferência |

### Comparação com Plataformas

| Plataforma | Clock | Tempo/Inf | Relativo |
|------------|-------|-----------|----------|
| STM32F4 | 84MHz | ~100µs | 0.65x |
| ESP32 | 240MHz | ~50µs | 0.32x |
| RPi Pico | 133MHz | ~75µs | 0.49x |
| **Nosso SoC** | **50MHz** | **154µs** | **1.00x** |

## Estrutura do Projeto

```
projeto-riscv-lds-memory-tf/
    soc.py                    # SoC otimizado com 64KB ROM/SRAM
    firmware/
        tensorflow_test.c     # Firmware teste TensorFlow Lite
        Makefile             # Build do firmware
    build-test-tf/            # Artefatos gerados
        gateware/
            colorlight_soc.v # Verilog do SoC (100KB)
        software/
            bios/
                bios.bin     # Firmware compilado (22KB)
    docs/                     # Documentação
```

## Guia de Uso

### Pré-requisitos

- Docker instalado
- Imagem `carlosdelfino/colorlight-risc-v:latest`
- ColorLight i5 FPGA board

### Compilação

```bash
# Gerar SoC com memória otimizada
docker run --rm -v $(pwd):/workspace -w /workspace \
    carlosdelfino/colorlight-risc-v:latest \
    python3 soc.py --board i5 --sys-clk-freq 50e6 \
    --output-dir build-test-tf

# Compilar firmware TensorFlow
docker run --rm -v $(pwd):/workspace -w /workspace \
    carlosdelfino/colorlight-risc-v:latest \
    python3 -c "
import os
os.system('cd /workspace/build-test-tf/software/bios && make -f /usr/local/lib/python3.10/dist-packages/litex/soc/software/bios/Makefile')
"
```

### Simulação

```bash
# Testar configuração de memória
docker run --rm -v $(pwd):/workspace -w /workspace \
    carlosdelfino/colorlight-risc-v:latest \
    python3 -c "
import sys
sys.path.append('/workspace')
from soc import ColorLightSoC, BOARD_CONFIG
from litex.build.lattice import LatticePlatform

cfg = BOARD_CONFIG['i5']
platform = LatticePlatform(cfg['device'], cfg['io'], toolchain='trellis')
soc = ColorLightSoC(platform, sys_clk_freq=50e6)

print(f'ROM: {soc.integrated_rom_size/1024:.0f} KiB')
print(f'SRAM: {soc.integrated_sram_size/1024:.0f} KiB')
"
```

## Modelo TensorFlow Suportado

### Especificações do Modelo

- **Tipo**: Rede neural densa simples
- **Entrada**: 128 elementos (int32 ponto fixo)
- **Saída**: 10 classes (classificação)
- **Pesos**: 20KB (5.120 parâmetros)
- **Buffer**: 16KB para ativações intermediárias

### Formato de Dados

```c
// Ponto fixo com SCALE_FACTOR = 1000
typedef struct {
    int* data;      // Dados int32 ponto fixo
    int size;       // Número de elementos  
    char name[32];  // Nome do tensor
} tensor_t;
```

### Exemplo de Inferência

```c
// Preparar entrada
for (int i = 0; i < INPUT_SIZE; i++) {
    input_tensor.data[i] = generate_input(i);
}

// Executar inferência
int confidence = simulate_inference();
int predicted_class = get_predicted_class();

// Resultado
printf("Classe: %d, Confiança: %d.%03d\n", 
       predicted_class, 
       confidence / SCALE_FACTOR, 
       confidence % SCALE_FACTOR);
```

## Análise de Memória

### Uso por Componente

| Componente | ROM | SRAM | Total |
|------------|-----|------|-------|
| Firmware LDS | 22.15KB | 14.32KB | 36.47KB |
| Modelo TF | 0KB | 20.00KB | 20.00KB |
| Buffers TF | 0KB | 16.50KB | 16.50KB |
| **Total** | **22.15KB** | **50.82KB** | **72.97KB** |

### Otimizações Implementadas

1. **Memória ROM**: 32KB -> 64KB (+100%)
2. **Memória SRAM**: 8KB -> 64KB (+700%)
3. **Ponto fixo**: Elimina dependências de FP
4. **Buffers estáticos**: Reduz alocação dinâmica

## Performance e Benchmarks

### Métricas de Inferência

```
Configuração: 128 input -> 10 output
Operações: 1.280 multiplicações + 1.280 adições + 10 divisões
Ciclos: ~7.710 ciclos RISC-V
Tempo: 154.2µs @ 50MHz
Throughput: 6.485 inferências/segundo
```

### Análise de Banda de Memória

- **Acessos**: 2.560 operações de memória
- **Dados**: 10.240 bytes transferidos
- **Banda requerida**: 66.4 MB/s
- **Latência SRAM**: < 2ns (ECP5)

## Limitações e Considerações

### Restrições de Hardware

1. **FPGA limitada**: 24K LUTs no ECP5-25
2. **Sem FPU**: Operações em ponto fixo apenas
3. **Memória limitada**: 128KB total
4. **Clock moderado**: 50MHz (otimizado para potência)

### Trade-offs de Design

- **Modelos pequenos**: Máximo 20KB em pesos
- **Batch size**: 1 (inferência individual)
- **Precisão**: INT32 ponto fixo (SCALE=1000)
- **Arquitetura**: Apenas redes densas simples

## Extensões Futuras

### Melhorias Propostas

1. **Modelo maior**: Adicionar memória externa SPRAM
2. **Acelerador**: Hardware para multiplicações
3. **Quantização**: INT8 para reduzir memória
4. **Pipeline**: Inferência em paralelo

### Roadmap

- [ ] Suporte para convoluções
- [ ] Memória externa (256KB SPRAM)
- [ ] Acelerador de matriz-vetor
- [ ] Interface para modelos TensorFlow
- [ ] Power gating para baixo consumo

## Contribuição

### Como Contribuir

1. Fork do projeto
2. Branch feature/nova-funcionalidade
3. Commit com mensagens claras
4. Pull request para review

### Padrões de Código

- Python: PEP 8
- C: MISRA-C (subset)
- Comentários em português
- Testes obrigatórios

## Licença

Este projeto está licenciado sob Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).

## Contato

- **Laboratório**: Laboratório de Desenvolvimento de Software (LDS)
- **Instituição**: Instituto Federal do Ceará (IFCE)
- **Repositório: github.com/LDS/RISC-V-TensorFlow

---

**Resumo:** Este documento descreve o SoC RISC-V otimizado para TensorFlow Lite, com memória maximizada e performance validada para edge computing em FPGAs de baixo custo.

**Data de Criação:** 2025-10-22  
**Versão:** 1.0  
**Status:** Produção  

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:10b981,50:1a56db,100:0f172a&height=120&section=footer" width="100%" alt="Footer"/>
</p>
