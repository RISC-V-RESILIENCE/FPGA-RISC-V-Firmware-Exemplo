![visitors](https://visitor-badge.laobi.icu/badge?page_id=RISC-V-RESILIENCE.RISC-V-Resilience-Workspace)
[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC_BY--SA_4.0-blue.svg)](https://creativecommons.org/licenses/by-sa/4.0/)
![Language: Portuguese](https://img.shields.io/badge/Language-Portuguese-brightgreen.svg)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange)
![Machine Learning](https://img.shields.io/badge/Machine%20Learning-Prática-green)
![Status](https://img.shields.io/badge/Status-Educa%C3%A7%C3%A3o-brightgreen)
![Repository Size](https://img.shields.io/github/repo-size/RISC-V-RESILIENCE/RISC-V-Resilience-Workspace)
![Last Commit](https://img.shields.io/github/last-commit/RISC-V-RESILIENCE/RISC-V-Resilience-Workspace)

<!-- Animated Header -->
<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f172a,50:1a56db,100:10b981&height=220&section=header&text=Scripts%20de%20Inicializa%C3%A7%C3%A3o&fontSize=42&fontColor=ffffff&animation=fadeIn&fontAlignY=35&desc=TensorFlow%20GUI%20-%20Multiplataforma&descSize=18&descAlignY=55&descColor=94a3b8" width="100%" alt="Scripts Header"/>
</p>

# Scripts de Inicialização TensorFlow GUI

Este diretório contém três scripts de inicialização para executar a aplicação TensorFlow GUI, cada um compatível com diferentes sistemas operacionais e shells.

## Scripts Disponíveis

### 1. start.bat (Windows CMD)
- **Sistema:** Windows
- **Shell:** Command Prompt (CMD)
- **Execução:** `start.bat`

### 2. start.ps1 (Windows PowerShell)
- **Sistema:** Windows
- **Shell:** PowerShell
- **Execução:** `.\start.ps1`

### 3. start.sh (Linux/macOS/Unix)
- **Sistema:** Linux, macOS, Unix
- **Shell:** Bash
- **Execução:** `./start.sh`

## Características Comuns

Todos os scripts possuem as mesmas funcionalidades:

### ✅ Detecção Automática do Projeto
- Identificam automaticamente o diretório raiz do projeto
- Funcionam de qualquer local na estrutura de diretórios
- Busca recursiva pelo arquivo `TensorFlow_GUI_Simple.py`

### ✅ Gestão de Ambiente Virtual
- Criam ambiente virtual automaticamente se não existir
- Instalam dependências do arquivo `requirements.txt`
- Ativam o ambiente virtual antes da execução

### ✅ Configuração do TensorFlow
- Configuram variáveis de ambiente para otimização
- Suprimem logs desnecessários
- Garantem execução estável

### ✅ Tratamento de Erros
- Mensagens claras em caso de falha
- Verificação de dependências
- Saída com códigos de erro apropriados

## Como Usar

### Windows (CMD)
```cmd
start.bat
```

### Windows (PowerShell)
```powershell
.\start.ps1
```

### Linux/macOS/Unix
```bash
./start.sh
```

## Estrutura de Diretórios Suportada

Os scripts funcionam independentemente de onde são executados:

```
TensorFlow-Lite-Test-Amostras-matematicas/
├── scripts/
│   ├── start.bat
│   ├── start.ps1
│   ├── start.sh
│   └── TensorFlow_GUI_Simple.py
├── venv/
└── requirements.txt
```

### Locais de Execução Suportados:

1. **Do diretório `scripts`:**
   ```bash
   cd scripts
   ./start.sh  # ou start.bat / start.ps1
   ```

2. **Do diretório raiz do projeto:**
   ```bash
   cd TensorFlow-Lite-Test-Amostras-matematicas
   scripts/start.sh
   ```

3. **De qualquer subdiretório:**
   ```bash
   cd TensorFlow-Lite-Test-Amostras-matematicas/subdir
   ../scripts/start.sh
   ```

4. **De fora da estrutura (busca recursiva):**
   ```bash
   cd /qualquer/diretorio
   /caminho/para/projeto/scripts/start.sh
   ```

## Requisitos do Sistema

### Windows
- Windows 10 ou superior
- Python 3.8+
- PowerShell 5.1+ (para script .ps1)

### Linux/macOS/Unix
- Python 3.8+
- Bash 4.0+
- pip

## Fluxo de Execução

1. 🚀 **Inicialização** - Exibe mensagem de boas-vindas
2. 📁 **Detecção do Projeto** - Encontra o diretório raiz automaticamente
3. 🔄 **Ambiente Virtual** - Verifica/cria/ativa o ambiente virtual
4. 📦 **Dependências** - Instala/verifica pacotes necessários
5. 🎯 **Execução** - Inicia a aplicação TensorFlow GUI
6. 👋 **Finalização** - Aguarda confirmação do usuário

## Variáveis de Ambiente Configuradas

- `TF_ENABLE_ONEDNN_OPTS=0` - Desabilita otimizações OneDNN
- `TF_CPP_MIN_LOG_LEVEL=2` - Reduz verbosidade de logs do TensorFlow

## Solução de Problemas

### Erro: "Projeto TensorFlow não encontrado"
- Verifique se o arquivo `TensorFlow_GUI_Simple.py` existe em `scripts/`
- Execute o script de dentro da estrutura do projeto

### Erro: "python: comando não encontrado"
- Instale Python 3.8+ e adicione ao PATH do sistema
- Use `python3` em vez de `python` se necessário

### Erro: Permissão negada (Linux/macOS)
```bash
chmod +x scripts/start.sh
```

### Erro: Política de execução do PowerShell
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:10b981,50:1a56db,100:0f172a&height=120&section=footer" width="100%" alt="Footer"/>
</p>

---
**Resumo:** Documentação completa para os três scripts de inicialização multiplataforma da aplicação TensorFlow GUI.
**Data de Criação:** 2025-04-04
**Autor:** Sistema de Documentação
**Versão:** 1.0
**Última Atualização:** 2025-04-04
**Atualizado por:** Sistema de Documentação
**Histórico de Alterações:**
- 2025-04-04 - Criado por Sistema de Documentação - Versão 1.0
