#!/bin/bash
##############################################################################
# flash-tensorflow.sh - Gravação do SoC RISC-V TensorFlow na ColorLight i5
# Laboratório de Desenvolvimento de Software (LDS) - IFCE
#
# Uso: ./flash-tensorflow.sh [board] [build_dir]
# Exemplo: ./flash-tensorflow.sh i5 build-tensorflow-final
##############################################################################

set -e

# Parâmetros padrão
BOARD=${1:-i5}
BUILD_DIR=${2:-build-test-tf}
DOCKER_IMAGE="carlosdelfino/colorlight-risc-v:latest"

echo "================================================================="
echo "  GRAVAÇÃO DO SoC RISC-V TENSORFLOW LITE"
echo "  Laboratório de Desenvolvimento de Software - IFCE"
echo "================================================================="
echo

# Verificar se o diretório de build existe
if [ ! -d "$BUILD_DIR" ]; then
    echo "ERRO: Diretório de build não encontrado: $BUILD_DIR"
    echo "Execute primeiro: python3 soc.py --board $BOARD --build"
    exit 1
fi

# Verificar se o bitstream foi gerado
BITSTREAM="$BUILD_DIR/gateware/colorlight_soc.bit"
if [ ! -f "$BITSTREAM" ]; then
    echo "ERRO: Bitstream não encontrado: $BITSTREAM"
    echo "Verifique se a síntese foi concluída com sucesso"
    exit 1
fi

echo "Configuração:"
echo "  Placa: ColorLight $BOARD"
echo "  Build: $BUILD_DIR"
echo "  Bitstream: $BITSTREAM"
echo "  Docker: $DOCKER_IMAGE"
echo

# Verificar permissões USB (necessário para gravação)
if [ ! -w "/dev/bus/usb" ]; then
    echo "AVISO: Sem permissão USB. Use:"
    echo "  sudo chmod -R 777 /dev/bus/usb"
    echo "  ou execute com: --privileged -v /dev/bus/usb:/dev/bus/usb"
fi

# Comando de gravação com openFPGALoader
FLASH_CMD="openFPGALoader --board colorlight-$BOARD $BITSTREAM"

echo "Comando de gravação:"
echo "  $FLASH_CMD"
echo

# Executar gravação no Docker
echo "Iniciando gravação..."
docker run --rm \
    --privileged \
    -v $(pwd):/workspace \
    -v /dev/bus/usb:/dev/bus/usb \
    -w /workspace \
    $DOCKER_IMAGE \
    $FLASH_CMD

echo
echo "================================================================="
echo "  GRAVAÇÃO CONCLUÍDA!"
echo "================================================================="
echo
echo "Para testar o firmware TensorFlow:"
echo "  1. Conecte a UART (115200 8N1)"
echo "  2. Pressione ENTER no terminal serial"
echo "  3. Aguarde o banner 'TensorFlow Lite Test'"
echo "  4. Digite 'help' para comandos disponíveis"
echo
echo "LED piscando indica que o SoC está rodando corretamente."
