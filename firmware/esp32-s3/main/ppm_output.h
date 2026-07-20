#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"

#define SIMJOY_MAX_CHANNELS 16

typedef struct {
    uint8_t channel_count;
    uint16_t channels[SIMJOY_MAX_CHANNELS];
    uint16_t frame_us;
    uint16_t pulse_us;
    bool positive_polarity;
} simjoy_ppm_frame_t;

esp_err_t simjoy_ppm_start(int gpio_num);
void simjoy_ppm_set_frame(const simjoy_ppm_frame_t *frame);
void simjoy_ppm_get_frame(simjoy_ppm_frame_t *frame);
