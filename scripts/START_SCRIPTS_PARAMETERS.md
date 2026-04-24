# Uso dos Scripts Start com Parâmetros

## Descrição
Os scripts `start.sh`, `start.ps1` e `start.bat` foram modificados para repassar todos os parâmetros recebidos para o aplicativo TensorFlow GUI.

## Sintaxe

### Linux/macOS (Bash)
```bash
./scripts/start.sh [parâmetros...]
```

### Windows (PowerShell)
```powershell
.\scripts\start.ps1 [parâmetros...]
```

### Windows (Batch)
```cmd
scripts\start.bat [parâmetros...]
```

## Exemplos de Uso

### 1. Ajuda do Aplicativo
```bash
# Linux/macOS
./scripts/start.sh --help

# Windows PowerShell
.\scripts\start.ps1 --help

# Windows Batch
scripts\start.bat --help
```

### 2. Modo Debug
```bash
# Linux/macOS
./scripts/start.sh --debug --verbose

# Windows PowerShell
.\scripts\start.ps1 --debug --verbose

# Windows Batch
scripts\start.bat --debug --verbose
```

### 3. Configuração Customizada
```bash
# Linux/macOS
./scripts/start.sh --config custom_config.json --port 8080

# Windows PowerShell
.\scripts\start.ps1 --config custom_config.json --port 8080

# Windows Batch
scripts\start.bat --config custom_config.json --port 8080
```

## Parâmetros Suportados

Os scripts repassam todos os parâmetros diretamente para o `TensorFlow_GUI_Simple.py`. 
Consulte a ajuda do aplicativo para ver todos os parâmetros disponíveis:

```bash
./scripts/start.sh --help
```

## Funcionalidades Mantidas

- ✅ **Detecção automática do projeto**: Funciona de qualquer diretório
- ✅ **Ambiente virtual**: Configuração e ativação automáticas
- ✅ **Dependências**: Instalação e verificação automáticas
- ✅ **Variáveis de ambiente**: Configuração do TensorFlow
- ✅ **Repasso de parâmetros**: Todos os argumentos são repassados

## Notas Técnicas

### Bash (start.sh)
- Usa `"$@"` para repassar todos os parâmetros preservando espaços e aspas
- Mantém compatibilidade com parâmetros complexos

### PowerShell (start.ps1)
- Usa `$args` para repassar todos os parâmetros
- Preserva a estrutura de argumentos do PowerShell

### Batch (start.bat)
- Usa `%*` para repassar todos os parâmetros
- Mantém compatibilidade com a sintaxe batch tradicional

## Exemplo Completo

```bash
# Executar com configuração customizada e modo debug
./scripts/start.sh --config meu_config.json --debug --verbose --log-level debug

# Isso será executado como:
# python /path/to/project/scripts/TensorFlow_GUI_Simple.py --config meu_config.json --debug --verbose --log-level debug
```

## Resumo

Agora todos os scripts de inicialização suportam o repasse completo de parâmetros, permitindo personalização total da execução do aplicativo TensorFlow GUI mantendo todas as funcionalidades de configuração automática do ambiente.
