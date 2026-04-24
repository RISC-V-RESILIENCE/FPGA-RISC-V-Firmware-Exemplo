![visitors](https://visitor-badge.laobi.icu/badge?page_id=ArvoreDosSaberes.TensorFlow-Lite-Test-Amostras-matematicas)
[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC_BY--SA_4.0-blue.svg)](https://creativecommons.org/licenses/by-sa/4.0/)
![Language: Portuguese](https://img.shields.io/badge/Language-Portuguese-brightgreen.svg)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange)
![Machine Learning](https://img.shields.io/badge/Machine%20Learning-Prática-green)
![Status](https://img.shields.io/badge/Status-Educa%C3%A7%C3%A3o-brightgreen)
![Repository Size](https://img.shields.io/github/repo-size/ArvoreDosSaberes/TensorFlow-Lite-Test-Amostras-matematicas)
![Last Commit](https://img.shields.io/github/last-commit/ArvoreDosSaberes/TensorFlow-Lite-Test-Amostras-matematicas)

# TensorFlow Senoidal - Visualização Interativa

## 📋 Descrição

Aplicação QT6 para visualização interativa do treinamento de redes neurais TensorFlow com dados senoidais. O sistema permite explorar como diferentes parâmetros afetam o treinamento através de uma interface gráfica intuitiva com gráficos em tempo real.

## 🏗️ Estrutura do Projeto

```
TensorFlow Lite Test - Amostra Senoidal/
├── 📁 bin/                     # Scripts de execução (Windows .bat)
│   ├── run_gui.bat            # Executar interface gráfica
│   ├── run_original.bat       # Executar script original
│   ├── test_app.bat           # Executar testes
│   └── setup_env.bat          # Configurar ambiente virtual
├── 📁 scripts/                 # Código Python
│   ├── TensorFlow_GUI_Simple.py # Interface gráfica principal
│   ├── GeradorAmostrasSenoidalis.py # Script original (referência)
│   └── requirements.txt       # Dependências Python
├── 📁 utils/                   # Utilitários Python
│   ├── project_utils.py       # Funções utilitárias do projeto
│   └── test_app.py           # Script de testes
├── 📁 logs/                    # Logs da aplicação (criado automaticamente)
├── 📁 venv/                    # Ambiente virtual Python (criado automaticamente)
├── start.bat                  # Menu principal do projeto
└── README.md                  # Este arquivo
```

## 🚀 Instalação e Execução

### ⚡ Execução Rápida (Recomendado)

```bash
# Executar menu principal
start.bat
```

O menu principal oferece:
- 🚀 Executar Interface Gráfica
- 📊 Executar Script Original  
- 🧪 Executar Testes
- 📦 Configurar Ambiente
- 📝 Ver Logs

### 🔧 Setup Inicial (Primeira vez)

```bash
# Configurar ambiente virtual automaticamente
bin\setup_env.bat

# Ou manualmente:
python -m venv venv
venv\Scripts\activate
pip install -r scripts\requirements.txt
```

### 📦 Execução Individual

**Interface Gráfica:**
```bash
bin\run_gui.bat
```

**Script Original:**
```bash
bin\run_original.bat
```

**Testes:**
```bash
bin\test_app.bat
```

**Via Python Utils:**
```bash
# Ativar venv primeiro
venv\Scripts\activate

# Executar via utilitário
python utils\project_utils.py gui
python utils\project_utils.py test
python utils\project_utils.py setup
```

## 🎮 Como Usar a Interface Gráfica

### 1. 🎛️ Controles do Modelo
- **Épocas (10-1000)**: Número de iterações de treinamento
- **Batch Size (4-128)**: Tamanho do lote para cada atualização
- **Fator de Ruído (0.00-0.50)**: Intensidade do ruído adicionado aos dados

### 2. 📊 Gráficos Disponíveis

#### Gráfico 1: Senoide Pura
- Mostra a função seno(x) original sem ruído
- Referência para comparar com os dados com ruído

#### Gráfico 2: Senoide com Ruído  
- Dados de treinamento com ruído gaussiano
- Simula dados reais do mundo

#### Gráfico 3: Conjuntos de Dados
- **Verde**: Dados de treinamento (60%)
- **Laranja**: Dados de validação (20%)  
- **Roxo**: Dados de teste (20%)

#### Gráfico 4: Loss Durante Treinamento
- **Azul**: Loss do conjunto de treinamento
- **Vermelho**: Loss do conjunto de validação
- Mostra convergência do modelo

#### Gráfico 5: MAE Durante Treinamento
- Mean Absolute Error para treinamento e validação
- Métrica alternativa para avaliar performance

#### Gráfico 6: Predições vs Dados Reais
- **Azul**: Valores reais de validação
- **Vermelho**: Predições do modelo
- Avaliação visual da qualidade do modelo

### 3. 🔄 Fluxo de Operação

1. **Gerar Dados**: Cria novo conjunto de dados senoidais com ruído
2. **Treinar Modelo**: Executa treinamento da rede neural com parâmetros atuais
3. **Fazer Predições**: Aplica modelo treinado nos dados de validação

### 4. 📝 Área de Informações
- Exibe arquitetura do modelo (model summary)
- Mostra métricas finais (loss, MAE)
- Logs detalhados do processo

## 🧠 Arquitetura do Modelo

```python
model = tf.keras.Sequential([
    tf.keras.layers.Dense(16, activation='relu', input_shape=(1,)),
    tf.keras.layers.Dense(16, activation='relu'), 
    tf.keras.layers.Dense(1)
])
```

- **Entrada**: Valor x (0 a 2π)
- **Camadas ocultas**: 16 neurônios cada com ativação ReLU
- **Saída**: Valor y previsto (seno(x))
- **Otimizador**: RMSprop
- **Loss**: Mean Squared Error (MSE)
- **Métricas**: Mean Absolute Error (MAE)

## 📈 Experimentos Sugeridos

### Experimento 1: Impacto do Ruído
1. Mantenha épocas=600, batch_size=16
2. Varie o fator de ruído: 0.05 → 0.10 → 0.20 → 0.30
3. Observe como o ruído afeta a convergência

### Experimento 2: Tamanho do Lote
1. Mantenha épocas=600, ruído=0.10
2. Varie batch_size: 4 → 16 → 32 → 64 → 128
3. Compare velocidade vs qualidade

### Experimento 3: Número de Épocas
1. Mantenha batch_size=16, ruído=0.10
2. Varie épocas: 100 → 300 → 600 → 1000
3. Identifique ponto de overfitting

## 🔍 Logs e Debug

Os logs são salvos automaticamente na pasta `logs/`:
- Nome: `tensorflow_gui_YYYYMMDD_HHMMSS.log`
- Contém: timestamps, função, linha, nível, mensagem
- Formato: `%(asctime)s - %(name)s - %(funcName)s:%(lineno)d - %(levelname)s - %(message)s`

## 📚 Conceitos Demonstrados

- 🎯 **Geração de Dados**: Funções senoidais com ruído gaussiano
- 🔄 **Divisão de Dados**: Treino/Validação/Teste (60/20/20)
- 🧠 **Redes Neurais**: Arquitetura feedforward com TensorFlow
- 📊 **Visualização**: Gráficos interativos com matplotlib
- 🎛️ **Controle Interativo**: Sliders para ajuste de hiperparâmetros
- 📈 **Métricas**: Loss e MAE para avaliação de modelo
- 🔮 **Predição**: Aplicação de modelo treinado

## 🛠️ Ambiente Virtual

O projeto usa sempre o ambiente virtual `venv/` para garantir consistência:

- **Isolamento**: Dependências isoladas do sistema
- **Reprodutibilidade**: Versões específicas garantidas
- **Portabilidade**: Funciona em qualquer máquina Windows
- **Automação**: Scripts ativam o venv automaticamente

## 🤝 Contribuições

Este projeto é educacional e demonstra conceitos fundamentais de machine learning com interface gráfica interativa.

---
**Resumo:** Aplicação QT6 para visualização interativa de treinamento TensorFlow com dados senoidais.
**Data de Criação:** 2025-10-15
