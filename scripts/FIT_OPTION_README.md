# Uso da Opção --fit no generate_esp32_compatible.py

## Descrição
A opção `--fit` foi adicionada ao script `generate_esp32_compatible.py` para permitir o treinamento automático de modelos com dados gerados, sem necessidade de fornecer um modelo pré-existente.

## Como Usar

### 1. Treinamento Automático (Modo --fit)
```bash
python generate_esp32_compatible.py modelo_saida.tflite --fit
```

Este comando:
- Cria um modelo neural simples do zero
- Gera automaticamente dados de treinamento (função seno)
- Treina o modelo por 100 épocas
- Converte para TFLite compatível com ESP32
- Salva o modelo treinado

### 2. Conversão de Modelo Existente
```bash
python generate_esp32_compatible.py modelo_saida.tflite modelo_entrada.tflite
```

### 3. Modelo Simples (Modo Padrão)
```bash
python generate_esp32_compatible.py modelo_saida.tflite
```

## Melhorias Implementadas

### Treinamento Aprimorado
- **Dados de treinamento**: 2000 amostras para treinamento + 200 para validação
- **Épocas**: 100 épocas com verbose para acompanhar progresso
- **Métricas**: Loss e MAE exibidas ao final
- **Validação**: Conjunto de validação separado para evitar overfitting

### Interface Melhorada
- **argparse**: Substituição do parsing manual de argumentos
- **Ajuda**: `--help` mostra todas as opções disponíveis
- **Mensagens**: Logs mais informativos sobre o processo

## Requisitos

### TensorFlow
O script requer TensorFlow instalado. Caso não tenha:

```bash
# Instalar no ambiente atual
pip install tensorflow

# Ou ativar ambiente virtual (recomendado)
source ../venv/bin/activate
pip install tensorflow
```

## Exemplo de Saída

```
2026-04-05 09:59:24,109 - INFO - 🔧 Gerador de Modelo TFLite Compatível ESP32
2026-04-05 09:59:24,109 - INFO - ==================================================
2026-04-05 09:59:24,109 - INFO - 🏋️ Modo de treinamento automático ativado
2026-04-05 09:59:24,109 - INFO - 🔧 Criando e treinando modelo com dados gerados...
2026-04-05 09:59:24,109 - INFO - ✅ TensorFlow 2.x.x carregado
2026-04-05 09:59:24,109 - INFO - 📊 Gerando dados de treinamento...
2026-04-05 09:59:24,109 - INFO - 🏋️ Treinando modelo...
Epoch 1/100
63/63 [==============================] - 1s 5ms/step - loss: 0.4521 - mae: 0.5623 - val_loss: 0.4211 - val_mae: 0.5432
...
Epoch 100/100
63/63 [==============================] - 0s 2ms/step - loss: 0.0012 - mae: 0.0289 - val_loss: 0.0011 - val_mae: 0.0276
2026-04-05 09:59:35,123 - INFO - 📊 Métricas finais - Loss: 0.0011, MAE: 0.0276
2026-04-05 09:59:35,123 - INFO - 🔄 Convertendo para TFLite...
2026-04-05 09:59:35,145 - INFO - ✅ Modelo simples salvo: modelo_saida.tflite
2026-04-05 09:59:35,145 - INFO - 📊 Versão do schema: 3
```

## Arquitetura do Modelo

O modelo gerado é uma rede neural simples para aprender a função seno:

```
Input (1) → Dense(64, ReLU) → Dense(64, ReLU) → Dense(1) → Output
```

- **Entrada**: Valor numérico (ângulo em radianos)
- **Saída**: Seno do valor de entrada
- **Aplicação**: Teste de inferência em ESP32

## Próximos Passos

Após gerar o modelo com `--fit`:

1. **Converter para array C**:
   ```bash
   xxd -i modelo_saida.tflite > modelo.h
   ```

2. **Integrar no projeto ESP-IDF**:
   - Copiar `modelo.h` para o projeto
   - Incluir no código fonte
   - Compilar e testar

3. **Validar no hardware**:
   - Enviar valores de teste
   - Verificar precisão da inferência

## Resumo

A opção `--fit` torna o processo de criação de modelos mais acessível, eliminando a necessidade de ter um modelo pré-treinado e permitindo testes rápidos de compatibilidade com ESP32.
