#!/bin/bash
##############################################################################
# test-tensorflow.sh - Teste do SoC RISC-V TensorFlow via UART
# Laboratório de Desenvolvimento de Software (LDS) - IFCE
#
# Uso: ./test-tensorflow.sh [serial_port] [baud_rate]
# Exemplo: ./test-tensorflow.sh /dev/ttyUSB0 115200
##############################################################################

set -e

# Parâmetros padrão
SERIAL_PORT=${1:-/dev/ttyACM0}
BAUD_RATE=${2:-115200}
TIMEOUT=10

echo "================================================================="
echo "  TESTE DO SoC RISC-V TENSORFLOW LITE VIA UART"
echo "  Laboratório de Desenvolvimento de Software - IFCE"
echo "================================================================="
echo

echo "Configuração:"
echo "  Porta serial: $SERIAL_PORT"
echo "  Baud rate: $BAUD_RATE"
echo "  Timeout: $TIMEOUT segundos"
echo

# Verificar se a porta serial existe
if [ ! -c "$SERIAL_PORT" ]; then
    echo "ERRO: Porta serial não encontrada: $SERIAL_PORT"
    echo "Portas disponíveis:"
    ls -la /dev/tty* | grep -E "(ttyUSB|ttyACM)" || echo "  Nenhuma porta USB encontrada"
    echo
    echo "Soluções:"
    echo "  1. Conectar a ColorLight i5 via USB"
    echo "  2. Verificar permissões: sudo chmod 666 $SERIAL_PORT"
    echo "  3. Usar porta correta: /dev/ttyUSB0 ou /dev/ttyACM0"
    exit 1
fi

# Verificar permissões
if [ ! -w "$SERIAL_PORT" ]; then
    echo "AVISO: Sem permissão de escrita em $SERIAL_PORT"
    echo "Execute: sudo chmod 666 $SERIAL_PORT"
    echo
fi

# Função para enviar comando e esperar resposta
send_command() {
    local cmd="$1"
    local expected="$2"
    local timeout="$3"
    
    echo "Enviando: $cmd"
    echo "$cmd" > "$SERIAL_PORT"
    
    if [ -n "$expected" ]; then
        echo "Aguardando resposta: $expected"
        timeout "$timeout" grep -q "$expected" < "$SERIAL_PORT" && echo "OK: Resposta recebida" || echo "TIMEOUT: Sem resposta"
    fi
    echo
}

# Testar comunicação
echo "Testando comunicação serial..."

# Iniciar monitoramento em background
timeout "$TIMEOUT" cat "$SERIAL_PORT" &
CAT_PID=$!

# Aguardar um pouco para o firmware inicializar
sleep 2

# Enviar ENTER para ativar o prompt
send_command "" "LDS-RISCV>" 5

# Enviar comandos de teste
echo "=== TESTE DE COMANDOS TENSORFLOW ==="

send_command "banner" "TensorFlow Lite Test" 5
send_command "info" "ROM: 64 KiB" 5
send_command "info" "SRAM: 64 KiB" 5
send_command "help" "banner  info  led  help  reboot" 5

echo "=== TESTE DE INFERÊNCIA ==="
echo "A inferência é executada automaticamente na inicialização."
echo "Verifique o output anterior para:"
echo "  - 'TensorFlow Lite Test'"
echo "  - 'Classe predita: X (confiança: X.XXX)'"
echo "  - '10 inferências executadas'"
echo

# Testar LED
send_command "led" "LED alternado" 3

# Finalizar
echo "=== FINALIZANDO TESTE ==="
send_command "reboot" "" 2

# Matar processo cat
kill $CAT_PID 2>/dev/null || true

echo
echo "================================================================="
echo "  TESTE CONCLUÍDO!"
echo "================================================================="
echo
echo "Resultados esperados:"
echo "  [OK] Comunicação serial funcionando"
echo "  [OK] Firmware TensorFlow respondendo"
echo "  [OK] Memória de 64KB detectada"
echo "  [OK] Inferência executando"
echo "  [OK] LED respondendo"
echo
echo "Se algum teste falhou:"
echo "  1. Verifique se o FPGA foi gravado corretamente"
echo "  2. Confirme a conexão serial"
echo "  3. Reset o hardware (botão na ColorLight i5)"
