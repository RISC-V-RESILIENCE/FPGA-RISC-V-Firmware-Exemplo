/*
 * neural_fixedpoint.h - API pública da biblioteca de inferência neural
 *                      em ponto fixo (RV32IM sem FPU).
 *
 * Laboratório de Desenvolvimento de Software (LDS) - IFCE
 */

#ifndef NEURAL_FIXEDPOINT_H
#define NEURAL_FIXEDPOINT_H

#ifdef __cplusplus
extern "C" {
#endif

/* Tamanhos expostos (apenas informativos para o chamador). */
#define NEURAL_INPUT_SIZE   64
#define NEURAL_OUTPUT_SIZE   8

/* Tipos de ruído aceitos pela biblioteca. */
typedef enum {
    NEURAL_NOISE_WHITE  = 0,
    NEURAL_NOISE_PINK   = 1,
    NEURAL_NOISE_BROWN  = 2,
    NEURAL_NOISE_SINE   = 3,
    NEURAL_NOISE_CHIRP  = 4,
    NEURAL_NOISE_COUNT
} neural_noise_t;

/*
 * neural_init — Inicializa buffers internos e o frame ASCII.
 * Deve ser chamado uma única vez, após uart_init()/printf estarem prontos.
 */
void neural_init(void);

/*
 * neural_run — Executa uma inferência com o tipo de ruído informado,
 * atualiza o frame ASCII e imprime via printf.
 * Retorna a amplitude prevista em ponto fixo (escala x100).
 */
int neural_run(neural_noise_t noise_type);

/*
 * neural_run_by_name — Igual a neural_run, porém recebe o nome do ruído
 * (ex.: "white", "pink", "brown", "sine", "chirp", além de sinônimos
 * aceitos como "browian", "near", "grey", "violet", "blue").
 * Retorna a amplitude em ponto fixo, ou -1 se o nome não for reconhecido.
 */
int neural_run_by_name(const char *name);

#ifdef __cplusplus
}
#endif

#endif /* NEURAL_FIXEDPOINT_H */
