@echo off
REM 🚀 TensorFlow GUI - Script Principal Simplificado
REM Funciona de qualquer diretório na estrutura do projeto

echo 🚀 TensorFlow GUI - Visualização Interativa
echo 📊 Estudo de Redes Neurais com Dados Senoidais
echo.

REM Encontrar o diretório raiz do projeto TensorFlow-Lite-Test-Amostras-matematicas
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%"

REM Verificar se estamos no diretório scripts e ajustar conforme necessário
if exist "%SCRIPT_DIR%\TensorFlow_GUI_Simple.py" (
    REM O script está sendo executado do diretório scripts - PROJECT_ROOT é o diretório pai
    set "PROJECT_ROOT=%SCRIPT_DIR%.."
) else if exist "%SCRIPT_DIR%..\scripts\TensorFlow_GUI_Simple.py" (
    REM O script está sendo executado de um subdiretório, procurar o projeto
    set "PROJECT_ROOT=%SCRIPT_DIR%.."
) else (
    REM Procurar recursivamente pelo arquivo TensorFlow_GUI_Simple.py
    set "SEARCH_DIR=%SCRIPT_DIR%"
    :search_loop
    if exist "%SEARCH_DIR%\scripts\TensorFlow_GUI_Simple.py" (
        set "PROJECT_ROOT=%SEARCH_DIR%"
        goto found_project
    )
    if "%SEARCH_DIR%"=="%SEARCH_DIR%\.." (
        echo ❌ Erro: Projeto TensorFlow não encontrado na estrutura de diretórios
        pause
        exit /b 1
    )
    set "SEARCH_DIR=%SEARCH_DIR%\.."
    goto search_loop
    :found_project
)

REM Normalizar o caminho do projeto
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"

REM Mudar para diretório raiz do projeto
cd /d "%PROJECT_ROOT%"

echo 📁 Diretório do projeto: %CD%
echo.

REM Verificar ambiente virtual
if not exist "%PROJECT_ROOT%\venv\Scripts\activate.bat" (
    echo 📦 Configurando ambiente virtual...
    python -m venv "%PROJECT_ROOT%\venv"
    
    echo 🔄 Ativando ambiente virtual...
    call "%PROJECT_ROOT%\venv\Scripts\activate.bat"
    
    echo 📦 Instalando dependências...
    pip install --upgrade pip
    pip install -r "%PROJECT_ROOT%\scripts\requirements.txt"
) else (
    echo 🔄 Ativando ambiente virtual...
    call "%PROJECT_ROOT%\venv\Scripts\activate.bat"
    
    echo 📦 Verificando dependências...
    pip install -q -r "%PROJECT_ROOT%\scripts\requirements.txt"
)

REM Configurar variáveis de ambiente para TensorFlow
set TF_ENABLE_ONEDNN_OPTS=0
set TF_CPP_MIN_LOG_LEVEL=2

echo 🎯 Executando aplicação TensorFlow GUI...
echo.
python "%PROJECT_ROOT%\scripts\TensorFlow_GUI_Simple.py" %*

echo.
echo 👋 Aplicação finalizada
pause
