from tkinter import YView
import tensorflow as tf
import numpy as np
import math
import PyQt6

SAMPES=10000
SEED=1337

np.random.seed(SEED)

tf.random.set_seed(SEED)

x_value = np.random.uniform(low=0, high=2*math.pi, size=SAMPES)

y_value = np.sin(x_value)
## exibe na gui feita com qt6 o valor de x_value e y_value

y_value += 0.1 * np.random.randn(*y_value.shape)
## exibe na gui feita com qt6 o valor de x_value e y_value com ruído

TRAIN_SPLIT = int(0.6 * SAMPES)
TEST_SPLIT = int(0.2 * SAMPES + TRAIN_SPLIT)

x_train, x_validate, x_test = np.split(x_value, [TRAIN_SPLIT, TEST_SPLIT])
y_train, y_validate, y_test = np.split(y_value, [TRAIN_SPLIT, TEST_SPLIT])

assert(x_train.size+x_validate.size+x_test.size == SAMPES)
assert(y_train.size+y_validate.size+y_test.size == SAMPES)
## exibe na gui feita com qt6 o valor de x_train, x_validate, x_test, y_train, y_validate, y_test

from tf.keras import models, layers

model_1 = tf.keras.Sequential()
model_1.add(layers.Dense(16, activation='relu', input_shape=(1,)))
model_1.add(layers.Dense(16, activation='relu'))
model_1.add(layers.Dense(1))
model_1.compile(optimizer='rmsprop', loss='mse', metrics=['mae'])

## o model summary deve ser exebido numa caixa de texto do rodapé
model_1.summary()

history_1 = model_1.fit(x_train, y_train, epochs=600, batch_size=16, validation_data=(x_validate, y_validate))
## crie campos no rodapé para exibir o history_1

## Faça um gráfico exibindo os valores de treinamento e validação
loss = history_1.history['loss']
val_loss = history_1.history['val_loss']
epochs = range(1, len(loss) + 1)

## aqui faça um grafico do mean absolute error
mae = history_1.history['mae']
val_mae = history_1.history['val_mae']

## aqui usamos o modelo para fazer uma predição dos dados avaliados
predictions = model_1.predict(x_validate)

## aqui faça um grafico da predição dos dados avaliados



