#include "ppm_output.h"

#include <string.h>

#include "driver/rmt_tx.h"
#include "esp_check.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

static const char *TAG = "simjoy_ppm";
static rmt_channel_handle_t s_tx_channel;
static rmt_encoder_handle_t s_copy_encoder;
static SemaphoreHandle_t s_frame_mutex;
static simjoy_ppm_frame_t s_frame = {
    .channel_count = 8,
    .channels = {1500, 1500, 1000, 1500, 1500, 1500, 1500, 1500},
    .frame_us = 22500,
    .pulse_us = 300,
    .positive_polarity = true,
};

static void sanitize_frame(simjoy_ppm_frame_t *frame)
{
    frame->channel_count = frame->channel_count < 4 ? 4 : frame->channel_count;
    frame->channel_count = frame->channel_count > SIMJOY_MAX_CHANNELS ? SIMJOY_MAX_CHANNELS : frame->channel_count;
    frame->pulse_us = frame->pulse_us < 100 ? 100 : frame->pulse_us;
    frame->pulse_us = frame->pulse_us > 1000 ? 1000 : frame->pulse_us;
    frame->frame_us = frame->frame_us < 10000 ? 10000 : frame->frame_us;
    frame->frame_us = frame->frame_us > 40000 ? 40000 : frame->frame_us;
    for (uint8_t i = 0; i < frame->channel_count; ++i) {
        frame->channels[i] = frame->channels[i] < 800 ? 800 : frame->channels[i];
        frame->channels[i] = frame->channels[i] > 2200 ? 2200 : frame->channels[i];
        if (frame->channels[i] <= frame->pulse_us) {
            frame->channels[i] = frame->pulse_us + 1;
        }
    }
}

static void ppm_task(void *arg)
{
    (void)arg;
    rmt_symbol_word_t symbols[SIMJOY_MAX_CHANNELS + 1];
    const rmt_transmit_config_t transmit_config = {
        .loop_count = 0,
        .flags.eot_level = 0,
    };
    while (true) {
        simjoy_ppm_frame_t frame;
        simjoy_ppm_get_frame(&frame);
        const uint8_t active = frame.positive_polarity ? 1 : 0;
        const uint8_t idle = active ? 0 : 1;
        uint32_t used_us = 0;
        for (uint8_t i = 0; i < frame.channel_count; ++i) {
            const uint16_t gap = frame.channels[i] - frame.pulse_us;
            symbols[i] = (rmt_symbol_word_t){
                .level0 = active,
                .duration0 = frame.pulse_us,
                .level1 = idle,
                .duration1 = gap,
            };
            used_us += frame.channels[i];
        }
        uint32_t sync_gap = frame.frame_us > used_us + frame.pulse_us
            ? frame.frame_us - used_us - frame.pulse_us
            : 3000;
        sync_gap = sync_gap > 32767 ? 32767 : sync_gap;
        symbols[frame.channel_count] = (rmt_symbol_word_t){
            .level0 = active,
            .duration0 = frame.pulse_us,
            .level1 = idle,
            .duration1 = sync_gap,
        };
        const size_t symbol_count = frame.channel_count + 1U;
        esp_err_t result = rmt_transmit(
            s_tx_channel,
            s_copy_encoder,
            symbols,
            symbol_count * sizeof(rmt_symbol_word_t),
            &transmit_config
        );
        if (result == ESP_OK) {
            result = rmt_tx_wait_all_done(s_tx_channel, pdMS_TO_TICKS(100));
        }
        if (result != ESP_OK) {
            ESP_LOGW(TAG, "PPM transmit error: %s", esp_err_to_name(result));
            vTaskDelay(pdMS_TO_TICKS(20));
        }
    }
}

esp_err_t simjoy_ppm_start(int gpio_num)
{
    s_frame_mutex = xSemaphoreCreateMutex();
    if (!s_frame_mutex) {
        return ESP_ERR_NO_MEM;
    }
    const rmt_tx_channel_config_t channel_config = {
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .gpio_num = gpio_num,
        .mem_block_symbols = 64,
        .resolution_hz = 1000000,
        .trans_queue_depth = 2,
        .flags.invert_out = false,
        .flags.with_dma = false,
    };
    ESP_ERROR_CHECK_WITHOUT_ABORT(rmt_new_tx_channel(&channel_config, &s_tx_channel));
    if (!s_tx_channel) {
        return ESP_FAIL;
    }
    const rmt_copy_encoder_config_t encoder_config = {};
    ESP_ERROR_CHECK_WITHOUT_ABORT(rmt_new_copy_encoder(&encoder_config, &s_copy_encoder));
    if (!s_copy_encoder) {
        return ESP_FAIL;
    }
    ESP_RETURN_ON_ERROR(rmt_enable(s_tx_channel), TAG, "RMT enable failed");
    BaseType_t created = xTaskCreate(ppm_task, "simjoy_ppm", 4096, NULL, 8, NULL);
    return created == pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
}

void simjoy_ppm_set_frame(const simjoy_ppm_frame_t *frame)
{
    if (!frame || !s_frame_mutex) {
        return;
    }
    simjoy_ppm_frame_t safe = *frame;
    sanitize_frame(&safe);
    if (xSemaphoreTake(s_frame_mutex, pdMS_TO_TICKS(10))) {
        s_frame = safe;
        xSemaphoreGive(s_frame_mutex);
    }
}

void simjoy_ppm_get_frame(simjoy_ppm_frame_t *frame)
{
    if (!frame) {
        return;
    }
    if (s_frame_mutex && xSemaphoreTake(s_frame_mutex, pdMS_TO_TICKS(10))) {
        *frame = s_frame;
        xSemaphoreGive(s_frame_mutex);
    } else {
        *frame = s_frame;
    }
}
