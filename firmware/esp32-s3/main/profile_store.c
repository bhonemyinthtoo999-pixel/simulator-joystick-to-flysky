#include "profile_store.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cJSON.h"
#include "nvs.h"

#define PROFILE_NAMESPACE "simjoy"
#define PROFILE_KEY "profile"
#define PROFILE_JSON_MAX 8192

static float s_smoothed[SIMJOY_MAX_CHANNELS];
static bool s_smoothed_valid[SIMJOY_MAX_CHANNELS];

static void set_error(char *error, size_t size, const char *message)
{
    if (error && size) {
        snprintf(error, size, "%s", message ? message : "unknown error");
    }
}

static int json_int(const cJSON *object, const char *name, int fallback)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(object, name);
    return cJSON_IsNumber(item) ? item->valueint : fallback;
}

static double json_number(const cJSON *object, const char *name, double fallback)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(object, name);
    return cJSON_IsNumber(item) ? item->valuedouble : fallback;
}

static bool json_bool(const cJSON *object, const char *name, bool fallback)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(object, name);
    return cJSON_IsBool(item) ? cJSON_IsTrue(item) : fallback;
}

static const char *json_string(const cJSON *object, const char *name, const char *fallback)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(object, name);
    return cJSON_IsString(item) && item->valuestring ? item->valuestring : fallback;
}

static simjoy_source_type_t parse_source(const char *value)
{
    if (!strcmp(value, "axis")) return SIMJOY_SOURCE_AXIS;
    if (!strcmp(value, "button")) return SIMJOY_SOURCE_BUTTON;
    if (!strcmp(value, "hat")) return SIMJOY_SOURCE_HAT;
    if (!strcmp(value, "constant")) return SIMJOY_SOURCE_CONSTANT;
    return SIMJOY_SOURCE_NONE;
}

void simjoy_profile_default(simjoy_profile_t *profile)
{
    if (!profile) return;
    memset(profile, 0, sizeof(*profile));
    snprintf(profile->profile_id, sizeof(profile->profile_id), "factory-default");
    snprintf(profile->name, sizeof(profile->name), "Factory Default");
    profile->channel_count = 8;
    profile->ppm_frame_us = 22500;
    profile->ppm_pulse_us = 300;
    profile->positive_polarity = true;
    profile->failsafe_timeout_ms = 700;
    const char *names[4] = {"Roll", "Pitch", "Throttle", "Yaw"};
    (void)names;
    for (uint8_t i = 0; i < profile->channel_count; ++i) {
        simjoy_channel_mapping_t *mapping = &profile->mappings[i];
        mapping->minimum = 1000;
        mapping->center = 1500;
        mapping->maximum = 2000;
        mapping->failsafe = i == 2 ? 1000 : 1500;
        mapping->source_type = i < 4 ? SIMJOY_SOURCE_AXIS : SIMJOY_SOURCE_NONE;
        mapping->source_index = i;
        mapping->unipolar = i == 2;
    }
    memset(s_smoothed_valid, 0, sizeof(s_smoothed_valid));
}

static esp_err_t parse_profile_object(const cJSON *root, simjoy_profile_t *profile, char *error, size_t error_size)
{
    if (!cJSON_IsObject(root) || !profile) {
        set_error(error, error_size, "profile must be a JSON object");
        return ESP_ERR_INVALID_ARG;
    }
    simjoy_profile_t parsed;
    simjoy_profile_default(&parsed);
    snprintf(parsed.profile_id, sizeof(parsed.profile_id), "%s", json_string(root, "profile_id", "unnamed"));
    snprintf(parsed.name, sizeof(parsed.name), "%s", json_string(root, "name", "Unnamed profile"));
    parsed.channel_count = (uint8_t)json_int(root, "channel_count", 8);
    parsed.ppm_frame_us = (uint16_t)json_int(root, "ppm_frame_us", 22500);
    parsed.ppm_pulse_us = (uint16_t)json_int(root, "ppm_pulse_us", 300);
    parsed.positive_polarity = strcmp(json_string(root, "ppm_polarity", "positive"), "negative") != 0;
    parsed.failsafe_timeout_ms = (uint16_t)json_int(root, "failsafe_timeout_ms", 700);

    if (parsed.channel_count < 4 || parsed.channel_count > SIMJOY_MAX_CHANNELS) {
        set_error(error, error_size, "channel_count must be 4..16");
        return ESP_ERR_INVALID_ARG;
    }
    if (parsed.ppm_frame_us < 10000 || parsed.ppm_frame_us > 40000 ||
        parsed.ppm_pulse_us < 100 || parsed.ppm_pulse_us > 1000) {
        set_error(error, error_size, "invalid PPM timing");
        return ESP_ERR_INVALID_ARG;
    }
    if (parsed.failsafe_timeout_ms < 100 || parsed.failsafe_timeout_ms > 10000) {
        set_error(error, error_size, "failsafe_timeout_ms must be 100..10000");
        return ESP_ERR_INVALID_ARG;
    }

    const cJSON *mappings = cJSON_GetObjectItemCaseSensitive(root, "mappings");
    if (!cJSON_IsArray(mappings) || cJSON_GetArraySize(mappings) != parsed.channel_count) {
        set_error(error, error_size, "mapping count must match channel_count");
        return ESP_ERR_INVALID_ARG;
    }
    uint32_t maximum_sum = 0;
    for (uint8_t i = 0; i < parsed.channel_count; ++i) {
        const cJSON *item = cJSON_GetArrayItem(mappings, i);
        if (!cJSON_IsObject(item)) {
            set_error(error, error_size, "mapping must be an object");
            return ESP_ERR_INVALID_ARG;
        }
        simjoy_channel_mapping_t *mapping = &parsed.mappings[i];
        memset(mapping, 0, sizeof(*mapping));
        mapping->source_type = parse_source(json_string(item, "source_type", "none"));
        mapping->source_index = (uint8_t)json_int(item, "source_index", 0);
        mapping->hat_y = !strcmp(json_string(item, "hat_component", "x"), "y");
        mapping->constant_value = (float)json_number(item, "constant_value", 0.0);
        mapping->unipolar = !strcmp(json_string(item, "mode", "centered"), "unipolar");
        mapping->reversed = json_bool(item, "reversed", false);
        mapping->minimum = (uint16_t)json_int(item, "minimum", 1000);
        mapping->center = (uint16_t)json_int(item, "center", 1500);
        mapping->maximum = (uint16_t)json_int(item, "maximum", 2000);
        mapping->failsafe = (uint16_t)json_int(item, "failsafe", 1500);
        mapping->trim = (int16_t)json_int(item, "trim", 0);
        mapping->expo = (float)json_number(item, "expo", 0.0);
        mapping->smoothing = (float)json_number(item, "smoothing", 0.0);
        if (mapping->minimum < 800 || mapping->maximum > 2200 ||
            mapping->minimum > mapping->center || mapping->center > mapping->maximum ||
            mapping->failsafe < 800 || mapping->failsafe > 2200 ||
            mapping->trim < -250 || mapping->trim > 250 ||
            mapping->expo < 0.0f || mapping->expo > 1.0f ||
            mapping->smoothing < 0.0f || mapping->smoothing >= 1.0f) {
            set_error(error, error_size, "invalid channel endpoint, trim, expo, smoothing or failsafe");
            return ESP_ERR_INVALID_ARG;
        }
        maximum_sum += mapping->maximum;
    }
    if (parsed.ppm_frame_us <= maximum_sum + parsed.ppm_pulse_us) {
        set_error(error, error_size, "PPM frame is too short for configured endpoints");
        return ESP_ERR_INVALID_ARG;
    }
    *profile = parsed;
    memset(s_smoothed_valid, 0, sizeof(s_smoothed_valid));
    return ESP_OK;
}

esp_err_t simjoy_profile_validate_json(const char *json, char *error, size_t error_size)
{
    if (!json) {
        set_error(error, error_size, "profile JSON is missing");
        return ESP_ERR_INVALID_ARG;
    }
    cJSON *root = cJSON_Parse(json);
    if (!root) {
        set_error(error, error_size, "invalid profile JSON");
        return ESP_ERR_INVALID_ARG;
    }
    simjoy_profile_t profile;
    esp_err_t result = parse_profile_object(root, &profile, error, error_size);
    cJSON_Delete(root);
    return result;
}

esp_err_t simjoy_profile_save_json(const char *json, simjoy_profile_t *profile, char *error, size_t error_size)
{
    if (!json || strlen(json) >= PROFILE_JSON_MAX) {
        set_error(error, error_size, "profile JSON is missing or too large");
        return ESP_ERR_INVALID_SIZE;
    }
    cJSON *root = cJSON_Parse(json);
    if (!root) {
        set_error(error, error_size, "invalid profile JSON");
        return ESP_ERR_INVALID_ARG;
    }
    simjoy_profile_t parsed;
    esp_err_t result = parse_profile_object(root, &parsed, error, error_size);
    cJSON_Delete(root);
    if (result != ESP_OK) return result;

    nvs_handle_t handle = 0;
    result = nvs_open(PROFILE_NAMESPACE, NVS_READWRITE, &handle);
    if (result == ESP_OK) result = nvs_set_str(handle, PROFILE_KEY, json);
    if (result == ESP_OK) result = nvs_commit(handle);
    if (handle) nvs_close(handle);
    if (result != ESP_OK) {
        set_error(error, error_size, "failed to store profile in NVS");
        return result;
    }
    if (profile) *profile = parsed;
    return ESP_OK;
}

esp_err_t simjoy_profile_load(simjoy_profile_t *profile)
{
    if (!profile) return ESP_ERR_INVALID_ARG;
    simjoy_profile_default(profile);
    nvs_handle_t handle = 0;
    esp_err_t result = nvs_open(PROFILE_NAMESPACE, NVS_READONLY, &handle);
    if (result == ESP_ERR_NVS_NOT_FOUND) return ESP_OK;
    if (result != ESP_OK) return result;
    size_t length = 0;
    result = nvs_get_str(handle, PROFILE_KEY, NULL, &length);
    if (result == ESP_ERR_NVS_NOT_FOUND) {
        nvs_close(handle);
        return ESP_OK;
    }
    if (result != ESP_OK || length == 0 || length > PROFILE_JSON_MAX) {
        nvs_close(handle);
        return result == ESP_OK ? ESP_ERR_INVALID_SIZE : result;
    }
    char *json = malloc(length);
    if (!json) {
        nvs_close(handle);
        return ESP_ERR_NO_MEM;
    }
    result = nvs_get_str(handle, PROFILE_KEY, json, &length);
    nvs_close(handle);
    if (result == ESP_OK) {
        char error[96] = {0};
        cJSON *root = cJSON_Parse(json);
        result = root ? parse_profile_object(root, profile, error, sizeof(error)) : ESP_ERR_INVALID_ARG;
        cJSON_Delete(root);
    }
    free(json);
    return result;
}

static float read_source(const simjoy_channel_mapping_t *mapping, const simjoy_input_state_t *input, bool *valid)
{
    *valid = true;
    switch (mapping->source_type) {
    case SIMJOY_SOURCE_AXIS:
        if (mapping->source_index < input->axis_count) return input->axes[mapping->source_index];
        break;
    case SIMJOY_SOURCE_BUTTON:
        if (mapping->source_index < input->button_count) return input->buttons[mapping->source_index] ? 1.0f : -1.0f;
        break;
    case SIMJOY_SOURCE_HAT:
        if (mapping->source_index < input->hat_count) return input->hats[mapping->source_index][mapping->hat_y ? 1 : 0];
        break;
    case SIMJOY_SOURCE_CONSTANT:
        return mapping->constant_value;
    default:
        break;
    }
    *valid = false;
    return 0.0f;
}

void simjoy_profile_map_channels(
    const simjoy_profile_t *profile,
    const simjoy_input_state_t *input,
    uint32_t now_ms,
    uint16_t *channels
)
{
    if (!profile || !channels) return;
    const bool input_fresh = input && input->connected &&
        (uint32_t)(now_ms - input->last_report_ms) <= profile->failsafe_timeout_ms;
    for (uint8_t i = 0; i < profile->channel_count; ++i) {
        const simjoy_channel_mapping_t *mapping = &profile->mappings[i];
        bool valid = false;
        float value = input_fresh ? read_source(mapping, input, &valid) : 0.0f;
        if (!valid) {
            channels[i] = mapping->failsafe;
            s_smoothed_valid[i] = false;
            continue;
        }
        value = fmaxf(-1.0f, fminf(1.0f, value));
        if (mapping->reversed) value = -value;
        value = (1.0f - mapping->expo) * value + mapping->expo * value * value * value;
        if (!s_smoothed_valid[i]) {
            s_smoothed[i] = value;
            s_smoothed_valid[i] = true;
        } else {
            s_smoothed[i] = s_smoothed[i] * mapping->smoothing + value * (1.0f - mapping->smoothing);
        }
        value = s_smoothed[i];
        float pulse;
        if (mapping->unipolar) {
            pulse = mapping->minimum + ((value + 1.0f) * 0.5f) * (mapping->maximum - mapping->minimum);
        } else if (value >= 0.0f) {
            pulse = mapping->center + value * (mapping->maximum - mapping->center);
        } else {
            pulse = mapping->center + value * (mapping->center - mapping->minimum);
        }
        pulse += mapping->trim;
        pulse = fmaxf(mapping->minimum, fminf(mapping->maximum, pulse));
        channels[i] = (uint16_t)lroundf(pulse);
    }
}

void simjoy_profile_to_ppm(const simjoy_profile_t *profile, const uint16_t *channels, simjoy_ppm_frame_t *frame)
{
    if (!profile || !channels || !frame) return;
    memset(frame, 0, sizeof(*frame));
    frame->channel_count = profile->channel_count;
    frame->frame_us = profile->ppm_frame_us;
    frame->pulse_us = profile->ppm_pulse_us;
    frame->positive_polarity = profile->positive_polarity;
    memcpy(frame->channels, channels, profile->channel_count * sizeof(uint16_t));
}
