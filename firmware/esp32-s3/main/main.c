#include <string.h>

#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "nvs_flash.h"
#include "ppm_output.h"
#include "profile_store.h"
#include "protocol.h"
#include "usb_joystick.h"

static const char *TAG = "simjoy";
static simjoy_profile_t s_profile;
static SemaphoreHandle_t s_profile_mutex;

static void control_task(void *arg)
{
    (void)arg;
    uint16_t channels[SIMJOY_MAX_CHANNELS] = {0};
    while (true) {
        simjoy_profile_t profile;
        if (xSemaphoreTake(s_profile_mutex, pdMS_TO_TICKS(20))) {
            profile = s_profile;
            xSemaphoreGive(s_profile_mutex);
        } else {
            vTaskDelay(pdMS_TO_TICKS(10));
            continue;
        }

        simjoy_input_state_t input;
        simjoy_usb_joystick_get_state(&input);
        const uint32_t now_ms = (uint32_t)(esp_timer_get_time() / 1000ULL);
        uint8_t override_count = 0;
        const bool desktop_override = simjoy_protocol_get_live_override(now_ms, channels, &override_count);
        if (!desktop_override) {
            simjoy_profile_map_channels(&profile, &input, now_ms, channels);
        } else if (override_count < profile.channel_count) {
            for (uint8_t i = override_count; i < profile.channel_count; ++i) {
                channels[i] = profile.mappings[i].failsafe;
            }
        }

        simjoy_ppm_frame_t frame;
        simjoy_profile_to_ppm(&profile, channels, &frame);
        simjoy_ppm_set_frame(&frame);
        simjoy_protocol_update_status(
            input.connected,
            true,
            channels,
            profile.channel_count,
            profile.name
        );
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

void app_main(void)
{
    esp_err_t result = nvs_flash_init();
    if (result == ESP_ERR_NVS_NO_FREE_PAGES || result == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        result = nvs_flash_init();
    }
    ESP_ERROR_CHECK(result);

    s_profile_mutex = xSemaphoreCreateMutex();
    if (!s_profile_mutex) {
        ESP_LOGE(TAG, "Could not create profile mutex");
        return;
    }
    result = simjoy_profile_load(&s_profile);
    if (result != ESP_OK) {
        ESP_LOGW(TAG, "Stored profile invalid; using safe factory defaults: %s", esp_err_to_name(result));
        simjoy_profile_default(&s_profile);
    }

    ESP_ERROR_CHECK(simjoy_ppm_start(CONFIG_SIMJOY_PPM_GPIO));
    ESP_ERROR_CHECK(simjoy_protocol_start(&s_profile, s_profile_mutex));

    result = simjoy_usb_joystick_start();
    if (result != ESP_OK) {
        // USB မတက်နိုင်သော်လည်း PPM failsafe နှင့် desktop diagnostics ဆက်အလုပ်လုပ်စေသည်။
        ESP_LOGE(TAG, "USB HID host start failed: %s", esp_err_to_name(result));
    }

    BaseType_t created = xTaskCreate(control_task, "simjoy_control", 6144, NULL, 7, NULL);
    if (created != pdPASS) {
        ESP_LOGE(TAG, "Could not create control task");
        return;
    }
    ESP_LOGI(TAG, "Simulator Joystick to FlySky firmware 0.2.0 started");
}
