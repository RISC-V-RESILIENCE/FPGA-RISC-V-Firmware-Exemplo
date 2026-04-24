# 📡 Comunicação Serial - TensorFlow GUI

## 🎯 Visão Geral

A nova funcionalidade de comunicação serial permite monitorar e analisar dados de predição em tempo real vindos de microcontroladores (ESP32, STM32, etc.) que executam modelos TensorFlow Lite.

## 🔧 Funcionalidades Implementadas

### 1. 📦 Box de Comunicação Serial
- **Localização**: Entre o box de controle e o de informações do modelo
- **Controles**: Seleção de porta, baudrate, botões de conectar/desconectar
- **Visualização**: Área de exibição de dados recebidos em tempo real
- **Estatísticas**: Contador de predições, erro médio e erro máximo

### 2. 🔄 SerialReader (Thread)
- Leitura assíncrona de dados da porta serial
- Buffer circular para gerenciar fluxo de dados
- Extração automática de dados de predição usando regex
- Sinais PyQt para comunicação thread-safe

### 3. 📊 Gráficos Adicionais
- **Gráfico 7**: "Microcontrolador - Predições em Tempo Real"
  - Compara predições do MC vs valores reais
  - Atualização automática a cada 10 predições
- **Gráfico 8**: "Microcontrolador - Erro de Predição"
  - Mostra evolução do erro ao longo do tempo
  - Calcula e exibe erro médio

### 4. 🔍 Parsing de Logs
A classe reconhece múltiplos formatos de logs:
```
PREDICTION: x=1.57, y_pred=0.99, y_real=1.00, error=0.01
Prediction: input=1.57, output=0.99, expected=1.00, error=0.01
[2026-04-05 10:30:15] prediction: 1.57 -> 0.99 (expected: 1.00)
TFLite: input=1.57, output=0.99
```

## 🚀 Como Usar

### 1. Conectando ao Microcontrolador
1. Selecione a porta serial no dropdown (ex: COM3, /dev/ttyUSB0)
2. Escolha o baudrate (padrão: 115200)
3. Clique em "🔌 Conectar"
4. O status mudará para "Conectado" (verde)

### 2. Monitorando Dados
- **Dados Recebidos**: Área exibe os logs brutos do MC
- **Estatísticas**: Contadores atualizados automaticamente
- **Gráficos**: Visualização em tempo real das predições

### 3. Analisando Resultados
- **Gráfico 7**: Verifique precisão das predições vs valores reais
- **Gráfico 8**: Monitore evolução do erro ao longo do tempo
- **Estatísticas**: Acompanhe erro médio e máximo

### 4. Controles
- **🔄 Atualizar Portas**: Recarrega lista de portas disponíveis
- **🗑️ Limpar**: Limpa todos os dados e gráficos
- **🔌 Conectar/Desconectar**: Controla conexão serial

## 📝 Formato de Logs Esperado

Para melhor análise, o microcontrolador deve enviar logs no formato:
```c
printf("PREDICTION: x=%.3f, y_pred=%.3f, y_real=%.3f, error=%.3f\n", 
       input_value, predicted_value, expected_value, error);
```

## ⚙️ Configurações

### Buffer Sizes
- **Dados seriais**: 1000 linhas (circular)
- **Predições**: 500 pontos (gráficos)
- **Display**: 50 linhas (visíveis)

### Atualizações
- **Gráficos**: A cada 10 predições
- **Estatísticas**: Em tempo real
- **Display**: Imediato

## 🔧 Dependências

```python
import serial          # Comunicação serial
import threading       # Thread para leitura assíncrona
import re             # Expressões regulares para parsing
import json           # Manipulação de dados (futuro)
```

## 🐛 Troubleshooting

### Conexão Falha
- Verifique se a porta está correta
- Confirme o baudrate
- Certifique-se de que nenhum outro programa está usando a porta

### Dados Não Extraídos
- Verifique formato dos logs
- Confirme padrões regex na classe `SerialReader`
- Use área de "Dados Recebidos" para debug

### Gráficos Não Atualizam
- Verifique se dados de predição estão sendo extraídos
- Confirme se há pontos suficientes (mínimo 2)
- Limpe dados e tente novamente

## 🚀 Próximos Melhorias

- [ ] Suporte a múltiplos formatos de log
- [ ] Exportação de dados capturados
- [ ] Configuração de padrões regex via UI
- [ ] Gravação e reprodução de sessões
- [ ] Comparação com modelo local (PC vs MC)

---

**Resumo**: Esta funcionalidade permite análise completa de predições em tempo real de microcontroladores, facilitando debug e validação de modelos TinyML.
