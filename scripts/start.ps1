# 🚀 TensorFlow GUI - Script Principal Simplificado (PowerShell)
# Funciona de qualquer diretório na estrutura do projeto

Write-Host "🚀 TensorFlow GUI - Visualização Interativa"
Write-Host "📊 Estudo de Redes Neurais com Dados Senoidais"
Write-Host ""

# Encontrar o diretório raiz do projeto TensorFlow-Lite-Test-Amostras-matematicas
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = $ScriptDir

# Verificar se estamos no diretório scripts e ajustar conforme necessário
if (Test-Path "$ScriptDir\TensorFlow_GUI_Simple.py") {
    # O script está sendo executado do diretório scripts - PROJECT_ROOT é o diretório pai
    $ProjectRoot = Split-Path -Parent $ScriptDir
}
elseif (Test-Path "$ScriptDir\..\scripts\TensorFlow_GUI_Simple.py") {
    # O script está sendo executado de um subdiretório, procurar o projeto
    $ProjectRoot = Split-Path -Parent $ScriptDir
}
else {
    # Procurar recursivamente pelo arquivo TensorFlow_GUI_Simple.py
    $SearchDir = $ScriptDir
    while ($SearchDir -ne $null) {
        if (Test-Path "$SearchDir\scripts\TensorFlow_GUI_Simple.py") {
            $ProjectRoot = $SearchDir
            break
        }
        $SearchDir = Split-Path -Parent $SearchDir
    }
    
    if ($SearchDir -eq $null) {
        Write-Host "❌ Erro: Projeto TensorFlow não encontrado na estrutura de diretórios" -ForegroundColor Red
        Read-Host "Pressione Enter para sair"
        exit 1
    }
}

# Normalizar o caminho do projeto
$ProjectRoot = (Get-Item $ProjectRoot).FullName

# Mudar para diretório raiz do projeto
Set-Location $ProjectRoot

Write-Host "📁 Diretório do projeto: $PWD"
Write-Host ""

# Verificar ambiente virtual
if (-not (Test-Path "$ProjectRoot\venv\Scripts\Activate.ps1")) {
    Write-Host "📦 Configurando ambiente virtual..."
    python -m venv "$ProjectRoot\venv"
    
    Write-Host "🔄 Ativando ambiente virtual..."
    & "$ProjectRoot\venv\Scripts\Activate.ps1"
    
    Write-Host "📦 Instalando dependências..."
    pip install --upgrade pip
    pip install -r "$ProjectRoot\scripts\requirements.txt"
}
else {
    Write-Host "🔄 Ativando ambiente virtual..."
    & "$ProjectRoot\venv\Scripts\Activate.ps1"
    
    Write-Host "📦 Verificando dependências..."
    pip install -q -r "$ProjectRoot\scripts\requirements.txt"
}

# Configurar variáveis de ambiente para TensorFlow
$env:TF_ENABLE_ONEDNN_OPTS = "0"
$env:TF_CPP_MIN_LOG_LEVEL = "2"

Write-Host "🎯 Executando aplicação TensorFlow GUI..."
Write-Host ""
python "$ProjectRoot\scripts\TensorFlow_GUI_Simple.py" $args

Write-Host ""
Write-Host "👋 Aplicação finalizada"
Read-Host "Pressione Enter para continuar"
