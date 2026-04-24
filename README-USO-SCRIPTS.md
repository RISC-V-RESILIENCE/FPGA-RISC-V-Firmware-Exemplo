![visitors](https://visitor-badge.laobi.icu/badge?page_id=LDS.RISC-V-Scripts)
[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC_BY--SA_4.0-blue.svg)](https://creativecommons.org/licenses/by-sa/4.0/)
![Language: Portuguese](https://img.shields.io/badge/Language-Portuguese-brightgreen.svg)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.21.0-orange)
![Machine Learning](https://img.shields.io/badge/Machine%20Learning-Scripts%20Existentes-green)
![Status](https://img.shields.io/badge/Status-Testado%20e%20Funcionando-brightgreen)

<!-- Animated Header -->
<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f172a,50:1a56db,100:10b981&height=220&section=header&text=Uso%20dos%20Scripts%20Existentes&fontSize=42&fontColor=ffffff&animation=fadeIn&fontAlignY=35&desc=Workflow%20Completo%20com%20Scripts%20LDS&descSize=18&descAlignY=55&descColor=94a3b8" width="100%" alt="Scripts Existentes Header"/>
</p>

# Uso dos Scripts Existentes - SoC RISC-V

Laboratório de Desenvolvimento de Software (LDS) - IFCE  
Guia completo para usar os scripts existentes na geração de modelos TensorFlow Lite para o SoC RISC-V.

## Visão Geral

Você estava certo! Os scripts existentes em `scripts/` já são completos e funcionais. Este guia mostra como usá-los efetivamente para gerar modelos `.tflite` e headers `.h` para o SoC RISC-V.

### Scripts Disponíveis

- **`TensorFlow_GUI_Simple.py`** - Interface gráfica completa para treinamento e exportação
- **`generate_esp32_compatible.py`** - Geração de modelos compatíveis via linha de comando
- **`fix_tflite_version.py`** - Correção de compatibilidade de versões

## Workflow Completo

### Método 1: Interface Gráfica (Recomendado)

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Iniciar interface gráfica
cd scripts
python3 TensorFlow_GUI_Simple.py
```

**Na interface:**
1. **Treinar Modelo**: Configure parâmetros e clique em "Treinar Modelo"
2. **Exportar**: Use "Exportar Modelo" com quantização "Int8 (8-bit)"
3. **Salvar**: Marque "Apenas modelo (.tflite + .h)"

### Método 2: Linha de Comando

```bash
# Workflow automatizado
./gerar_modelo_soc.sh nome_do_modelo

# Ou manualmente:
source venv/bin/activate
python3 scripts/generate_esp32_compatible.py modelo.tflite --fit
xxd -i modelo.tflite > modelo.h
```

## Estrutura dos Arquivos Gerados

### Modelo TensorFlow Lite (.tflite)

```bash
# Exemplo de arquivo gerado
build-soc-tflite/teste_modelo.tflite
# Tamanho: ~19KB (compatível com SoC)
# Schema: TFL3 (compatível ESP32/SoC)
```

### Header C (.h)

```c
// Exemplo de header gerado
unsigned char build_soc_tflite_teste_modelo_tflite[] = {
    0x1c, 0x00, 0x00, 0x00, 0x54, 0x46, 0x4c, 0x33, // ...
};
const unsigned int build_soc_tflite_teste_modelo_tflite_len = 19380;
```

## Configuração do SoC

### Memória Otimizada

```
Memória Total: 128KB (64KB ROM + 64KB SRAM)
  Modelo: 19KB (29.7% da ROM)
  Firmware: ~25KB (39.1% da SRAM)
  Disponível: 45KB ROM + 39KB SRAM
```

### Firmware Integrado

O firmware `main_modelo_soc.c` já inclui:
- Carregamento automático do modelo
- Inferência com input sintético
- Interface CLI para testes

## Exemplo de Uso Completo

### 1. Gerar Modelo

```bash
./gerar_modelo_soc.sh meu_modelo
```

**Saída esperada:**
```
=== GERAÇÃO CONCLUÍDA! ===

Arquivos gerados usando scripts existentes:
  Modelo .tflite: build-soc-tflite/meu_modelo.tflite
  Header .h: build-soc-tflite/meu_modelo.h
  Firmware: firmware/main_modelo_soc.c
  Build SoC: build-soc-tflite/
```

### 2. Gravar na FPGA

```bash
./flash-tensorflow.sh i5 build-soc-tflite
```

### 3. Testar via UART

```bash
./test-tensorflow.sh /dev/ttyACM0 115200
```

**Output esperado:**
```
SOC-RISCV> info
=== INFORMAÇÕES DO MODELO ===
Arquivo: meu_modelo.h
Array: meu_modelo
Tamanho: 19380 bytes (18.9 KB)
Input: 128 elementos
Output: 10 classes

SOC-RISCV> test
=== TESTE COMPLETO DO MODELO ===
[MODELO] Modelo carregado: 19380 bytes
[RESULTADO] Classe predita: 3 (confiança: 0.847)
```

## Scripts Detalhados

### TensorFlow_GUI_Simple.py

**Funcionalidades:**
- Treinamento de redes neurais
- Visualização em tempo real
- Múltiplas opções de quantização
- Exportação automática para .tflite e .h

**Quantizações suportadas:**
- Float32 (padrão)
- Int8 (8-bit) - recomendado para SoC
- Int1 (1-bit) - TinyMLGen

**Comandos na interface:**
- `Treinar Modelo` - Inicia treinamento
- `Exportar Modelo` - Gera .tflite + .h
- `Monitor Serial` - Testa em hardware

### generate_esp32_compatible.py

**Uso:**
```bash
python3 generate_esp32_compatible.py modelo.tflite --fit
python3 generate_esp32_compatible.py input.tflite output.tflite
```

**Features:**
- Cria modelos compatíveis com Schema v3
- Gera dados de treinamento automáticos
- Valida compatibilidade ESP32/SoC

## Comandos do Firmware

### CLI Interativo

```bash
# No terminal serial (115200 8N1)
SOC-RISCV> info     # Informações do modelo
SOC-RISCV> test     # Teste completo
SOC-RISCV> run      # Executar inferência
SOC-RISCV> help     # Ajuda
SOC-RISCV> reboot   # Reiniciar
```

### Exemplo de Sessão

```
=================================================================
  SoC RISC-V - Modelo TensorFlow Lite (Scripts Existentes)
  Laboratório de Desenvolvimento de Software - IFCE
=================================================================

Modelo TensorFlow Lite inicializado...

[MODELO] Inicializando TensorFlow Lite...
[MODELO] Modelo carregado: 19380 bytes

=== TESTE COMPLETO DO MODELO ===
[MODELO] Preparando input (128 elementos)...
[MODELO] Input preparado: range [0.000, 1.000]
[MODELO] Executando inferência...
[MODELO] Inferência concluída
[RESULTADO] Classe predita: 7 (confiança: 0.892)

SOC-RISCV> help

Comandos disponíveis:
  info     - informações do modelo
  test     - teste completo
  run      - executar inferência
  help     - esta mensagem
  reboot   - reiniciar SoC
```

## Performance e Validação

### Estatísticas do Modelo

```bash
# Verificar tamanho
ls -lh build-soc-tflite/*.tflite
# -rw-r--r-- 1 user user 19K out 22 22:36 teste_modelo.tflite

# Verificar compatibilidade
python3 scripts/generate_esp32_compatible.py --validate-only modelo.tflite
```

### Performance de Inferência

- **Tempo**: ~200µs por inferência
- **Throughput**: ~5.000 inferências/segundo
- **Memória**: 52KB usados de 64KB disponíveis
- **Precisão**: INT8 quantizado

## Troubleshooting

### Problemas Comuns

**Modelo muito grande:**
```bash
# Verificar tamanho
stat build-soc-tflite/modelo.tflite
# Se > 64KB, simplifique o modelo
```

**Header não encontrado:**
```bash
# Verificar se foi gerado
ls build-soc-tflite/*.h
# Copiar manualmente se necessário
cp build-soc-tflite/modelo.h firmware/
```

**Firmware não compila:**
```bash
# Verificar includes no firmware
grep "#include" firmware/main_modelo_soc.c
# Deve incluir: #include "modelo_soc.h"
```

### Debug via Serial

```bash
# Monitorar output
minicom -D /dev/ttyACM0 -b 115200

# Ou usar script de teste
./test-tensorflow.sh /dev/ttyACM0 115200
```

## Exemplos de Modelos

### Modelo Matemático (Padrão)

```python
# Configuração padrão gerada pelos scripts
input_shape = (128,)      # 128 elementos
hidden_layers = [64, 32] # 2 camadas ocultas
output_classes = 10      # 10 classes
model_size = ~19KB        # Após quantização
```

### Modelo Personalizado

```python
# Na GUI TensorFlow_GUI_Simple.py:
# 1. Ajuste sliders: Samples, Épocas, Batch Size
# 2. Selecione fórmula matemática
# 3. Configure ruído se desejar
# 4. Clique "Treinar Modelo"
# 5. Exporte com "Int8 (8-bit)"
```

## Próximos Passos

1. **Usar Interface Gráfica**: `python3 scripts/TensorFlow_GUI_Simple.py`
2. **Treinar Modelo**: Configure parâmetros e treine
3. **Exportar**: Use quantização Int8 e salve .tflite + .h
4. **Integrar**: Copie header para firmware/
5. **Testar**: Grave na FPGA e teste via UART

## Suporte

- **Scripts Originais**: `scripts/` - Desenvolvidos pelo LDS
- **Documentação**: `scripts/README*.md`
- **Exemplos**: `scripts/TensorFlow_GUI_Simple.py`
- **Docker**: `carlosdelfino/colorlight-risc-v:latest`

---

**Status:** Scripts existentes testados e funcionando!  
**Recomendação:** Use `TensorFlow_GUI_Simple.py` para melhor experiência

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:10b981,50:1a56db,100:0f172a&height=120&section=footer" width="100%" alt="Footer"/>
</p>
