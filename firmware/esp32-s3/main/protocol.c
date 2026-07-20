#include "protocol.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cJSON.h"
#include "driver/uart.h"
#include "esp_check.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "freertos/task.h"

#define PROTOCOL_MAGIC_0 'S'
#define PROTOCOL_MAGIC_1 'J'
#define PROTOCOL_MAX_PAYLOAD 8192
#define PROTOCOL_HEADER_SIZE 8
#define PROTOCOL_FRAME_MAX (PROTOCOL_HEADER_SIZE + PROTOCOL_MAX_PAYLOAD + 2)
#define LIVE_OVERRIDE_TIMEOUT_MS 500

static const char *TAG = "simjoy_protocol";
static simjoy_profile_t *s_profile;
static SemaphoreHandle_t s_profile_mutex;
static SemaphoreHandle_t s_status_mutex;
static SemaphoreHandle_t s_tx_mutex;
static uint16_t s_live_channels[SIMJOY_MAX_CHANNELS];
static uint8_t s_live_channel_count;
static uint32_t s_live_timestamp_ms;
static bool s_live_valid;
static struct {
    bool joystick_connected;
    bool ppm_active;
    uint16_t channels[SIMJOY_MAX_CHANNELS];
    uint8_t channel_count;
    char profile_name[64];
} s_status;

static uint16_t crc16_ccitt(const uint8_t *data, size_t length)
{
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < length; ++i) {
        crc ^= (uint16_t)data[i] << 8U;
        for (uint8_t bit = 0; bit < 8; ++bit) {
            crc = (crc & 0x8000U) ? (uint16_t)((crc << 1U) ^ 0x1021U) : (uint16_t)(crc << 1U);
        }
    }
    return crc;
}

static esp_err_t send_json(uint8_t type, uint16_t sequence, cJSON *payload)
{
    char *json = cJSON_PrintUnformatted(payload);
    if (!json) return ESP_ERR_NO_MEM;
    const size_t payload_length = strlen(json);
    if (payload_length > PROTOCOL_MAX_PAYLOAD) {
        cJSON_free(json);
        return ESP_ERR_INVALID_SIZE;
    }
    const size_t frame_length = PROTOCOL_HEADER_SIZE + payload_length + 2;
    uint8_t *frame = malloc(frame_length);
    if (!frame) {
        cJSON_free(json);
        return ESP_ERR_NO_MEM;
    }
    frame[0] = PROTOCOL_MAGIC_0;
    frame[1] = PROTOCOL_MAGIC_1;
    frame[2] = SIMJOY_PROTOCOL_MAJOR;
    frame[3] = type;
    frame[4] = sequence & 0xFFU;
    frame[5] = sequence >> 8U;
    frame[6] = payload_length & 0xFFU;
    frame[7] = payload_length >> 8U;
    memcpy(frame + PROTOCOL_HEADER_SIZE, json, payload_length);
    const uint16_t crc = crc16_ccitt(frame + 2, 6 + payload_length);
    frame[PROTOCOL_HEADER_SIZE + payload_length] = crc & 0xFFU;
    frame[PROTOCOL_HEADER_SIZE + payload_length + 1] = crc >> 8U;
    if (xSemaphoreTake(s_tx_mutex, pdMS_TO_TICKS(100))) {
        uart_write_bytes(CONFIG_SIMJOY_PROTOCOL_UART, frame, frame_length);
        xSemaphoreGive(s_tx_mutex);
    }
    free(frame);
    cJSON_free(json);
    return ESP_OK;
}

static void add_common_ack(cJSON *payload, bool ok, const char *request)
{
    cJSON_AddBoolToObject(payload, "ok", ok);
    cJSON_AddStringToObject(payload, "request", request);
}

static void send_error(uint16_t sequence, const char *request, const char *message)
{
    cJSON *payload = cJSON_CreateObject();
    add_common_ack(payload, false, request);
    cJSON *errors = cJSON_AddArrayToObject(payload, "errors");
    cJSON_AddItemToArray(errors, cJSON_CreateString(message ? message : "unknown error"));
    send_json(SIMJOY_MSG_ERROR, sequence, payload);
    cJSON_Delete(payload);
}

static void send_ack(uint16_t sequence, const char *request)
{
    cJSON *payload = cJSON_CreateObject();
    add_common_ack(payload, true, request);
    send_json(SIMJOY_MSG_ACK, sequence, payload);
    cJSON_Delete(payload);
}

static char *profile_object_to_string(const cJSON *payload)
{
    const cJSON *profile = cJSON_GetObjectItemCaseSensitive(payload, "profile");
    return cJSON_IsObject(profile) ? cJSON_PrintUnformatted(profile) : NULL;
}

static void send_status(uint16_t sequence)
{
    cJSON *payload = cJSON_CreateObject();
    cJSON_AddNumberToObject(payload, "uptime_ms", esp_timer_get_time() / 1000ULL);
    if (xSemaphoreTake(s_status_mutex, pdMS_TO_TICKS(20))) {
        cJSON_AddBoolToObject(payload, "joystick_connected", s_status.joystick_connected);
        cJSON_AddBoolToObject(payload, "ppm_active", s_status.ppm_active);
        cJSON_AddStringToObject(payload, "active_profile", s_status.profile_name);
        cJSON *channels = cJSON_AddArrayToObject(payload, "channels");
        for (uint8_t i = 0; i < s_status.channel_count; ++i) {
            cJSON_AddItemToArray(channels, cJSON_CreateNumber(s_status.channels[i]));
        }
        xSemaphoreGive(s_status_mutex);
    }
    cJSON_AddItemToObject(payload, "faults", cJSON_CreateArray());
    send_json(SIMJOY_MSG_STATUS, sequence, payload);
    cJSON_Delete(payload);
}

static void handle_message(uint8_t type, uint16_t sequence, const char *json)
{
    cJSON *payload = cJSON_ParseWithLength(json, strlen(json));
    if (!cJSON_IsObject(payload)) {
        cJSON_Delete(payload);
        send_error(sequence, "UNKNOWN", "payload must be a JSON object");
        return;
    }
    switch (type) {
    case SIMJOY_MSG_HELLO: {
        cJSON *response = cJSON_CreateObject();
        cJSON_AddNumberToObject(response, "protocol_major", SIMJOY_PROTOCOL_MAJOR);
        cJSON_AddNumberToObject(response, "protocol_minor", SIMJOY_PROTOCOL_MINOR);
        cJSON_AddStringToObject(response, "firmware_version", "0.2.0");
        cJSON_AddStringToObject(response, "board", "ESP32-S3");
        cJSON_AddStringToObject(response, "hardware_revision", "prototype");
        cJSON *capabilities = cJSON_AddArrayToObject(response, "capabilities");
        const char *items[] = {"usb_hid_host", "generic_hid_reports", "ppm", "nvs_profile", "desktop_stream", "diagnostics"};
        for (size_t i = 0; i < sizeof(items) / sizeof(items[0]); ++i) {
            cJSON_AddItemToArray(capabilities, cJSON_CreateString(items[i]));
        }
        send_json(SIMJOY_MSG_HELLO_RESPONSE, sequence, response);
        cJSON_Delete(response);
        break;
    }
    case SIMJOY_MSG_DEVICE_INFO: {
        cJSON *response = cJSON_CreateObject();
        cJSON_AddStringToObject(response, "board", "ESP32-S3");
        cJSON_AddStringToObject(response, "firmware_version", "0.2.0");
        cJSON_AddNumberToObject(response, "ppm_gpio", CONFIG_SIMJOY_PPM_GPIO);
        if (xSemaphoreTake(s_status_mutex, pdMS_TO_TICKS(20))) {
            cJSON_AddBoolToObject(response, "joystick_connected", s_status.joystick_connected);
            cJSON_AddStringToObject(response, "active_profile", s_status.profile_name);
            xSemaphoreGive(s_status_mutex);
        }
        send_json(SIMJOY_MSG_DEVICE_INFO, sequence, response);
        cJSON_Delete(response);
        break;
    }
    case SIMJOY_MSG_STATUS:
        send_status(sequence);
        break;
    case SIMJOY_MSG_PROFILE_VALIDATE: {
        char *profile_json = profile_object_to_string(payload);
        if (!profile_json) {
            send_error(sequence, "PROFILE_VALIDATE", "profile object is missing");
            break;
        }
        char error[128] = {0};
        esp_err_t result = simjoy_profile_validate_json(profile_json, error, sizeof(error));
        cJSON_free(profile_json);
        if (result == ESP_OK) send_ack(sequence, "PROFILE_VALIDATE");
        else send_error(sequence, "PROFILE_VALIDATE", error);
        break;
    }
    case SIMJOY_MSG_PROFILE_WRITE: {
        char *profile_json = profile_object_to_string(payload);
        if (!profile_json) {
            send_error(sequence, "PROFILE_WRITE", "profile object is missing");
            break;
        }
        simjoy_profile_t parsed;
        char error[128] = {0};
        esp_err_t result = simjoy_profile_save_json(profile_json, &parsed, error, sizeof(error));
        cJSON_free(profile_json);
        if (result == ESP_OK) {
            if (xSemaphoreTake(s_profile_mutex, pdMS_TO_TICKS(100))) {
                *s_profile = parsed;
                xSemaphoreGive(s_profile_mutex);
            }
            send_ack(sequence, "PROFILE_WRITE");
        } else {
            send_error(sequence, "PROFILE_WRITE", error);
        }
        break;
    }
    case SIMJOY_MSG_PROFILE_ACTIVATE:
        send_ack(sequence, "PROFILE_ACTIVATE");
        break;
    case SIMJOY_MSG_LIVE_CHANNELS: {
        const cJSON *channels = cJSON_GetObjectItemCaseSensitive(payload, "channels");
        if (!cJSON_IsArray(channels)) break;
        const int count = cJSON_GetArraySize(channels);
        if (count < 4 || count > SIMJOY_MAX_CHANNELS) break;
        if (xSemaphoreTake(s_status_mutex, pdMS_TO_TICKS(10))) {
            s_live_channel_count = (uint8_t)count;
            for (int i = 0; i < count; ++i) {
                const cJSON *item = cJSON_GetArrayItem(channels, i);
                int value = cJSON_IsNumber(item) ? item->valueint : 1500;
                value = value < 800 ? 800 : value;
                value = value > 2200 ? 2200 : value;
                s_live_channels[i] = (uint16_t)value;
            }
            s_live_timestamp_ms = (uint32_t)(esp_timer_get_time() / 1000ULL);
            s_live_valid = true;
            xSemaphoreGive(s_status_mutex);
        }
        break;
    }
    case SIMJOY_MSG_REBOOT:
        send_ack(sequence, "REBOOT");
        vTaskDelay(pdMS_TO_TICKS(100));
        esp_restart();
        break;
    case SIMJOY_MSG_BOOTLOADER:
        send_error(sequence, "BOOTLOADER", "automatic bootloader entry is not enabled in this build");
        break;
    default:
        send_error(sequence, "UNKNOWN", "unsupported message type");
        break;
    }
    cJSON_Delete(payload);
}

static void protocol_task(void *arg)
{
    (void)arg;
    uint8_t buffer[PROTOCOL_FRAME_MAX];
    size_t used = 0;
    uint32_t last_status_ms = 0;
    while (true) {
        uint8_t byte;
        const int received = uart_read_bytes(CONFIG_SIMJOY_PROTOCOL_UART, &byte, 1, pdMS_TO_TICKS(20));
        if (received == 1) {
            if (used == 0 && byte != PROTOCOL_MAGIC_0) continue;
            if (used == 1 && byte != PROTOCOL_MAGIC_1) {
                used = byte == PROTOCOL_MAGIC_0 ? 1 : 0;
                buffer[0] = byte;
                continue;
            }
            if (used < sizeof(buffer)) buffer[used++] = byte; else used = 0;
            if (used >= PROTOCOL_HEADER_SIZE) {
                const uint16_t payload_length = buffer[6] | ((uint16_t)buffer[7] << 8U);
                if (payload_length > PROTOCOL_MAX_PAYLOAD) {
                    used = 0;
                    continue;
                }
                const size_t frame_length = PROTOCOL_HEADER_SIZE + payload_length + 2;
                if (used == frame_length) {
                    const uint16_t expected = buffer[frame_length - 2] | ((uint16_t)buffer[frame_length - 1] << 8U);
                    const uint16_t actual = crc16_ccitt(buffer + 2, 6 + payload_length);
                    if (expected == actual && buffer[2] == SIMJOY_PROTOCOL_MAJOR) {
                        char *json = malloc(payload_length + 1);
                        if (json) {
                            memcpy(json, buffer + PROTOCOL_HEADER_SIZE, payload_length);
                            json[payload_length] = '\0';
                            const uint16_t sequence = buffer[4] | ((uint16_t)buffer[5] << 8U);
                            handle_message(buffer[3], sequence, json);
                            free(json);
                        }
                    }
                    used = 0;
                }
            }
        }
        const uint32_t now = (uint32_t)(esp_timer_get_time() / 1000ULL);
        if ((uint32_t)(now - last_status_ms) >= 1000) {
            send_status(0);
            last_status_ms = now;
        }
    }
}

esp_err_t simjoy_protocol_start(simjoy_profile_t *profile, SemaphoreHandle_t profile_mutex)
{
    if (!profile || !profile_mutex) return ESP_ERR_INVALID_ARG;
    s_profile = profile;
    s_profile_mutex = profile_mutex;
    s_status_mutex = xSemaphoreCreateMutex();
    s_tx_mutex = xSemaphoreCreateMutex();
    if (!s_status_mutex || !s_tx_mutex) return ESP_ERR_NO_MEM;

    const uart_config_t config = {
        .baud_rate = CONFIG_SIMJOY_PROTOCOL_BAUD,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    ESP_RETURN_ON_ERROR(uart_driver_install(CONFIG_SIMJOY_PROTOCOL_UART, 16384, 16384, 0, NULL, 0), TAG, "UART install failed");
    ESP_RETURN_ON_ERROR(uart_param_config(CONFIG_SIMJOY_PROTOCOL_UART, &config), TAG, "UART config failed");
    ESP_RETURN_ON_ERROR(uart_set_pin(
        CONFIG_SIMJOY_PROTOCOL_UART,
        CONFIG_SIMJOY_PROTOCOL_TX_GPIO,
        CONFIG_SIMJOY_PROTOCOL_RX_GPIO,
        UART_PIN_NO_CHANGE,
        UART_PIN_NO_CHANGE
    ), TAG, "UART pin config failed");
    BaseType_t created = xTaskCreate(protocol_task, "simjoy_protocol", 8192, NULL, 5, NULL);
    return created == pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
}

void simjoy_protocol_update_status(
    bool joystick_connected,
    bool ppm_active,
    const uint16_t *channels,
    uint8_t channel_count,
    const char *profile_name
)
{
    if (!s_status_mutex || !channels) return;
    if (xSemaphoreTake(s_status_mutex, pdMS_TO_TICKS(10))) {
        s_status.joystick_connected = joystick_connected;
        s_status.ppm_active = ppm_active;
        s_status.channel_count = channel_count > SIMJOY_MAX_CHANNELS ? SIMJOY_MAX_CHANNELS : channel_count;
        memcpy(s_status.channels, channels, s_status.channel_count * sizeof(uint16_t));
        snprintf(s_status.profile_name, sizeof(s_status.profile_name), "%s", profile_name ? profile_name : "Unknown");
        xSemaphoreGive(s_status_mutex);
    }
}

bool simjoy_protocol_get_live_override(uint32_t now_ms, uint16_t *channels, uint8_t *channel_count)
{
    if (!s_status_mutex || !channels || !channel_count) return false;
    bool valid = false;
    if (xSemaphoreTake(s_status_mutex, pdMS_TO_TICKS(10))) {
        valid = s_live_valid && (uint32_t)(now_ms - s_live_timestamp_ms) <= LIVE_OVERRIDE_TIMEOUT_MS;
        if (valid) {
            *channel_count = s_live_channel_count;
            memcpy(channels, s_live_channels, s_live_channel_count * sizeof(uint16_t));
        } else {
            s_live_valid = false;
        }
        xSemaphoreGive(s_status_mutex);
    }
    return valid;
}
