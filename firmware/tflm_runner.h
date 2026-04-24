/*
 * tflm_runner.h — API C para o TensorFlow Lite Micro usado no firmware
 * VexRiscv/LiteX. Envolve a API C++ do TFLM (MicroInterpreter +
 * MicroMutableOpResolver) em funções extern "C" para ser consumida
 * diretamente de neural_fixedpoint.c.
 *
 * Fluxo típico:
 *   tflm_runner_init(model_data, model_data_size);
 *   tflm_runner_set_input_int8(i, q);
 *   tflm_runner_invoke();
 *   q = tflm_runner_get_output_int8(j);
 */
#ifndef TFLM_RUNNER_H
#define TFLM_RUNNER_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Retornos: 0 = OK, !=0 = erro (códigos definidos em tflm_runner.cc). */
int tflm_runner_init(const unsigned char *model_data, unsigned int model_len);

/* Tamanhos do tensor de entrada/saída (número de elementos). */
int tflm_runner_input_size(void);
int tflm_runner_output_size(void);

/* Parâmetros de quantização expostos como int/int32 (evita float no C). */
int32_t tflm_runner_input_zero_point(void);
int32_t tflm_runner_output_zero_point(void);
/* Escala × 1e6 (retornada como int32 para evitar FPU). */
int32_t tflm_runner_input_scale_1e6(void);
int32_t tflm_runner_output_scale_1e6(void);

/* Manipulação de tensores int8 (o caso do nosso modelo INT8). */
void    tflm_runner_set_input_int8(int index, int8_t q);
int8_t  tflm_runner_get_output_int8(int index);

/* Execução da inferência; retorna 0 em sucesso. */
int tflm_runner_invoke(void);

/* Banner textual curto (arena usada / disponível). */
const char *tflm_runner_banner(void);

#ifdef __cplusplus
}
#endif

#endif /* TFLM_RUNNER_H */
