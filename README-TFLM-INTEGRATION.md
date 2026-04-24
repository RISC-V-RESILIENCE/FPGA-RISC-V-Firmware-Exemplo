![visitors](https://visitor-badge.laobi.icu/badge?page_id=LDS.RISC-V-TFLM)
[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC_BY--SA_4.0-blue.svg)](https://creativecommons.org/licenses/by-sa/4.0/)
![Language: Portuguese](https://img.shields.io/badge/Language-Portuguese-brightgreen.svg)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.21.0-orange)
![Machine Learning](https://img.shields.io/badge/Machine%20Learning-TFLite%20Micro-green)
![Status](https://img.shields.io/badge/Status-Pronto%20para%20Uso-brightgreen)

<!-- Animated Header -->
<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f172a,50:1a56db,100:10b981&height=220&section=header&text=TensorFlow%20Lite%20Micro%20Integration&fontSize=42&fontColor=ffffff&animation=fadeIn&fontAlignY=35&desc=SoC%20RISC-V%20com%20TFLM%20Quantizado&descSize=18&descAlignY=55&descColor=94a3b8" width="100%" alt="TFLM Integration Header"/>
</p>

# TensorFlow Lite Micro Integration - SoC RISC-V

Laboratório de Desenvolvimento de Software (LDS) - IFCE  
Guia completo para integração de modelos TensorFlow Lite Micro com quantização de 8 bits no SoC RISC-V otimizado.

## Visão Geral

Este projeto agora suporta integração completa com TensorFlow Lite Micro, permitindo executar modelos de Machine Learning quantizados em 8 bits no SoC RISC-V com memória otimizada.

### Características

- **TensorFlow Lite Micro**: Framework completo para inferência em edge devices
- **Quantização 8-bit**: INT8 para otimização de memória e performance
- **Workflow Automatizado**: Scripts para conversão .tflite -> .h
- **Memória Otimizada**: 64KB ROM + 64KB SRAM
- **Validação Automática**: Verificação de compatibilidade com SoC

## Estrutura do Projeto

```
projeto-riscv-lds-memory-tf/
    tensorflow-lite-micro/          # TFLM source code
    convert_tflite_to_header.py     # Conversor .tflite -> .h
    quantize_model.py               # Quantização 8-bit
    integrate_tflite_model.sh       # Workflow completo
    firmware/
        tensorflow_lite_micro.c     # Firmware TFLM
        model_data.h               # Header gerado (modelo)
    build-tflm-integrated/         # Build com TFLM
```

## Pré-requisitos

### Ambiente Python
```bash
# Ativar ambiente virtual
source venv/bin/activate

# Verificar instalação
python --version  # Python 3.12.3+
pip list | grep tensorflow  # TensorFlow 2.21.0+
```

### Dependências
```bash
pip install tensorflow flatbuffers numpy
```

### Docker
```bash
# Imagem Docker com toolchain LiteX
docker pull carlosdelfino/colorlight-risc-v:latest
```

## Workflow de Integração

### Passo 1: Fornecer Modelo .tflite

Quando você tiver o modelo .tflite pronto, use:

```bash
./integrate_tflite_model.sh seu_modelo.tflite nome_do_modelo
```

### Passo 2: Processamento Automático

O script executará automaticamente:

1. **Validação do Modelo**
   - Verifica tamanho máximo (64KB)
   - Valida compatibilidade com SoC
   - Analisa inputs/outputs

2. **Quantização 8-bit**
   - Aplica quantização INT8
   - Gera dataset representativo
   - Otimiza para inferência

3. **Conversão para Header**
   - Transforma .tflite em .h
   - Gera arrays C/C++
   - Inclui metadata

4. **Integração no Firmware**
   - Atualiza firmware TFLM
   - Compila com novo modelo
   - Gera bitstream final

## Exemplo de Uso

### Convertendo um Modelo

```bash
# Exemplo com modelo matemático
./integrate_tflite_model.sh math_model.tflite math_classifier

# Exemplo com modelo de imagem
./integrate_tflite_model.sh image_classifier.tflite img_model
```

### Saída Esperada

```
=== INTEGRAÇÃO TENSORFLOW LITE CONCLUÍDA! ===

Arquivos gerados:
  Modelo quantizado: math_classifier_quantized.tflite
  Header do modelo: math_classifier_data.h
  Firmware TFLM: firmware/main.c
  Firmware binário: build-tflm-integrated/software/bios/bios.bin
  Build SoC: build-tflm-integrated/

Tamanhos:
  Modelo quantizado: 12,456 bytes
  Firmware: 24,892 bytes
  Header: 12,656 bytes
```

## Firmware TensorFlow Lite Micro

### Funcionalidades

O firmware `tensorflow_lite_micro.c` oferece:

- **Inicialização TFLM**: Setup completo do framework
- **Quantização/Dequantização**: Conversão INT8 <-> Float
- **Inferência**: Execução de modelos otimizados
- **CLI Interativo**: Comandos para teste e debug

### Comandos Disponíveis

```bash
# No terminal serial (115200 8N1)
TFLM-RISCV> info     # Informações do modelo e sistema
TFLM-RISCV> test     # Teste completo de inferência
TFLM-RISCV> run      # Inferência com input aleatório
TFLM-RISCV> help     # Lista de comandos
TFLM-RISCV> reboot   # Reiniciar SoC
```

### Exemplo de Output

```
=== TensorFlow Lite Micro - SoC RISC-V ===
CPU: VexRiscv RV32IM @ 50MHz
Memória: 64KB ROM + 64KB SRAM
Framework: TensorFlow Lite Micro
Quantização: INT8 (8-bit)

Informações do Modelo:
Tamanho: 12456 bytes (12.2 KB)
Tensor Arena: 40960 bytes
Uso total: 53416 bytes (52.2 KB)

Configuração de Quantização:
  Input: scale=0.003922, zero_point=0
  Output: scale=0.003922, zero_point=0

[RESULTADO] Classe predita: 3 (confiança: 0.847)
```

## Scripts de Conversão

### convert_tflite_to_header.py

Converte modelos .tflite para headers C/C++:

```bash
python3 convert_tflite_to_header.py modelo.tflite modelo.h
python3 convert_tflite_to_header.py --quantize-8bit modelo.tflite modelo.h
```

**Features:**
- Quantização automática 8-bit
- Validação de tamanho
- Geração de metadata
- Arrays C otimizados

### quantize_model.py

Aplica quantização INT8 em modelos:

```bash
python3 quantize_model.py input.tflite output.tflite
python3 quantize_model.py --representative-data data.npy model.tflite
```

**Features:**
- Quantização pós-treinamento
- Dataset representativo automático
- Validação de compatibilidade
- Otimização para edge devices

## Memória e Performance

### Uso de Memória

| Componente | Tamanho | % SRAM |
|------------|---------|--------|
| Modelo TFLM | ~12KB | 18.8% |
| Tensor Arena | 40KB | 62.5% |
| Firmware | ~25KB | 39.1% |
| **Total** | **~52KB** | **81.3%** |

### Performance Estimada

| Métrica | Valor | Observação |
|---------|-------|------------|
| Inferência | ~200µs | Modelo 12KB |
| Throughput | ~5,000 inf/s | @ 50MHz |
| Precisão | INT8 | 8-bit quantizado |
| Memória | 52KB | < 64KB SRAM |

## Troubleshooting

### Erros Comuns

**Modelo muito grande:**
```
ERRO: Modelo muito grande para o SoC!
Reduza para menos de 65,536 bytes
```
- Solução: Simplifique modelo ou use pruning

**Falha na quantização:**
```
ERRO na quantização: Unsupported ops
```
- Solução: Verifique se as operações são suportadas pelo TFLM

**Firmware não compila:**
```
ERRO: model_data.h não encontrado
```
- Solução: Execute o workflow completo de integração

### Debug via Serial

```bash
# Monitorar output do firmware
./test-tensorflow.sh /dev/ttyACM0 115200

# Verificar comandos disponíveis
echo "help" > /dev/ttyACM0
```

## Modelos Suportados

### Operações TFLM

- **Dense/Fully Connected**: Camadas densas
- **Conv2D**: Convoluções 2D (limitado)
- **Reshape**: Reformatação de tensors
- **Quantize/Dequantize**: Conversões de tipo
- **Add/Mul**: Operações aritméticas

### Limitações

- **Tamanho máximo**: 64KB (incluindo tensor arena)
- **Input/Output**: Preferencialmente 1D ou 2D pequenos
- **Quantização**: Apenas INT8 suportado
- **Ops**: Subset limitado do TensorFlow

## Exemplos de Modelos

### Modelo Matemático (Recomendado)

```python
# Exemplo: Classificador de padrões matemáticos
input_shape = (128,)  # 128 elementos
output_classes = 10    # 10 classes
model_size = ~12KB     # Após quantização
```

### Modelo Simples de Imagem

```python
# Exemplo: Classificador MNIST simplificado
input_shape = (8, 8, 1)  # 8x8 grayscale
output_classes = 10      # Dígitos 0-9
model_size = ~15KB       # Após quantização
```

## Próximos Passos

1. **Fornecer Modelo**: Entregue seu arquivo .tflite
2. **Executar Workflow**: Use `./integrate_tflite_model.sh`
3. **Testar Firmware**: Grave na FPGA e teste via UART
4. **Otimizar**: Ajuste modelo conforme necessário

## Suporte

- **Laboratório**: Laboratório de Desenvolvimento de Software (LDS)
- **Instituição**: Instituto Federal do Ceará (IFCE)
- **Docker**: `carlosdelfino/colorlight-risc-v:latest`

---

**Status:** Pronto para receber modelo .tflite  
**Próxima Ação:** Aguardando seu arquivo .tflite para integração completa

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:10b981,50:1a56db,100:0f172a&height=120&section=footer" width="100%" alt="Footer"/>
</p>
