/*
 * tflm_runner.cc — Wrapper C++ que expõe uma API extern "C" para o
 * TensorFlow Lite for Microcontrollers (TFLM), permitindo usar o
 * interpretador a partir do firmware C (neural_fixedpoint.c) do SoC
 * VexRiscv/LiteX.
 *
 * O design é minimalista: um único interpreter global, uma arena
 * estática e um OpResolver com apenas os operadores realmente usados
 * pelo modelo INT8 embarcado (FULLY_CONNECTED, SOFTMAX, RESHAPE,
 * TANH, LOGISTIC). A arena de 16 KiB é suficiente para modelos
 * pequenos (<= 4 KB de pesos).
 */

#include "tflm_runner.h"

#include <cstdio>
#include <cstring>
#include <cstdint>

#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/micro_log.h"
#include "tensorflow/lite/schema/schema_generated.h"

namespace {

constexpr int kTensorArenaSize = 16 * 1024;
alignas(16) uint8_t g_tensor_arena[kTensorArenaSize];

using OpResolver = tflite::MicroMutableOpResolver<8>;
OpResolver              g_op_resolver;
const tflite::Model*    g_model       = nullptr;
tflite::MicroInterpreter* g_interpreter = nullptr;
alignas(alignof(tflite::MicroInterpreter))
    uint8_t g_interpreter_storage[sizeof(tflite::MicroInterpreter)];

TfLiteTensor* g_input  = nullptr;
TfLiteTensor* g_output = nullptr;

char g_banner[96] = "[TFLM] Runner nao inicializado";

bool RegisterOps(OpResolver& resolver) {
    /* Conjunto mínimo para os modelos INT8 gerados pelo TFLite converter
     * padrão (Dense/Softmax com ativações comuns). Caso o modelo use um
     * op não registrado aqui, adicione a chamada correspondente. */
    if (resolver.AddFullyConnected() != kTfLiteOk) return false;
    if (resolver.AddSoftmax()        != kTfLiteOk) return false;
    if (resolver.AddReshape()        != kTfLiteOk) return false;
    if (resolver.AddTanh()           != kTfLiteOk) return false;
    if (resolver.AddLogistic()       != kTfLiteOk) return false;
    if (resolver.AddRelu()           != kTfLiteOk) return false;
    if (resolver.AddQuantize()       != kTfLiteOk) return false;
    if (resolver.AddDequantize()     != kTfLiteOk) return false;
    return true;
}

int32_t ScaleTo1e6(float scale) {
    double v = static_cast<double>(scale) * 1e6;
    if (v > 2147483647.0) v = 2147483647.0;
    if (v < -2147483648.0) v = -2147483648.0;
    return static_cast<int32_t>(v);
}

}  // namespace

extern "C" {

int tflm_runner_init(const unsigned char* model_data, unsigned int model_len) {
    (void)model_len;
    g_model = tflite::GetModel(model_data);
    printf("[TFLM] Sucesso GetModel()!");
    if (g_model == nullptr) {
        std::snprintf(g_banner, sizeof(g_banner),
                      "[TFLM] GetModel() retornou NULL");
        return 1;
    }
    if (g_model->version() != TFLITE_SCHEMA_VERSION) {
        std::snprintf(g_banner, sizeof(g_banner),
                      "[TFLM] Schema mismatch: modelo=%d runtime=%d",
                      (int)g_model->version(), (int)TFLITE_SCHEMA_VERSION);
        return 2;
    }

    if (!RegisterOps(g_op_resolver)) {
        std::snprintf(g_banner, sizeof(g_banner),
                      "[TFLM] Falha ao registrar operadores");
        return 3;
    }
    printf("[TFLM] Sucess RegisterOps");
    /* Placement new do interpreter no buffer estático. */
    g_interpreter = new (g_interpreter_storage)
        tflite::MicroInterpreter(g_model, g_op_resolver,
                                 g_tensor_arena, kTensorArenaSize);

    TfLiteStatus alloc = g_interpreter->AllocateTensors();
    printf("[TFLM] Sucess AllocateTensors!");
    if (alloc != kTfLiteOk) {
        std::snprintf(g_banner, sizeof(g_banner),
                      "[TFLM] AllocateTensors falhou (arena=%d)",
                      kTensorArenaSize);
        return 4;
    }

    g_input  = g_interpreter->input(0);
    g_output = g_interpreter->output(0);
    if (g_input == nullptr || g_output == nullptr) {
        std::snprintf(g_banner, sizeof(g_banner),
                      "[TFLM] input/output tensor NULL");
        return 5;
    }

    std::snprintf(g_banner, sizeof(g_banner),
                  "[TFLM] OK | arena_used=%u/%u | in=%d out=%d",
                  (unsigned)g_interpreter->arena_used_bytes(),
                  (unsigned)kTensorArenaSize,
                  (int)g_input->bytes,
                  (int)g_output->bytes);
    return 0;
}

int tflm_runner_input_size(void) {
    if (g_input == nullptr) return 0;
    return (int)(g_input->bytes);  /* int8 => 1 byte/elemento */
}

int tflm_runner_output_size(void) {
    if (g_output == nullptr) return 0;
    return (int)(g_output->bytes);
}

int32_t tflm_runner_input_zero_point(void) {
    if (g_input == nullptr) return 0;
    return (int32_t)g_input->params.zero_point;
}

int32_t tflm_runner_output_zero_point(void) {
    if (g_output == nullptr) return 0;
    return (int32_t)g_output->params.zero_point;
}

int32_t tflm_runner_input_scale_1e6(void) {
    if (g_input == nullptr) return 0;
    return ScaleTo1e6(g_input->params.scale);
}

int32_t tflm_runner_output_scale_1e6(void) {
    if (g_output == nullptr) return 0;
    return ScaleTo1e6(g_output->params.scale);
}

void tflm_runner_set_input_int8(int index, int8_t q) {
    if (g_input == nullptr) return;
    if (index < 0 || (size_t)index >= g_input->bytes) return;
    g_input->data.int8[index] = q;
}

int8_t tflm_runner_get_output_int8(int index) {
    if (g_output == nullptr) return 0;
    if (index < 0 || (size_t)index >= g_output->bytes) return 0;
    return g_output->data.int8[index];
}

int tflm_runner_invoke(void) {
    if (g_interpreter == nullptr) return 10;
    TfLiteStatus st = g_interpreter->Invoke();
    printf("[TFLM] Sucess Invoke!");
    return (st == kTfLiteOk) ? 0 : 11;
}

const char* tflm_runner_banner(void) {
    return g_banner;
}

/* Stubs para newlib libm/libstdc++ num ambiente sem pthread/errno:
 *   - __errno(): libm do newlib usa errno para sinalizar NaN/overflow.
 *   - __cxa_pure_virtual(): chamada virtual pura (TFLM não usa, mas g++ emite).
 *   - __dso_handle: referenciado por código com -fuse-cxa-atexit desativado. */
static int g_errno_placeholder = 0;
int* __errno(void) { return &g_errno_placeholder; }

void __cxa_pure_virtual() { while (1) { } }

void* __dso_handle = nullptr;

}  /* extern "C" */
