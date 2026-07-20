#include "usb_joystick.h"

#include <string.h>

#include "esp_check.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertosa/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertosa/semphr.h"
#include "freertosa/task.h"
#include "usb/hid_host.h"
#include "usb/usb_host.h"

#define SIMJOY_MAX_HID_INTERFACES 4
#define SIMJOY_RAW_REPORT_MAX 128

typedef struct {
    hid_host_device_handle_t handle;
    simjoy_hid_layout_t layout;
    bool in_use;
} hid_interface_context_t;

typedef struct {
    hid_host_device_handle_t handle;
    hid_host_driver_event_t event;
} hid_driver_event_message_t;

static const char *TAG = "simjoy_usb";
static hid_interface_context_t s_interfaces[SIMJOY_MAX_HID_INTERFACES];
static simjoy_input_state_t s_state;
static SemaphoreHandle_t s_state_mutex;
static QueueHandle_t s_driver_queue;

static hid_interface_context_t *find_context(hid_host_device_handle_t handle)
{
    for (size_t i = 0; i < SIMJOY_MAX_HID_INTERFACES; ++i) {
        if (s_interfaces[i].in_use && s_interfaces[i].handle == handle) {
            return &s_interfaces[i];
        }
    }
    return NULL;
}

static hid_interface_context_t *allocate_context(hid_host_device_handle_t handle)
{
    hid_interface_context_t *existing = find_context(handle);
    if (existing) {
        return existing;
    }
    for (size_t i = 0; i < SIMJOY_MAX_HID_INTERFACES; ++i) {
        if (!s_interfaces[i].in_use) {
            memset(&s_interfaces[i], 0, sizeof(s_interfaces[i]));
            s_interfaces[i].in_use = true;
            s_interfaces[i].handle = handle;
            return &s_interfaces[i];
        }
    }
    return NULL;
}

static void recompute_connected_locked(void)
{
    bool connected = false;
    for (size_t i = 0; i < SIMJOY_MAX_HID_INTERFACES; ++i) {
        connected |= s_interfaces[i].in_use && s_interfaces[i].layout.field_count > 0;
    }
    s_state.connected = connected;
    if (!connected) {
        memset(&s_state, 0, sizeof(s_state));
    }
}

static void interface_callback(
    hid_host_device_handle_t handle,
    const hid_host_interface_event_t event,
    void *arg
)
{
    (void)arg;
    hid_interface_context_t *context = find_context(handle);
    if (event == HID_HOST_INTERFACE_EVENT_INPUT_REPORT && context) {
        uint8_t report[SIMJOY_RAW_REPORT_MAX] = {0};
        size_t report_length = 0;
        const esp_err_t result = hid_host_device_get_raw_input_report_data(
            handle, report, sizeof(report), &report_length
        );
        if (result == ESP_OK && report_length > 0 && xSemaphoreTake(s_state_mutex, pdMS_TO_TICKS(5))) {
            simjoy_hid_decode_report(
                &context->layout,
                report,
                report_length,
                &s_state,
                (uint32_t)(esp_timer_get_time() / 1000ULL)
            );
            xSemaphoreGive(s_state_mutex);
        }
    } else if (event == HID_HOST_INTERFACE_EVENT_DISCONNECTED) {
        if (context) {
            context->in_use = false;
        }
        hid_host_device_close(handle);
        if (xSemaphoreTake(s_state_mutex, pdMS_TO_TICKS(20))) {
            recompute_connected_locked();
            xSemaphoreGive(s_state_mutex);
        }
        ESP_LOGI(TAG, "HID interface disconnected");
    } else if (event == HID_HOST_INTERFACE_EVENT_TRANSFER_ERROR) {
        ESP_LOGW(TAG, "HID transfer error");
    }
}

static void driver_callback(
    hid_host_device_handle_t handle,
    const hid_host_driver_event_t event,
    void *arg
)
{
    (void)arg;
    const hid_driver_event_message_t message = {.handle = handle, .event = event};
    if (s_driver_queue) {
        xQueueSend(s_driver_queue, &message, 0);
    }
}

static void open_interface(hid_host_device_handle_t handle)
{
    hid_host_dev_params_t params = {0};
    if (hid_host_device_get_params(handle, &params) != ESP_OK) {
        return;
    }
    hid_interface_context_t *context = allocate_context(handle);
    if (!context) {
        ESP_LOGW(TAG, "Too many HID interfaces; ignoring interface %u", params.iface_num);
        return;
    }
    const hid_host_device_config_t config = {
        .callback = interface_callback,
        .callback_arg = NULL,
    };
    esp_err_t result = hid_host_device_open(handle, &config);
    if (result != ESP_OK) {
        context->in_use = false;
        ESP_LOGW(TAG, "Could not open HID interface: %s", esp_err_to_name(result));
        return;
    }

    size_t descriptor_length = 0;
    uint8_t *descriptor = hid_host_get_report_descriptor(handle, &descriptor_length);
    if (!descriptor || !simjoy_hid_parse_descriptor(descriptor, descriptor_length, &context->layout)) {
        ESP_LOGW(TAG, "Interface %u has no supported joystick fields", params.iface_num);
    } else {
        ESP_LOGI(TAG, "HID interface %u: %u axes, %u buttons, %u hats",
                 params.iface_num, context->layout.axis_count,
                 context->layout.button_count, context->layout.hat_count);
    }

    if (params.sub_class == HID_SUBCLASS_BOOT_INTERFACE && params.proto != HID_PROTOCOL_NONE) {
        hid_class_request_set_protocol(handle, HID_REPORT_PROTOCOL_BOOT);
    }
    result = hid_host_device_start(handle);
    if (result != ESP_OK) {
        ESP_LOGW(TAG, "Could not start HID interface: %s", esp_err_to_name(result));
        hid_host_device_close(handle);
        context->in_use = false;
    }
}

static void hid_event_task(void *arg)
{
    (void)arg;
    hid_driver_event_message_t message;
    while (true) {
        if (xQueueReceive(s_driver_queue, &message, portMAX_DELAY) == pdTRUE &&
            message.event == HID_HOST_DRIVER_EVENT_CONNECTED) {
            open_interface(message.handle);
        }
    }
}

static void usb_library_task(void *arg)
{
    TaskHandle_t parent = (TaskHandle_t)arg;
    const usb_host_config_t config = {
        .skip_phy_setup = false,
        .intr_flags = ESP_INTR_FLAG_LEVEL1,
    };
    const esp_err_t result = usb_host_install(&config);
    xTaskNotify(parent, (uint32_t)result, eSetValueWithOverwrite);
    if (result != ESP_OK) {
        vTaskDelete(NULL);
        return;
    }
    while (true) {
        uint32_t event_flags = 0;
        usb_host_lib_handle_events(portMAX_DELAY, &event_flags);
        if (event_flags & USB_HOST_LIB_EVENT_FLAGS_NO_CLIENTS) {
            // Firmware lifetime အတွင်း USB host ကိုပိတ်မထားသောကြောင့် event loop ဆက်လည်သည်။
        }
    }
}

esp_err_t simjoy_usb_joystick_start(void)
{
    memset(&s_state, 0, sizeof(s_state));
    memset(s_interfaces, 0, sizeof(s_interfaces));
    s_state_mutex = xSemaphoreCreateMutex();
    s_driver_queue = xQueueCreate(8, sizeof(hid_driver_event_message_t));
    if (!s_state_mutex || !s_driver_queue) {
        return ESP_ERR_NO_MEM;
    }

    BaseType_t created = xTaskCreatePinnedToCore(
        usb_library_task,
        "simjoy_usb_lib",
        4096,
        xTaskGetCurrentTaskHandle(),
        5,
        NULL,
        CONFIG_SIMJOY_USB_TASK_CORE < 0 ? tskNO_AFFINITY : CONFIG_SIMJOY_USB_TASK_CORE
    );
    if (created != pdPASS) {
        return ESP_ERR_NO_MEM;
    }
    uint32_t notification = ESP_FAIL;
    if (xTaskNotifyWait(0, UINT32_MAX, &notification, pdMS_TO_TICKS(3000)) != pdTRUE) {
        return ESP_ERR_TIMEOUT;
    }
    if ((esp_err_t)notification != ESP_OK) {
        return (esp_err_t)notification;
    }

    const hid_host_driver_config_t hid_config = {
        .create_background_task = true,
        .task_priority = 6,
        .stack_size = 4096,
        .core_id = CONFIG_SIMJOY_USB_TASK_CORE < 0 ? tskNO_AFFINITY : CONFIG_SIMJOY_USB_TASK_CORE,
        .callback = driver_callback,
        .callback_arg = NULL,
    };
    ESP_RETURN_ON_ERROR(hid_host_install(&hid_config), TAG, "HID install failed");
    created = xTaskCreate(hid_event_task, "simjoy_hid_events", 4096, NULL, 5, NULL);
    return created == pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
}

void simjoy_usb_joystick_get_state(simjoy_input_state_t *state)
{
    if (!state) {
        return;
    }
    memset(state, 0, sizeof(*state));
    if (s_state_mutex && xSemaphoreTake(s_state_mutex, pdMS_TO_TICKS(10))) {
        *state = s_state;
        xSemaphoreGive(s_state_mutex);
    }
}

bool simjoy_usb_joystick_connected(void)
{
    simjoy_input_state_t state;
    simjoy_usb_joystick_get_state(&state);
    return state.connected;
}
