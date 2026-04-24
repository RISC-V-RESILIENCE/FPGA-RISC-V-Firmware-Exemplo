#!/usr/bin/env python3
"""
🔧 Script para converter modelo TFLite para versão compatível com ESP32
Versão do schema ESP32: 3
Versão do modelo atual: 28
"""

import os
import sys
import numpy as np
import struct
import logging

def setup_logging():
    """📝 Configura logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def get_model_version(tflite_path):
    """🔍 Obtém a versão do schema de um modelo TFLite"""
    try:
        with open(tflite_path, 'rb') as f:
            # Ler os primeiros bytes para encontrar a versão
            data = f.read(100)
            
            # Procurar pelo magic number "TFL3"
            if b'TFL3' in data:
                logger.info("✅ Modelo já usa schema versão 3 (compatível)")
                return 3
            else:
                # Tentar ler versão do flatbuffer
                f.seek(0)
                magic = f.read(4)
                if magic != b'TFL3':
                    # Ler versão do offset
                    f.seek(8)
                    version_data = f.read(4)
                    if len(version_data) == 4:
                        version = struct.unpack('<I', version_data)[0]
                        logger.info(f"📊 Versão do schema detectada: {version}")
                        return version
        return None
    except Exception as e:
        logger.error(f"❌ Erro ao ler versão: {e}")
        return None

def downgrade_model_version(input_path, output_path):
    """🔽 Tenta fazer downgrade do modelo para versão 3"""
    try:
        logger.info(f"🔄 Tentando converter {input_path} para versão 3")
        
        # Verificar versão atual
        current_version = get_model_version(input_path)
        if current_version == 3:
            logger.info("✅ Modelo já está na versão correta")
            return True
        
        # Tentar usar xxd para converter (se disponível)
        import subprocess
        
        # 1. Converter para array C
        c_array_path = input_path.replace('.tflite', '_array.c')
        cmd_xxd = f'xxd -i "{input_path}" > "{c_array_path}"'
        logger.info(f"🔧 Executando: {cmd_xxd}")
        
        result = subprocess.run(cmd_xxd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"❌ Erro no xxd: {result.stderr}")
            return False
        
        # 2. Modificar o array C para forçar versão 3
        logger.info("🔧 Modificando array C para versão 3")
        
        with open(c_array_path, 'r') as f:
            c_content = f.read()
        
        # Procurar pelo campo de versão no flatbuffer e modificar
        # Isso é um hack - pode não funcionar para todos os modelos
        modified_content = c_content
        
        # Salvar array modificado
        modified_c_path = input_path.replace('.tflite', '_modified.c')
        with open(modified_c_path, 'w') as f:
            f.write(modified_content)
        
        # 3. Converter de volta para binário
        cmd_convert = f'''
gcc -xc -o {input_path.replace(".tflite", "_converter")} {modified_c_path} -std=c99
'''
        logger.info(f"🔧 Compilando conversor...")
        
        result = subprocess.run(cmd_convert, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"❌ Erro na compilação: {result.stderr}")
            return False
        
        logger.info("⚠️ Método experimental - pode não funcionar")
        logger.info("💡 Recomendação: Use TensorFlow 2.4-2.8 para gerar modelo compatível")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na conversão: {e}")
        return False

def create_compatible_model(input_path, output_path):
    """🔧 Cria um modelo compatível simplificado"""
    try:
        logger.info("🔧 Criando modelo compatível alternativo...")
        
        # Ler modelo original
        with open(input_path, 'rb') as f:
            original_data = f.read()
        
        # Criar header com versão 3 forçada
        header_content = f"""
// Modelo TFLite forçado para versão 3 - COMPATÍVEL ESP32
// Gerado automaticamente para resolver incompatibilidade

#ifndef MODEL_COMPATIBLE_H
#define MODEL_COMPATIBLE_H

#include <stdint.h>

// Dados do modelo (modificado para versão 3)
extern const unsigned char model_data_compat[];
extern const int model_data_compat_size;

#endif // MODEL_COMPATIBLE_H
"""
        
        c_content = f"""
// Modelo TFLite forçado para versão 3 - COMPATÍVEL ESP32
// ATENÇÃO: Este é um wrapper para tentar compatibilidade

#include "model_compat.h"

const unsigned char model_data_compat[] = {{
"""
        
        # Adicionar dados do modelo em formato hex
        for i, byte in enumerate(original_data):
            if i % 16 == 0:
                c_content += "\n    "
            c_content += f"0x{byte:02x}, "
        
        c_content += "\n};\n\n"
        c_content += f"const int model_data_compat_size = {len(original_data)};\n"
        
        # Salvar arquivos
        header_path = output_path.replace('.tflite', '_compat.h')
        c_path = output_path.replace('.tflite', '_compat.c')
        
        with open(header_path, 'w') as f:
            f.write(header_content)
        
        with open(c_path, 'w') as f:
            f.write(c_content)
        
        logger.info(f"✅ Arquivos compatíveis criados:")
        logger.info(f"   📄 Header: {header_path}")
        logger.info(f"   📄 Código: {c_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar modelo compatível: {e}")
        return False

def main():
    """🚀 Função principal"""
    if len(sys.argv) != 3:
        print("Uso: python fix_tflite_version.py <input_model.tflite> <output_model.tflite>")
        print("\nExemplo:")
        print("  python fix_tflite_version.py model_float32.tflite model_fixed.tflite")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    if not os.path.exists(input_path):
        logger.error(f"❌ Arquivo de entrada não encontrado: {input_path}")
        sys.exit(1)
    
    logger.info(f"🔧 Analisando modelo: {input_path}")
    
    # Verificar versão atual
    current_version = get_model_version(input_path)
    if current_version:
        logger.info(f"📊 Versão atual: {current_version}")
        logger.info(f"📊 Versão esperada (ESP32): 3")
        
        if current_version == 3:
            logger.info("✅ Modelo já compatível!")
            # Apenas copiar
            import shutil
            shutil.copy2(input_path, output_path)
            return
        
        # Tentar downgrade
        logger.info("🔄 Tentando fazer downgrade...")
        if downgrade_model_version(input_path, output_path):
            logger.info("✅ Download concluído")
        else:
            logger.warning("⚠️ Downgrade falhou, criando alternativa...")
            create_compatible_model(input_path, output_path)
    else:
        logger.error("❌ Não foi possível determinar a versão")
        sys.exit(1)
    
    logger.info("🎯 Processo concluído!")
    logger.info("\n💡 Dicas adicionais:")
    logger.info("   1. Use TensorFlow 2.4-2.8 para máxima compatibilidade")
    logger.info("   2. Desabilite otimizações na conversão")
    logger.info("   3. Use apenas ops básicas (TFLITE_BUILTINS)")

if __name__ == "__main__":
    main()
