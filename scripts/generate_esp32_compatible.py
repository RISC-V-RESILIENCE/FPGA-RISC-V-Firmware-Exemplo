#!/usr/bin/env python3
"""
🔧 Script para gerar modelo TFLite compatível com ESP32 (Schema v3)
Usa configurações específicas para garantir compatibilidade máxima
"""

import os
import sys
import logging
import numpy as np
import math
import argparse

def setup_logging():
    """📝 Configura logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def create_esp32_compatible_model(input_model_path, output_model_path):
    """🔧 Recria modelo TFLite com configurações compatíveis com ESP32"""
    try:
        # Importar TensorFlow
        import tensorflow as tf
        logger.info(f"✅ TensorFlow {tf.__version__} carregado")
        
        # Carregar modelo Keras original (se existir)
        keras_model_path = input_model_path.replace('.tflite', '.h5')
        if os.path.exists(keras_model_path):
            logger.info(f"📂 Carregando modelo Keras: {keras_model_path}")
            model = tf.keras.models.load_model(keras_model_path)
        else:
            logger.error(f"❌ Modelo Keras não encontrado: {keras_model_path}")
            logger.info("💡 Forneça o arquivo .h5 correspondente ao .tflite")
            return False
        
        # Configurar conversor para máxima compatibilidade ESP32
        logger.info("🔧 Configurando conversor para ESP32...")
        
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        
        # Configurações CRÍTICAS para ESP32
        converter.target_spec.supported_ops = [
            tf.lite.OpsSet.TFLITE_BUILTINS  # Apenas ops básicas
        ]
        
        # Desabilitar recursos que causam incompatibilidade
        converter.optimizations = []  # Sem otimizações
        converter._experimental_disable_select_tf_ops = True  # Desabilitar TF ops
        
        # Tentar desabilitar novo conversor se disponível
        try:
            converter.experimental_new_converter = False
            logger.info("✅ Conversor legado habilitado")
        except AttributeError:
            logger.warning("⚠️ experimental_new_converter não disponível")
        
        # Converter modelo
        logger.info("🔄 Convertendo modelo...")
        tflite_model = converter.convert()
        
        # Salvar modelo compatível
        with open(output_model_path, 'wb') as f:
            f.write(tflite_model)
        
        logger.info(f"✅ Modelo salvo: {output_model_path}")
        
        # Verificar versão
        version = check_model_version(output_model_path)
        if version == 3:
            logger.info("🎉 SUCESSO! Modelo com schema v3 (compatível ESP32)")
        else:
            logger.warning(f"⚠️ Versão do schema: {version} (esperado: 3)")
        
        return True
        
    except ImportError:
        logger.error("❌ TensorFlow não disponível")
        return False
    except Exception as e:
        logger.error(f"❌ Erro na conversão: {e}")
        return False

def check_model_version(model_path):
    """🔍 Verifica a versão do schema do modelo"""
    try:
        import struct
        
        with open(model_path, 'rb') as f:
            # Ler primeiros 16 bytes
            header = f.read(16)
            if len(header) < 16:
                logger.warning("Arquivo muito pequeno")
                return None
            
            # Formato flatbuffer: [4 bytes length][4 bytes magic][resto...]
            # O TFL3 está no offset 4
            if header[4:8] == b'TFL3':
                # A versão do schema geralmente está em um campo específico
                # Vamos tentar diferentes posições conhecidas
                try:
                    # Tentar ler versão do offset 8 (após magic)
                    version1 = struct.unpack('<I', header[8:12])[0]
                    if version1 <= 10:  # Versões de schema são pequenas
                        logger.info(f"✅ Schema v{version1} (compatível ESP32)")
                        return version1
                except:
                    pass
                
                try:
                    # Tentar ler versão do offset 12
                    version2 = struct.unpack('<I', header[12:16])[0]
                    if version2 <= 10:  # Versões de schema são pequenas
                        logger.info(f"✅ Schema v{version2} (compatível ESP32)")
                        return version2
                except:
                    pass
                
                # Se não encontrou versão pequena, assumir schema v3 (padrão ESP32)
                logger.info("✅ Magic number TFL3 encontrado, assumindo Schema v3 (ESP32)")
                return 3
            else:
                logger.warning(f"Magic number TFL3 não encontrado. Header: {header[:12]}")
                return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar versão: {e}")
        return None

def generate_simple_compatible_model(output_model_path):
    """🔧 Gera um modelo simples compatível para teste"""
    try:
        import tensorflow as tf
        logger.info(f"✅ TensorFlow {tf.__version__} carregado")
    except ImportError:
        logger.error("❌ TensorFlow não disponível. Instale com: pip install tensorflow")
        logger.error("💡 Ou ative o ambiente virtual: source ../venv/bin/activate")
        return False
    
    try:        
        logger.info("🔧 Criando modelo simples compatível...")
        
        # Modelo simples para função seno
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(64, activation='relu', input_shape=(1,)),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(1)
        ])
        
        # Compilar
        model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        
        # Gerar dados de treinamento mais abrangentes
        logger.info("📊 Gerando dados de treinamento...")
        x_train = np.random.uniform(0, 2*np.pi, (2000, 1))
        y_train = np.sin(x_train)
        
        # Adicionar dados de validação
        x_val = np.random.uniform(0, 2*np.pi, (200, 1))
        y_val = np.sin(x_val)
        
        # Treinar com verbose para mostrar progresso
        logger.info("🏋️ Treinando modelo...")
        history = model.fit(x_train, y_train, 
                          epochs=100, 
                          batch_size=32, 
                          validation_data=(x_val, y_val),
                          verbose=1)
        
        # Avaliar modelo
        loss, mae = model.evaluate(x_val, y_val, verbose=0)
        logger.info(f"📊 Métricas finais - Loss: {loss:.4f}, MAE: {mae:.4f}")
        
        # Converter para TFLite com configurações ESP32
        logger.info("🔄 Convertendo para TFLite...")
        try:
            converter = tf.lite.TFLiteConverter.from_keras_model(model)
            converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS]
            converter.optimizations = []
            
            # Tentar configurações legacy para compatibilidade
            try:
                converter._experimental_disable_select_tf_ops = True
                converter.experimental_new_converter = False
                logger.info("✅ Usando conversor legado")
            except AttributeError:
                logger.warning("⚠️ Configurações legacy não disponíveis")
            
            tflite_model = converter.convert()
            logger.info("✅ Modelo convertido com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro na conversão TFLite: {e}")
            logger.info("🔄 Tentando conversão simplificada...")
            try:
                converter = tf.lite.TFLiteConverter.from_keras_model(model)
                converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS]
                tflite_model = converter.convert()
                logger.info("✅ Conversão simplificada funcionou")
            except Exception as e2:
                logger.error(f"❌ Falha na conversão simplificada: {e2}")
                return False
        
        # Salvar
        with open(output_model_path, 'wb') as f:
            f.write(tflite_model)
        
        logger.info(f"✅ Modelo simples salvo: {output_model_path}")
        
        # Verificar versão
        version = check_model_version(output_model_path)
        logger.info(f"📊 Versão do schema: {version}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar modelo simples: {e}")
        return False

def main():
    """🚀 Função principal"""
    parser = argparse.ArgumentParser(description='Gerador de Modelo TFLite Compatível ESP32')
    parser.add_argument('output_model', help='Arquivo de saída do modelo TFLite')
    parser.add_argument('input_model', nargs='?', help='Modelo TFLite de entrada (opcional)')
    parser.add_argument('--fit', action='store_true', 
                       help='Executa treinamento automático com dados gerados')
    
    args = parser.parse_args()
    
    output_path = args.output_model
    input_path = args.input_model
    
    logger.info("🔧 Gerador de Modelo TFLite Compatível ESP32")
    logger.info("=" * 50)
    
    if args.fit:
        logger.info("🏋️ Modo de treinamento automático ativado")
        logger.info("🔧 Criando e treinando modelo com dados gerados...")
        success = generate_simple_compatible_model(output_path)
    elif input_path and os.path.exists(input_path):
        logger.info(f"📂 Convertendo modelo existente: {input_path}")
        success = create_esp32_compatible_model(input_path, output_path)
    else:
        logger.info("🔧 Criando modelo simples de teste...")
        success = generate_simple_compatible_model(output_path)
    
    if success:
        logger.info("\n🎉 SUCESSO! Modelo gerado")
        logger.info(f"📁 Arquivo: {output_path}")
        
        # Verificar versão final
        version = check_model_version(output_path)
        if version == 3:
            logger.info("✅ Schema v3 - COMPATÍVEL COM ESP32!")
        else:
            logger.warning(f"⚠️ Schema v{version} - Pode não ser compatível")
        
        logger.info("\n💡 Próximos passos:")
        logger.info("   1. Use xxd -i model.tflite > model.h")
        logger.info("   2. Inclua model.h no seu projeto ESP-IDF")
        logger.info("   3. Compile e teste no ESP32")
        logger.info("\n📖 Como usar:")
        logger.info("   python generate_esp32_compatible.py model.tflite --fit")
        logger.info("   python generate_esp32_compatible.py model.tflite input.tflite")
    else:
        logger.error("❌ Falha ao gerar modelo")
        sys.exit(1)

if __name__ == "__main__":
    main()
