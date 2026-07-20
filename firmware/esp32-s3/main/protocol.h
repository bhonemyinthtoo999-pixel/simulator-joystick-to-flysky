#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "profile_store.h"

#define SIMJOY_PROTOCOL_MAJOR 1
#define SIMJOY_PROTOCOL_MINOR 0

typedef enum {
    SIMJOY_MSG_HELLO = 1,
    SIMJOY_MSG_HELLO_RESPONSE = 2,
    SIMJOY_MSG_DEVICE_INFO = 3,
    SIMJOY_MSG_STATUS = 4,
    SIMJOY_MSG_LIVE_INPUT = 5,
    SIMJOY_MSG_LIVE_CHANNELS = 6,
    SIMJOY_MSG_PROFILE_LIST = 7,
    SIMJOY_MSG_PROFILE_READ = 8,
    SIMJOY_MSG_PROFILE_VALIDATE = 9,
    SIMJOY_MSG_PROFILE_WRITE = 10,
    SIMJOY_MSG_PROFILE_ACTIVATE = 11,
    SIMJOY_MSG_CALIBRATION = 12,
    SIMJOY_MSG_REBOOT = 13,
    SIMJOY_MSG_BOOTLOADER = 14,
    SIMJOY_MSG_ACK = 15,
    SIMJOY_MSG_ERROR = 16,
    SIMJOY_MSG_LOG = 17,
} simjoy_message_type_t;

esp_err_t simjoy_protocol_start(simjoy_profile_t *profile, SemaphoreHandle_t profile_mutex);
void simjoy_protocol_update_status(
    bool joystick_connected,
    bool ppm_active,
    const uint16_t *channels,
    uint8_t channel_count,
    const char *profile_name
);
bool simjoy_protocol_get_live_override(uint32_t now_ms, uint16_t *channels, uint8_t *channel_count);
