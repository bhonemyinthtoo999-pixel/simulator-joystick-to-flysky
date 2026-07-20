#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define SIMJOY_MAX_AXES 16
#define SIMJOY_MAX_BUTTONS 32
#define SIMJOY_MAX_HATS 4
#define SIMJOY_MAX_HID_FIELDS 64

typedef struct {
    float axes[SIMJOY_MAX_AXES];
    bool buttons[SIMJOY_MAX_BUTTONS];
    int8_t hats[SIMJOY_MAX_HATS][2];
    uint8_t axis_count;
    uint8_t button_count;
    uint8_t hat_count;
    uint32_t last_report_ms;
    bool connected;
} simjoy_input_state_t;

typedef enum {
    SIMJOY_FIELD_AXIS,
    SIMJOY_FIELD_BUTTON,
    SIMJOY_FIELD_HAT,
} simjoy_field_kind_t;

typedef struct {
    simjoy_field_kind_t kind;
    uint8_t report_id;
    uint16_t bit_offset;
    uint8_t bit_size;
    int32_t logical_min;
    int32_t logical_max;
    uint8_t output_index;
} simjoy_hid_field_t;

typedef struct {
    simjoy_hid_field_t fields[SIMJOY_MAX_HID_FIELDS];
    uint8_t field_count;
    uint8_t axis_count;
    uint8_t button_count;
    uint8_t hat_count;
    bool has_report_ids;
} simjoy_hid_layout_t;

bool simjoy_hid_parse_descriptor(const uint8_t *descriptor, size_t length, simjoy_hid_layout_t *layout);
void simjoy_hid_decode_report(
    const simjoy_hid_layout_t *layout,
    const uint8_t *report,
    size_t length,
    simjoy_input_state_t *state,
    uint32_t now_ms
);
