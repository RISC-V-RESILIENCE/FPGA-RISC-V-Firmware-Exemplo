#!/bin/bash
# 🚀 TensorFlow GUI - Script Principal Simplificado (Bash)
# Funciona de qualquer diretório na estrutura do projeto

echo "🚀 TensorFlow GUI - Visualização Interativa"
echo "📊 Estudo de Redes Neurais com Dados Senoidais"
echo

# Encontrar o diretório raiz do projeto TensorFlow-Lite-Test-Amostras-matematicas
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Verificar se estamos no diretório scripts e ajustar conforme necessário
if [[ -f "$SCRIPT_DIR/TensorFlow_GUI_Simple.py" ]]; then
    # O script está sendo executado do diretório scripts - PROJECT_ROOT é o diretório pai
    PROJECT_ROOT="$SCRIPT_DIR/.."
elif [[ -f "$SCRIPT_DIR/../scripts/TensorFlow_GUI_Simple.py" ]]; then
    # O script está sendo executado de um subdiretório, procurar o projeto
    PROJECT_ROOT="$SCRIPT_DIR/.."
else
    # Procurar recursivamente pelo arquivo TensorFlow_GUI_Simple.py
    SEARCH_DIR="$SCRIPT_DIR"
    while [[ "$SEARCH_DIR" != "/" ]]; do
        if [[ -f "$SEARCH_DIR/scripts/TensorFlow_GUI_Simple.py" ]]; then
            PROJECT_ROOT="$SEARCH_DIR"
            break
        fi
        SEARCH_DIR="$(dirname "$SEARCH_DIR")"
    done
    
    if [[ "$SEARCH_DIR" == "/" ]]; then
        echo "❌ Erro: Projeto TensorFlow não encontrado na estrutura de diretórios"
        exit 1
    fi
fi

# Normalizar o caminho do projeto
PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd)"

# Mudar para diretório raiz do projeto
cd "$PROJECT_ROOT"

echo "📁 Diretório do projeto: $PWD"
echo

# Verificar ambiente virtual
if [[ ! -f "$PROJECT_ROOT/venv/bin/activate" ]]; then
    echo "📦 Configurando ambiente virtual..."
    python3 -m venv "$PROJECT_ROOT/venv"
    
    echo "🔄 Ativando ambiente virtual..."
    source "$PROJECT_ROOT/venv/bin/activate"
    
    echo "📦 Instalando dependências..."
    pip install --upgrade pip
    pip install -r "$PROJECT_ROOT/scripts/requirements.txt"
else
    echo "🔄 Ativando ambiente virtual..."
    source "$PROJECT_ROOT/venv/bin/activate"
    
    echo "📦 Verificando dependências..."
    pip install -q -r "$PROJECT_ROOT/scripts/requirements.txt"
fi

# Configurar variáveis de ambiente para TensorFlow
export TF_ENABLE_ONEDNN_OPTS=0
export TF_CPP_MIN_LOG_LEVEL=2

# ─────────────────────────────────────────────────────────────────────────────
# 📡 Multiplexador serial — compartilha /dev/ttyACM0 entre GUI e PuTTY
#
# No Linux, dois processos lendo o mesmo /dev/ttyACM0 brigam pelos bytes
# (não há broadcast nativo por TTY). O script scripts/serial_mux.py abre a
# UART real uma única vez e expõe duas PTYs espelhadas:
#
#   /tmp/ttyGUI   — read-only  → selecione esta no dropdown do GUI
#   /tmp/ttyPUTTY — read/write → aponte o PuTTY/minicom para esta
#
# Ajuste via ambiente: SERIAL_MUX_SRC, SERIAL_MUX_BAUD, SERIAL_MUX_DISABLE=1.
# ─────────────────────────────────────────────────────────────────────────────
SERIAL_MUX_SRC="${SERIAL_MUX_SRC:-/dev/ttyACM0}"
SERIAL_MUX_BAUD="${SERIAL_MUX_BAUD:-115200}"
SERIAL_MUX_LINK_GUI="${SERIAL_MUX_LINK_GUI:-/tmp/ttyGUI}"
SERIAL_MUX_LINK_PUTTY="${SERIAL_MUX_LINK_PUTTY:-/tmp/ttyPUTTY}"
export SERIAL_MUX_SRC SERIAL_MUX_BAUD SERIAL_MUX_LINK_GUI SERIAL_MUX_LINK_PUTTY

SERIAL_MUX_PID=""
cleanup_serial_mux() {
    if [[ -n "$SERIAL_MUX_PID" ]] && kill -0 "$SERIAL_MUX_PID" 2>/dev/null; then
        echo "📡 Encerrando multiplexador serial (PID=$SERIAL_MUX_PID)"
        kill -TERM "$SERIAL_MUX_PID" 2>/dev/null || true
        wait "$SERIAL_MUX_PID" 2>/dev/null || true
    fi
    rm -f "$SERIAL_MUX_LINK_GUI" "$SERIAL_MUX_LINK_PUTTY" 2>/dev/null || true
}
trap cleanup_serial_mux EXIT INT TERM

if [[ "${SERIAL_MUX_DISABLE:-0}" != "1" ]]; then
    if [[ -e "$SERIAL_MUX_SRC" ]]; then
        if [[ ! -r "$SERIAL_MUX_SRC" || ! -w "$SERIAL_MUX_SRC" ]]; then
            echo "⚠️  Sem permissão rw em $SERIAL_MUX_SRC"
            echo "    Adicione seu usuário ao grupo 'dialout':"
            echo "      sudo usermod -aG dialout \$USER && newgrp dialout"
        fi
        echo "📡 Iniciando multiplexador serial em $SERIAL_MUX_SRC @ $SERIAL_MUX_BAUD bps"
        python "$PROJECT_ROOT/scripts/serial_mux.py" \
            --src "$SERIAL_MUX_SRC" \
            --baud "$SERIAL_MUX_BAUD" \
            --gui "$SERIAL_MUX_LINK_GUI" \
            --putty "$SERIAL_MUX_LINK_PUTTY" &
        SERIAL_MUX_PID=$!

        # Espera curta até os symlinks aparecerem (até ~3s).
        for _ in 1 2 3 4 5 6; do
            if [[ -e "$SERIAL_MUX_LINK_GUI" && -e "$SERIAL_MUX_LINK_PUTTY" ]]; then
                break
            fi
            sleep 0.5
        done

        if kill -0 "$SERIAL_MUX_PID" 2>/dev/null && \
           [[ -e "$SERIAL_MUX_LINK_GUI" && -e "$SERIAL_MUX_LINK_PUTTY" ]]; then
            echo "   ✅ GUI   (ro) : $SERIAL_MUX_LINK_GUI"
            echo "   ✅ PuTTY (rw) : $SERIAL_MUX_LINK_PUTTY"
            echo "   ➜ No GUI, selecione $SERIAL_MUX_LINK_GUI (ou digite o caminho)."
            echo "   ➜ No PuTTY, configure Serial line = $SERIAL_MUX_LINK_PUTTY"
        else
            echo "❌ Falha ao iniciar o multiplexador (veja logs/serial_mux.log)"
            SERIAL_MUX_PID=""
        fi
    else
        echo "ℹ️  $SERIAL_MUX_SRC não encontrado — multiplexador desativado."
        echo "    Conecte a placa ou defina SERIAL_MUX_SRC para outra porta."
    fi
else
    echo "ℹ️  Multiplexador serial desativado (SERIAL_MUX_DISABLE=1)."
fi
echo

echo "🎯 Executando aplicação TensorFlow GUI..."
echo
python "$PROJECT_ROOT/scripts/TensorFlow_GUI_Simple.py" "$@"

echo
echo "👋 Aplicação finalizada"
cleanup_serial_mux
read -p "Pressione Enter para continuar..."
