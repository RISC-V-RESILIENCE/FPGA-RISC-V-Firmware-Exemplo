#!/usr/bin/env python3
"""
Analisador de topologia de rede neural TensorFlow Lite
Extrai informações detalhadas sobre a arquitetura da rede
"""

import tensorflow as tf
import numpy as np

def analyze_model_topology(model_path):
    """Analisa a topologia completa da rede neural"""
    print("=" * 60)
    print("ANÁLISE DETALHADA DA TOPOLOGIA DA REDE NEURAL")
    print("=" * 60)
    
    # Carregar o modelo
    interpreter = tf.lite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    
    # Obter todos os detalhes
    tensor_details = interpreter.get_tensor_details()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    print(f"Modelo: {model_path}")
    print(f"Tamanho: {len(open(model_path, 'rb').read())} bytes")
    print(f"Total de tensores: {len(tensor_details)}")
    print(f"Entradas: {len(input_details)}")
    print(f"Saídas: {len(output_details)}")
    print()
    
    # Análise das entradas
    print("--- ENTRADAS ---")
    for i, inp in enumerate(input_details):
        print(f"Entrada {i}: {inp['name']}")
        print(f"  Shape: {inp['shape']}")
        print(f"  Tipo: {inp['dtype']}")
        print(f"  Quantização: {inp.get('quantization', (0, 0))}")
        print()
    
    # Análise das saídas
    print("--- SAÍDAS ---")
    for i, out in enumerate(output_details):
        print(f"Saída {i}: {out['name']}")
        print(f"  Shape: {out['shape']}")
        print(f"  Tipo: {out['dtype']}")
        print(f"  Quantização: {out.get('quantization', (0, 0))}")
        print()
    
    # Mapear camadas
    print("--- ARQUITETURA DA REDE ---")
    layers = extract_layers(tensor_details)
    
    for i, layer in enumerate(layers):
        print(f"Camada {i+1}: {layer['type']}")
        print(f"  Operação: {layer['operation']}")
        print(f"  Tensor: {layer['tensor_name']}")
        print(f"  Shape: {layer['shape']}")
        print(f"  Tipo: {layer['dtype']}")
        print(f"  Quantização: {layer['quantization']}")
        print()
    
    # Fluxo de dados
    print("--- FLUXO DE DADOS ---")
    print_data_flow(tensor_details, input_details, output_details)
    
    # Parâmetros da rede
    print("--- PARÂMETROS DA REDE ---")
    count_parameters(tensor_details)
    
    print()
    print("=" * 60)
    print("RESUMO DA ARQUITETURA")
    print("=" * 60)
    
    # Resumo
    layer_types = [layer['type'] for layer in layers]
    print(f"Camadas: {len(layers)}")
    print(f"Tipos: {dict((type_, layer_types.count(type_)) for type_ in set(layer_types))}")
    print(f"Entrada: {input_details[0]['shape']} -> Saída: {output_details[0]['shape']}")

def extract_layers(tensor_details):
    """Extrai informações das camadas"""
    layers = []
    
    for tensor in tensor_details:
        name = tensor['name']
        layer_info = {
            'tensor_name': name,
            'shape': tensor['shape'],
            'dtype': tensor['dtype'],
            'quantization': tensor.get('quantization', (0, 0)),
            'is_variable': tensor.get('is_variable', False)
        }
        
        # Identificar tipo de camada
        if 'serving_default' in name:
            layer_info['type'] = 'Input'
            layer_info['operation'] = 'Input Layer'
        elif 'StatefulPartitionedCall' in name:
            layer_info['type'] = 'Output'
            layer_info['operation'] = 'Output Layer'
        elif 'MatMul' in name:
            layer_info['type'] = 'Dense'
            layer_info['operation'] = 'Matrix Multiplication'
        elif 'BiasAdd' in name or 'Add' in name:
            layer_info['type'] = 'Bias'
            layer_info['operation'] = 'Bias Addition'
        elif 'Relu' in name:
            layer_info['type'] = 'Activation'
            layer_info['operation'] = 'ReLU'
        elif 'Conv' in name:
            layer_info['type'] = 'Conv2D'
            layer_info['operation'] = 'Convolution'
        elif 'MaxPool' in name:
            layer_info['type'] = 'Pooling'
            layer_info['operation'] = 'Max Pooling'
        elif 'Flatten' in name:
            layer_info['type'] = 'Flatten'
            layer_info['operation'] = 'Flatten'
        else:
            layer_info['type'] = 'Unknown'
            layer_info['operation'] = 'Unknown Operation'
        
        layers.append(layer_info)
    
    # Ordenar por fluxo lógico
    return sort_layers_by_flow(layers)

def sort_layers_by_flow(layers):
    """Ordena camadas por fluxo lógico de dados"""
    # Ordem preferencial para tipos de camadas
    priority_order = {
        'Input': 0,
        'Conv2D': 1,
        'Dense': 2,
        'Bias': 3,
        'Activation': 4,
        'Pooling': 5,
        'Flatten': 6,
        'Output': 10
    }
    
    return sorted(layers, key=lambda x: priority_order.get(x['type'], 5))

def print_data_flow(tensor_details, input_details, output_details):
    """Imprime o fluxo de dados através da rede"""
    input_name = input_details[0]['name']
    output_name = output_details[0]['name']
    
    print(f"Entrada: {input_name}")
    
    # Encontrar camadas intermediárias
    intermediate_tensors = []
    for tensor in tensor_details:
        if (tensor['name'] != input_name and 
            tensor['name'] != output_name and
            not tensor.get('is_variable', False)):
            intermediate_tensors.append(tensor['name'])
    
    for tensor_name in intermediate_tensors:
        print(f"  ↓")
        print(f"  {tensor_name}")
    
    print(f"  ↓")
    print(f"Saída: {output_name}")

def count_parameters(tensor_details):
    """Conta o número de parâmetros treináveis"""
    total_params = 0
    trainable_params = 0
    
    for tensor in tensor_details:
        if tensor.get('is_variable', False):
            shape = tensor['shape']
            params = np.prod(shape)
            total_params += params
            
            if 'bias' in tensor['name'].lower():
                trainable_params += params
            elif 'kernel' in tensor['name'].lower() or 'weight' in tensor['name'].lower():
                trainable_params += params
    
    print(f"Parâmetros totais: {total_params:,}")
    print(f"Parâmetros treináveis: {trainable_params:,}")

def main():
    """Função principal"""
    model_path = "model_int8.tflite"
    analyze_model_topology(model_path)

if __name__ == "__main__":
    main()
