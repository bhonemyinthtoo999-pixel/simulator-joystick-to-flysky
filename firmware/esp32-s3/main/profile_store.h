#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"
#include "hid_report_parser.h"
#include "ppm_output.h"

typedef enum {
    SIMJOY_SOURCE_NONE,
    SIMJOY_SOURCE_AXIS,
    SIMJOY_SOURCE_BUTTON,
    SIMJOY_SOURCE_HAT,
    SIMJOY_SOURCE_CONSTANT,
} simjoy_source_type_t;

typedef struct {
    simjoy_source_type_t source_type;
    uint8_t source_index;
    bool hat_y;
    float constant_value;
    bool unipolar;
    bool reversed;
    uint16_t minimum;
    uint16_t center;
    uint16_t maximum;
    uint16_t failsafe;
    int16_t trim;
    float expo;
    float smoothing;
} simjoy_channel_mapping_t;

typedef struct {
    char profile_id[48];
    char name[64];
    uint8_t channel_count;
    uint16_t ppm_frame_us;
    uint16_t ppm_pulse_us;
    bool positive_polarity;
    uint16_t failsafe_timeout_ms;
    simjoy_channel_mapping_t mappings[SIMJOY_MAX_CHANNELS];
} simjoy_profile_t;

void simjoy_profile_default(simjoy_profile_t *profile);
esp_err_t simjoy_profile_load(simjoy_profile_t *profile);
esp_err_t simjoy_profile_validate_json(const char *json, char *error, size_t error_size);
esp_err_t simjoy_profile_save_json(const char *json, simjoy_profile_t *profile, char *error, size_t error_size);
void simjoy_profile_map_channels(
    const simjoy_profile_t *profile,
    const simjoy_input_state_t *input,
    uint32_t now_ms,
    uint16_t *channels
);
void simjoy_profile_to_ppm(const simjoy_profile_t *profile, const uint16_t *channels, simjoy_ppm_frame_t *frame);
