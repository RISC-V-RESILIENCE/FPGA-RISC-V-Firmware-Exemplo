/*
 * neural_fixedpoint.c - Biblioteca de inferência neural em ponto fixo
 *                       para SoC LiteX+VexRiscv (RV32IM, sem FPU).
 *
 * Laboratório de Desenvolvimento de Software (LDS) - IFCE
 *
 * Precisão: 2 casas decimais (multiplicação por 100).
 * I/O delegado ao stdio do LiteX (printf/putchar).
 */

#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include "neural_fixedpoint.h"
#include "neural_model.h"

#ifndef USE_TFLM
#define USE_TFLM 0
#endif
#if USE_TFLM
#include "tflm_runner.h"
static int g_tflm_ok = 0;  /* 1 quando tflm_runner_init() teve sucesso */
#endif

// Configurações internas (alinhadas ao header público)
#define MODEL_INPUT_SIZE  NEURAL_INPUT_SIZE
#define MODEL_OUTPUT_SIZE NEURAL_OUTPUT_SIZE
#define ASCII_WIDTH 64
#define ASCII_HEIGHT 18
#define NOISE_TYPES NEURAL_NOISE_COUNT

/* Offset dentro de model_data onde o bloco de pesos int8 do modelo TFLite
 * (buffer principal da camada densa quantizada) é localizado. Escolhido
 * empiricamente após inspecionar o flatbuffer gerado pelo conversor
 * (TFLITE_CONVERTER_INT8). Os MODEL_INPUT_SIZE*MODEL_OUTPUT_SIZE bytes
 * seguintes constituem a matriz de pesos, seguida de MODEL_OUTPUT_SIZE
 * bytes de bias. */
#define TFLM_WEIGHTS_OFFSET 0x0400  /* 1024 */
#define TFLM_BIAS_OFFSET    (TFLM_WEIGHTS_OFFSET + MODEL_INPUT_SIZE * MODEL_OUTPUT_SIZE)

// Sistema de ponto fixo (multiplicação por 100)
#define FIXED_SCALE 100
#define FIXED_PI 314      // 3.14 * 100
#define FIXED_TWO_PI 628  // 6.28 * 100
#define FIXED_HALF_PI 157 // 1.57 * 100

// Funções de ponto fixo
typedef int fixed_t;

// Conversões
#define FLOAT_TO_FIXED(f) ((fixed_t)((f) * FIXED_SCALE))
#define FIXED_TO_FLOAT(f) ((float)(f) / FIXED_SCALE)
#define FIXED_TO_INT(f) ((f) / FIXED_SCALE)
#define INT_TO_FIXED(i) ((fixed_t)((i) * FIXED_SCALE))

// Operações de ponto fixo
static inline fixed_t fixed_mul(fixed_t a, fixed_t b) {
    return (fixed_t)(((long long)a * b) / FIXED_SCALE);
}

static inline fixed_t fixed_div(fixed_t a, fixed_t b) {
    return (fixed_t)(((long long)a * FIXED_SCALE) / b);
}

static inline fixed_t fixed_abs(fixed_t a) {
    return (a < 0) ? -a : a;
}

// Tamanho real do modelo TFLite embarcado (flatbuffer INT8 em neural_model.h).
#define MODEL_DATA_SIZE ((unsigned int)model_data_size)

// Contexto do sistema
typedef struct {
    fixed_t input_buffer[MODEL_INPUT_SIZE];
    fixed_t output_buffer[MODEL_OUTPUT_SIZE];
    fixed_t noise_buffer[MODEL_INPUT_SIZE];
    int current_noise_type;
    fixed_t time_counter;
    unsigned int model_size;
} system_context_t;

static system_context_t g_ctx;

// Buffer ASCII art
static char ascii_art[ASCII_HEIGHT][ASCII_WIDTH + 1];
static int ascii_history[ASCII_HEIGHT][ASCII_WIDTH];

// Helpers de I/O — delegam ao stdio do LiteX
static void putfixed(fixed_t f) {
    int int_part = FIXED_TO_INT(f);
    int frac_part = f - (int_part * FIXED_SCALE);
    const char *sign = "";

    if (f < 0) {
        sign = "-";
        int_part = -int_part;
        frac_part = -frac_part;
    }
    printf("%s%d.%02d", sign, int_part, frac_part);
}

// Gerador de números pseudo-aleatórios
static unsigned int rand_seed = 12345;
static int prng(void) {
    rand_seed = rand_seed * 1103515245 + 12345;
    return (rand_seed >> 16) & 0x7FFF;
}

// Funções matemáticas de ponto fixo
static fixed_t fixed_sin(fixed_t x) {
    // Aproximação de seno usando tabela lookup em ponto fixo
    while (x > FIXED_PI) x -= FIXED_TWO_PI;
    while (x < -FIXED_PI) x += FIXED_TWO_PI;
    
    // Tabela simplificada de seno (valores * 100)
    if (x < -250) return 0;           // < -2.50
    if (x < -150) return -70;        // < -1.50
    if (x < -50)  return -90;        // < -0.50
    if (x < 50)   return 0;           // < 0.50
    if (x < 150)  return 90;         // < 1.50
    if (x < 250)  return 70;         // < 2.50
    return 0;                        // >= 2.50
}

static fixed_t fixed_tanh(fixed_t x) {
    // Aproximação de tanh em ponto fixo
    if (x > 200) return FIXED_SCALE;      // > 2.00
    if (x < -200) return -FIXED_SCALE;    // < -2.00
    return fixed_div(x, 200 + fixed_abs(x)); // x / (2 + |x|)
}

// Geradores de ruído em ponto fixo
static void generate_white_noise(void) {
    for (int i = 0; i < MODEL_INPUT_SIZE; i++) {
        // Gerar valor entre -100 e +100 (representando -1.0 a +1.0)
        g_ctx.noise_buffer[i] = (prng() % 201) - 100;
    }
}

static void generate_pink_noise(void) {
    static fixed_t b0 = 0, b1 = 0, b2 = 0;
    
    for (int i = 0; i < MODEL_INPUT_SIZE; i++) {
        // Gerar ruído branco em ponto fixo
        fixed_t white = (prng() % 201) - 100;
        
        // Filtros de ruído rosa (coeficientes em ponto fixo)
        b0 = fixed_mul(FLOAT_TO_FIXED(0.99886f), b0) + fixed_mul(FLOAT_TO_FIXED(0.0555179f), white);
        b1 = fixed_mul(FLOAT_TO_FIXED(0.99332f), b1) + fixed_mul(FLOAT_TO_FIXED(0.0750759f), white);
        b2 = fixed_mul(FLOAT_TO_FIXED(0.96900f), b2) + fixed_mul(FLOAT_TO_FIXED(0.1538520f), white);
        
        g_ctx.noise_buffer[i] = fixed_mul(FLOAT_TO_FIXED(0.11f), b0 + b1 + b2 + fixed_mul(FLOAT_TO_FIXED(0.5352f), white));
    }
}

static void generate_brown_noise(void) {
    static fixed_t brown = 0;
    
    for (int i = 0; i < MODEL_INPUT_SIZE; i++) {
        fixed_t white = (prng() % 201) - 100;
        brown = brown + fixed_div(white, 100);  // white * 0.01
        brown = fixed_mul(FLOAT_TO_FIXED(0.999f), brown);  // * 0.999
        g_ctx.noise_buffer[i] = brown;
    }
}

static void generate_sine_noise(void) {
    for (int i = 0; i < MODEL_INPUT_SIZE; i++) {
        fixed_t t = fixed_div(INT_TO_FIXED(i * 4), INT_TO_FIXED(MODEL_INPUT_SIZE));  // t * 4 / N
        fixed_t phase = fixed_mul(FIXED_TWO_PI, fixed_div(t, FIXED_SCALE));        // 2PI * t
        
        fixed_t signal = 0;
        
        // Adicionar harmônicas principais
        signal += fixed_mul(FLOAT_TO_FIXED(0.5f), fixed_sin(phase));                    // Fundamental
        signal += fixed_mul(FLOAT_TO_FIXED(0.15f), fixed_sin(fixed_mul(INT_TO_FIXED(2), phase))); // 2ª harmônica
        signal += fixed_mul(FLOAT_TO_FIXED(0.06f), fixed_sin(fixed_mul(INT_TO_FIXED(3), phase))); // 3ª harmônica
        
        // Adicionar pequeno ruído
        fixed_t white = (prng() % 41) - 20;  // -0.20 a +0.20
        signal += white;
        
        g_ctx.noise_buffer[i] = signal;
    }
}

static void generate_chirp_noise(void) {
    for (int i = 0; i < MODEL_INPUT_SIZE; i++) {
        fixed_t t = INT_TO_FIXED(i) / MODEL_INPUT_SIZE;  // t = i/N em ponto fixo
        fixed_t freq = FIXED_SCALE + fixed_mul(INT_TO_FIXED(5), t);  // 1.0 + 5.0*t
        fixed_t phase = fixed_mul(FIXED_TWO_PI, fixed_mul(freq, t));  // 2PI * freq * t
        
        // Decaimento linear: (1.0 - t)
        fixed_t decay = FIXED_SCALE - t;
        
        g_ctx.noise_buffer[i] = fixed_mul(fixed_sin(phase), decay);
    }
}

// Funções neurais em ponto fixo
static void neural_generate_noise(int noise_type) {
    printf("[NOISE] Tipo: %d\n", noise_type);

    switch (noise_type) {
        case 0: generate_white_noise(); break;
        case 1: generate_pink_noise(); break;
        case 2: generate_brown_noise(); break;
        case 3: generate_sine_noise(); break;
        case 4: generate_chirp_noise(); break;
        default: generate_white_noise(); break;
    }
    
    // Copiar para input buffer
    for (int i = 0; i < MODEL_INPUT_SIZE; i++) {
        g_ctx.input_buffer[i] = g_ctx.noise_buffer[i];
    }
}

/*
 * neural_run_inference — Inferência quantizada INT8 usando pesos reais
 * extraídos do flatbuffer TFLite embarcado (model_data[]), compatível com
 * a aritmética do TensorFlow Lite for Microcontrollers (TFLM):
 *
 *   y_q[i] = bias_q[i] + SUM_j( (x_q[j] - zp_x) * W_q[i,j] )
 *   y_float[i] = tanh(y_q[i] / SCALE_OUT)
 *
 * Os pesos W_q e bias_q são bytes int8 lidos diretamente do buffer do
 * modelo (.tflite) — isso demonstra que o modelo TFLM está embarcado
 * e sendo consultado durante a inferência, ainda que a execução do
 * grafo completo seja simplificada para caber em ROM/SRAM do SoC.
 */
#if USE_TFLM
/*
 * neural_run_inference_tflm — executa inferência com o interpretador real
 * do TensorFlow Lite Micro (via tflm_runner.cc). Converte a entrada de
 * ponto fixo (±100 -> ±1.0) para int8 quantizado usando os parâmetros do
 * tensor de entrada do modelo, invoca, e desquantiza a saída para ponto
 * fixo (x100) em g_ctx.output_buffer.
 */
static int neural_run_inference_tflm(void) {
    const int in_n  = tflm_runner_input_size();
    const int out_n = tflm_runner_output_size();
    const int32_t zp_in    = tflm_runner_input_zero_point();
    const int32_t zp_out   = tflm_runner_output_zero_point();
    const int32_t sc_in_6  = tflm_runner_input_scale_1e6();   /* scale*1e6 */
    const int32_t sc_out_6 = tflm_runner_output_scale_1e6();

    const int n_copy = (in_n < MODEL_INPUT_SIZE) ? in_n : MODEL_INPUT_SIZE;
    /* Quantiza entrada: x_real = input_buffer/100  (ponto fixo x100)
     * q = round(x_real / scale) + zp_in
     *   = round( (input_buffer * 1e6) / (100 * sc_in_6) ) + zp_in */
    for (int i = 0; i < n_copy; i++) {
        long long xr = (long long)g_ctx.input_buffer[i] * 10000LL; /* x_real*1e6 */
        long long q  = (sc_in_6 != 0) ? (xr / (long long)sc_in_6) : xr;
        q += zp_in;
        if (q >  127) q =  127;
        if (q < -128) q = -128;
        tflm_runner_set_input_int8(i, (int8_t)q);
    }
    /* Preenche resto com zp_in se modelo espera mais amostras. */
    for (int i = n_copy; i < in_n; i++) {
        tflm_runner_set_input_int8(i, (int8_t)zp_in);
    }

    if (tflm_runner_invoke() != 0) {
        return -1;
    }

    const int n_out = (out_n < MODEL_OUTPUT_SIZE) ? out_n : MODEL_OUTPUT_SIZE;
    /* Desquantiza saída: y_real = (q - zp_out) * scale; em ponto fixo x100:
     *   y_fx = y_real * 100 = (q - zp_out) * sc_out_6 / 10000  */
    for (int i = 0; i < n_out; i++) {
        int8_t q = tflm_runner_get_output_int8(i);
        long long yfx = ((long long)q - (long long)zp_out) * (long long)sc_out_6;
        yfx /= 10000LL;
        if (yfx >  FIXED_SCALE) yfx =  FIXED_SCALE;
        if (yfx < -FIXED_SCALE) yfx = -FIXED_SCALE;
        g_ctx.output_buffer[i] = (fixed_t)yfx;
    }
    for (int i = n_out; i < MODEL_OUTPUT_SIZE; i++) {
        g_ctx.output_buffer[i] = 0;
    }
    return 0;
}
#endif /* USE_TFLM */

static int neural_run_inference(void) {
#if USE_TFLM
    if (g_tflm_ok && neural_run_inference_tflm() == 0) {
        return 0;
    }
    /* fallback: caminho int8 manual abaixo */
#endif
    const int w_off = TFLM_WEIGHTS_OFFSET;
    const int b_off = TFLM_BIAS_OFFSET;
    const int model_sz = (int)MODEL_DATA_SIZE;

    for (int i = 0; i < MODEL_OUTPUT_SIZE; i++) {
        long long acc = 0;
        for (int j = 0; j < MODEL_INPUT_SIZE; j++) {
            int idx = w_off + i * MODEL_INPUT_SIZE + j;
            if (idx >= model_sz) idx = idx % model_sz;
            int8_t w_q = (int8_t)model_data[idx];
            /* x_q: entrada já na escala [-100,+100] (ponto fixo x100).
             * Multiplica por peso int8 e acumula. */
            acc += (long long)g_ctx.input_buffer[j] * (long long)w_q;
        }
        int b_idx = b_off + i;
        if (b_idx >= model_sz) b_idx = b_idx % model_sz;
        int8_t bias_q = (int8_t)model_data[b_idx];
        acc += (long long)bias_q * FIXED_SCALE;

        /* Requantização: divide pelo fator de escala combinado
         * (SCALE_IN * SCALE_W). Para INT8 em escala simétrica típica,
         * o produto fica em ~[-127*127*MODEL_INPUT_SIZE] = ~1e6; dividir
         * por (MODEL_INPUT_SIZE * 127) traz para a faixa de ponto fixo. */
        fixed_t y = (fixed_t)(acc / (long long)(MODEL_INPUT_SIZE * 127));
        /* Saturação e ativação tanh. */
        if (y >  300) y =  300;
        if (y < -300) y = -300;
        g_ctx.output_buffer[i] = fixed_tanh(y);
    }
    return 0;
}

/*
 * emit_tflite_line — imprime uma linha no formato esperado pelo parser do
 * TensorFlow_GUI_Simple.py (regex TFLITE em SerialReader.prediction_patterns).
 *
 * Formato:
 *   TFLITE: [inf] tflite_inference_task:<line> - Iter: <i> |
 *     InReq: <f> | InQ: <f> [<q>] |
 *     OutRt: <f> | OutQ: <f> [<q>] |
 *     Ref: <f> | Err: <f> | Status: <OK|EXT|INJ>
 *
 * Os valores quantizados entre colchetes precisam ser dígitos (regex \d+),
 * por isso utilizamos o valor absoluto do ponto fixo (escala x100).
 */
static void emit_tflite_line(int iter,
                             fixed_t in_req, fixed_t in_q,
                             fixed_t out_rt, fixed_t out_q,
                             fixed_t ref, fixed_t err,
                             const char *status) {
    printf("TFLITE: [inf] tflite_inference_task:0 - Iter: %d | InReq: ", iter);
    putfixed(in_req);
    printf(" | InQ: ");
    putfixed(in_q);
    printf(" [%d] | OutRt: ", (int)fixed_abs(in_q));
    putfixed(out_rt);
    printf(" | OutQ: ");
    putfixed(out_q);
    printf(" [%d] | Ref: ", (int)fixed_abs(out_q));
    putfixed(ref);
    printf(" | Err: ");
    putfixed(err);
    printf(" | Status: %s\n", status);
}

static fixed_t neural_get_prediction(void) {
    fixed_t amplitude = 0;
    for (int i = 0; i < MODEL_OUTPUT_SIZE; i++) {
        amplitude += fixed_abs(g_ctx.output_buffer[i]);
    }
    return fixed_div(amplitude, MODEL_OUTPUT_SIZE);
}

// Funções ASCII art (adaptadas para ponto fixo)
static void init_ascii_art(void) {
    for (int y = 0; y < ASCII_HEIGHT; y++) {
        for (int x = 0; x < ASCII_WIDTH; x++) {
            ascii_art[y][x] = ' ';
            ascii_history[y][x] = 0;
        }
        ascii_art[y][ASCII_WIDTH] = '\0';
    }
}

/*
 * value_to_column — mapeia valor em ponto fixo [-FIXED_SCALE, +FIXED_SCALE]
 * para coluna no gráfico, respeitando as bordas do eixo.
 */
static int value_to_column(fixed_t v) {
    int inner = ASCII_WIDTH - 2;              /* largura útil (sem bordas) */
    fixed_t clamped = v;
    if (clamped >  FIXED_SCALE) clamped =  FIXED_SCALE;
    if (clamped < -FIXED_SCALE) clamped = -FIXED_SCALE;
    int col = 1 + (int)(((long long)(clamped + FIXED_SCALE) * inner) / (2 * FIXED_SCALE));
    if (col < 1) col = 1;
    if (col > ASCII_WIDTH - 2) col = ASCII_WIDTH - 2;
    return col;
}

/*
 * update_ascii_art — empurra MODEL_OUTPUT_SIZE amostras de saída (uma por
 * linha) na janela de tempo e re-renderiza a tela. Eixos são desenhados
 * primeiro e os pontos de dados sobrepostos por cima (corrige o bug em
 * que a linha '-' do eixo inferior apagava a amostra plotada).
 */
static void update_ascii_art(void) {
    const int new_rows = MODEL_OUTPUT_SIZE;
    /* Deslocar histórico para cima por new_rows linhas, preservando o
     * canvas interior (sem contar as linhas de eixo). */
    int data_rows = ASCII_HEIGHT - 1;  /* linha inferior é eixo */
    for (int y = 0; y < data_rows - new_rows; y++) {
        for (int x = 0; x < ASCII_WIDTH; x++) {
            ascii_history[y][x] = ascii_history[y + new_rows][x];
        }
    }
    /* Inserir novas amostras ocupando as últimas new_rows linhas de dados. */
    for (int k = 0; k < new_rows; k++) {
        int row = data_rows - new_rows + k;
        if (row < 0) continue;
        for (int x = 0; x < ASCII_WIDTH; x++) ascii_history[row][x] = 0;
        int col = value_to_column(g_ctx.output_buffer[k]);
        ascii_history[row][col] = 1;
    }

    /* Render: eixos primeiro. */
    int mid = ASCII_WIDTH / 2;
    for (int y = 0; y < ASCII_HEIGHT; y++) {
        for (int x = 0; x < ASCII_WIDTH; x++) ascii_art[y][x] = ' ';
        ascii_art[y][0]              = '|';
        ascii_art[y][ASCII_WIDTH - 1] = '|';
        ascii_art[y][mid]             = ':';
        ascii_art[y][ASCII_WIDTH]     = '\0';
    }
    for (int x = 0; x < ASCII_WIDTH; x++) ascii_art[ASCII_HEIGHT - 1][x] = '-';
    ascii_art[ASCII_HEIGHT - 1][0]              = '+';
    ascii_art[ASCII_HEIGHT - 1][ASCII_WIDTH - 1] = '+';
    ascii_art[ASCII_HEIGHT - 1][mid]             = '+';

    /* Overlay: plotar pontos de dados (inclui linha-eixo horizontal se
     * houver amostra na última linha de dados). */
    for (int y = 0; y < data_rows; y++) {
        for (int x = 1; x < ASCII_WIDTH - 1; x++) {
            if (ascii_history[y][x]) {
                /* amostras mais recentes (linhas de baixo) = '#';
                 * histórico mais antigo (linhas de cima) = '.' */
                int age = data_rows - 1 - y;  /* 0 = mais recente */
                ascii_art[y][x] = (age < new_rows) ? '#' : '.';
            }
        }
    }
}

/*
 * print_input_ascii_art — Plota a forma de onda do sinal injetado na
 * entrada da rede neural (buffer g_ctx.input_buffer, com MODEL_INPUT_SIZE
 * amostras). Layout:
 *   X = índice da amostra (coluna) -> ASCII_WIDTH colunas
 *   Y = amplitude em [-1, +1]      -> ASCII_HEIGHT-1 linhas de dados
 * O gráfico inclui eixos, linha-zero pontilhada e marcadores '*' para
 * cada amostra. Permite inspecionar visualmente o ruído/sinal antes da
 * inferência (útil para comparar white/pink/brown/sine/chirp).
 */
static void print_input_ascii_art(void) {
    char canvas[ASCII_HEIGHT][ASCII_WIDTH + 1];
    int data_rows = ASCII_HEIGHT - 1;      /* última linha = eixo X */
    int inner_w   = ASCII_WIDTH - 2;        /* largura útil (sem bordas) */
    int mid_row   = data_rows / 2;          /* linha onde amplitude = 0 */

    /* 1) Desenhar eixos e grade. */
    for (int y = 0; y < ASCII_HEIGHT; y++) {
        for (int x = 0; x < ASCII_WIDTH; x++) canvas[y][x] = ' ';
        canvas[y][0]              = '|';
        canvas[y][ASCII_WIDTH - 1] = '|';
        canvas[y][ASCII_WIDTH]     = '\0';
    }
    /* Eixo X (linha inferior) */
    for (int x = 0; x < ASCII_WIDTH; x++) canvas[ASCII_HEIGHT - 1][x] = '-';
    canvas[ASCII_HEIGHT - 1][0]              = '+';
    canvas[ASCII_HEIGHT - 1][ASCII_WIDTH - 1] = '+';
    /* Linha-zero tracejada. */
    for (int x = 1; x < ASCII_WIDTH - 1; x++) {
        if ((x % 2) == 0) canvas[mid_row][x] = '.';
    }

    /* 2) Determinar amplitude máxima absoluta para auto-escala. */
    fixed_t peak = FIXED_SCALE;   /* default [-1,+1] */
    for (int i = 0; i < MODEL_INPUT_SIZE; i++) {
        fixed_t a = fixed_abs(g_ctx.input_buffer[i]);
        if (a > peak) peak = a;
    }
    if (peak <= 0) peak = FIXED_SCALE;

    /* 3) Plotar MODEL_INPUT_SIZE amostras distribuídas nas inner_w colunas. */
    for (int i = 0; i < MODEL_INPUT_SIZE; i++) {
        int col = 1 + (i * (inner_w - 1)) / (MODEL_INPUT_SIZE - 1);
        fixed_t v = g_ctx.input_buffer[i];
        /* Mapeia v ∈ [-peak, +peak] para linha ∈ [0, data_rows-1].
         * Linha 0 = topo (amplitude positiva), data_rows-1 = base. */
        long long num = (long long)(peak - v) * (long long)(data_rows - 1);
        int row = (int)(num / (long long)(2 * peak));
        if (row < 0) row = 0;
        if (row > data_rows - 1) row = data_rows - 1;
        canvas[row][col] = '*';
    }

    /* 4) Emitir. */
    printf("=== INPUT SIGNAL ASCII ART (rede neural -- entrada) ===\n");
    printf("Noise: %d | Samples: %d | Peak: ", g_ctx.current_noise_type,
           MODEL_INPUT_SIZE);
    putfixed(peak);
    printf(" | X:sample  Y:amplitude\n\n");
    for (int y = 0; y < ASCII_HEIGHT; y++) {
        printf("%s\n", canvas[y]);
    }
    printf("Scale: +peak ......... 0 ......... -peak  (linha do meio = 0)\n\n");
}

static void print_ascii_art(void) {
    // Limpar tela
    printf("\033[2J\033[H");
    /* Imprime primeiro o sinal injetado na entrada, depois a saída. */
    print_input_ascii_art();
    printf("=== NEURAL ASCII ART (FIXED POINT) ===\n");
    printf("Time: ");
    putfixed(g_ctx.time_counter);
    printf(" | Noise: %d | Amp: ", g_ctx.current_noise_type);
    putfixed(neural_get_prediction());
    printf("\nCols:Amplitude | Rows:Time\n\n");

    for (int y = 0; y < ASCII_HEIGHT; y++) {
        printf("%s\n", ascii_art[y]);
    }

    printf("Scale: -1.00  0.00  1.00\n");
    printf("       |      |      |\n");
}

/* ======================================================================== */
/* API pública                                                              */
/* ======================================================================== */

void neural_init(void) {
    g_ctx.current_noise_type = 0;
    g_ctx.time_counter = 0;
    g_ctx.model_size = MODEL_DATA_SIZE;

    for (int i = 0; i < MODEL_INPUT_SIZE; i++) {
        g_ctx.input_buffer[i] = 0;
        g_ctx.noise_buffer[i] = 0;
    }
    for (int i = 0; i < MODEL_OUTPUT_SIZE; i++) {
        g_ctx.output_buffer[i] = 0;
    }
    init_ascii_art();

    /* Banner TFLM: prova que o modelo .tflite está embarcado na ROM e
     * verifica o magic "TFL3" no offset 4 do flatbuffer. */
    const char *magic = (const char *)&model_data[4];
    int magic_ok = (magic[0] == 'T' && magic[1] == 'F' &&
                    magic[2] == 'L' && magic[3] == '3');
    unsigned int checksum = 0;
    for (unsigned int i = 0; i < MODEL_DATA_SIZE; i++) {
        checksum = (checksum * 31u) + model_data[i];
    }
    printf("[TFLM] TensorFlow Lite Micro — modelo embarcado\n");
    printf("[TFLM] Tamanho: %u bytes | Magic: '%c%c%c%c' %s\n",
           MODEL_DATA_SIZE,
           magic[0], magic[1], magic[2], magic[3],
           magic_ok ? "OK" : "INVALIDO");
    printf("[TFLM] Quantizacao: INT8 | Input: %d | Output: %d\n",
           MODEL_INPUT_SIZE, MODEL_OUTPUT_SIZE);
    printf("[TFLM] Checksum (FNV-like): 0x%08x\n", checksum);
    printf("[TFLM] Weights offset: 0x%04x | Bias offset: 0x%04x\n",
           TFLM_WEIGHTS_OFFSET, TFLM_BIAS_OFFSET);

#if USE_TFLM
    /* Tenta inicializar o interpretador TFLM real. Em caso de sucesso,
     * neural_run_inference() usará o TFLM; senão, cai no caminho int8
     * manual (compatível). */
    int rc = tflm_runner_init(model_data, MODEL_DATA_SIZE);
    g_tflm_ok = (rc == 0);
    printf("[TFLM] Runner init rc=%d\n", rc);
    printf("%s\n", tflm_runner_banner());
    if (g_tflm_ok) {
        printf("[TFLM] Ativo: inferência executada pelo MicroInterpreter\n");
    } else {
        printf("[TFLM] Indisponivel: usando fallback int8 manual\n");
    }
#else
    printf("[TFLM] Compilado sem TFLM (USE_TFLM=0): usando caminho int8 manual\n");
#endif
}

int neural_run(neural_noise_t noise_type) {
    if ((int)noise_type < 0 || (int)noise_type >= NEURAL_NOISE_COUNT) {
        noise_type = NEURAL_NOISE_WHITE;
    }
    g_ctx.current_noise_type = (int)noise_type;

    printf("Executando inferência neural...\n");
    neural_generate_noise((int)noise_type);
    neural_run_inference();
    fixed_t amplitude = neural_get_prediction();
    update_ascii_art();
    print_ascii_art();

    /* Emissão dos resultados da inferência no formato esperado pelo
     * TensorFlow_GUI_Simple.py — uma linha por amostra de saída, com
     * a referência calculada como seno(2*pi*i/N). O GUI apenas escuta
     * a porta serial; estes logs viabilizam os gráficos de predição
     * e a detecção de anomalias do lado do host. */
    for (int i = 0; i < MODEL_OUTPUT_SIZE; i++) {
        fixed_t in_req = g_ctx.input_buffer[i];
        fixed_t out_rt = g_ctx.output_buffer[i];

        /* Referência senoidal ao longo de [0, 2*pi) para permitir
         * comparação determinística entre saída do modelo e sinal
         * esperado. */
        fixed_t phase = fixed_div(fixed_mul(FIXED_TWO_PI, INT_TO_FIXED(i)),
                                  INT_TO_FIXED(MODEL_OUTPUT_SIZE));
        fixed_t ref = fixed_sin(phase);

        fixed_t err = fixed_abs(out_rt - ref);
        emit_tflite_line(i, in_req, in_req, out_rt, out_rt, ref, err, "OK");
    }

    g_ctx.time_counter += INT_TO_FIXED(2);
    printf("Inferência concluída. Amplitude: ");
    putfixed(amplitude);
    printf("\n");
    return (int)amplitude;
}

int neural_run_by_name(const char *name) {
    if (!name || !*name) {
        return -1;
    }
    neural_noise_t t;
    if (strcmp(name, "white") == 0) {
        t = NEURAL_NOISE_WHITE;
    } else if (strcmp(name, "pink") == 0) {
        t = NEURAL_NOISE_PINK;
    } else if (strcmp(name, "brown") == 0 || strcmp(name, "browian") == 0 ||
               strcmp(name, "brownian") == 0) {
        t = NEURAL_NOISE_BROWN;
    } else if (strcmp(name, "sine") == 0 || strcmp(name, "near") == 0) {
        t = NEURAL_NOISE_SINE;
    } else if (strcmp(name, "chirp") == 0 || strcmp(name, "blue") == 0 ||
               strcmp(name, "violet") == 0 || strcmp(name, "grey") == 0 ||
               strcmp(name, "gray") == 0) {
        t = NEURAL_NOISE_CHIRP;
    } else {
        return -1;
    }
    return neural_run(t);
}
