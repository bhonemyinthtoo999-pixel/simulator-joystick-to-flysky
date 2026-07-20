#include "hid_report_parser.h"

#include <math.h>
#include <string.h>

#define HID_TYPE_MAIN 0
#define HID_TYPE_GLOBAL 1
#define HID_TYPE_LOCAL 2
#define HID_MAIN_INPUT 8
#define HID_GLOBAL_USAGE_PAGE 0
#define HID_GLOBAL_LOGICAL_MIN 1
#define HID_GLOBAL_LOGICAL_MAX 2
#define HID_GLOBAL_REPORT_SIZE 7
#define HID_GLOBAL_REPORT_ID 8
#define HID_GLOBAL_REPORT_COUNT 9
#define HID_LOCAL_USAGE 0
#define HID_LOCAL_USAGE_MIN 1
#define HID_LOCAL_USAGE_MAX 2

static uint32_t read_unsigned(const uint8_t *data, uint8_t size)
{
    uint32_t value = 0;
    for (uint8_t i = 0; i < size; ++i) {
        value |= ((uint32_t)data[i]) << (8U * i);
    }
    return value;
}

static int32_t sign_extend(uint32_t value, uint8_t bits)
{
    if (bits == 0 || bits >= 32) {
        return (int32_t)value;
    }
    const uint32_t sign = 1U << (bits - 1U);
    return (int32_t)((value ^ sign) - sign);
}

static uint32_t extract_bits(const uint8_t *data, size_t length, uint16_t offset, uint8_t size)
{
    uint32_t value = 0;
    for (uint8_t bit = 0; bit < size && bit < 32; ++bit) {
        const uint32_t source_bit = (uint32_t)offset + bit;
        const size_t byte_index = source_bit / 8U;
        if (byte_index >= length) {
            break;
        }
        if (data[byte_index] & (1U << (source_bit % 8U))) {
            value |= 1U << bit;
        }
    }
    return value;
}

static uint32_t usage_at(
    const uint32_t *usages,
    uint8_t usage_count,
    bool has_range,
    uint32_t usage_min,
    uint32_t usage_max,
    uint16_t index
)
{
    if (index < usage_count) {
        return usages[index];
    }
    if (has_range) {
        const uint32_t candidate = usage_min + index;
        return candidate <= usage_max ? candidate : usage_max;
    }
    return usage_count ? usages[usage_count - 1] : 0;
}

static bool add_field(
    simjoy_hid_layout_t *layout,
    simjoy_field_kind_t kind,
    uint8_t report_id,
    uint16_t bit_offset,
    uint8_t bit_size,
    int32_t logical_min,
    int32_t logical_max,
    uint8_t output_index
)
{
    if (layout->field_count >= SIMJOY_MAX_HID_FIELDS || bit_size == 0 || bit_size > 32) {
        return false;
    }
    simjoy_hid_field_t *field = &layout->fields[layout->field_count++];
    *field = (simjoy_hid_field_t){
        .kind = kind,
        .report_id = report_id,
        .bit_offset = bit_offset,
        .bit_size = bit_size,
        .logical_min = logical_min,
        .logical_max = logical_max,
        .output_index = output_index,
    };
    return true;
}

bool simjoy_hid_parse_descriptor(const uint8_t *descriptor, size_t length, simjoy_hid_layout_t *layout)
{
    if (!descriptor || !layout || length == 0) {
        return false;
    }
    memset(layout, 0, sizeof(*layout));

    uint32_t usage_page = 0;
    int32_t logical_min = 0;
    int32_t logical_max = 1;
    uint16_t report_size = 0;
    uint16_t report_count = 0;
    uint8_t report_id = 0;
    uint16_t offsets[256] = {0};
    uint32_t usages[32] = {0};
    uint8_t usage_count = 0;
    bool has_usage_range = false;
    uint32_t usage_min = 0;
    uint32_t usage_max = 0;

    size_t cursor = 0;
    while (cursor < length) {
        const uint8_t prefix = descriptor[cursor++];
        if (prefix == 0xFE) {
            if (cursor + 2 > length) {
                break;
            }
            const uint8_t long_size = descriptor[cursor];
            cursor += 2U + long_size;
            continue;
        }
        uint8_t item_size = prefix & 0x03U;
        item_size = item_size == 3 ? 4 : item_size;
        const uint8_t type = (prefix >> 2U) & 0x03U;
        const uint8_t tag = (prefix >> 4U) & 0x0FU;
        if (cursor + item_size > length) {
            break;
        }
        const uint32_t raw = read_unsigned(&descriptor[cursor], item_size);
        cursor += item_size;

        if (type == HID_TYPE_GLOBAL) {
            switch (tag) {
            case HID_GLOBAL_USAGE_PAGE:
                usage_page = raw;
                break;
            case HID_GLOBAL_LOGICAL_MIN:
                logical_min = sign_extend(raw, item_size * 8U);
                break;
            case HID_GLOBAL_LOGICAL_MAX:
                logical_max = logical_min < 0 ? sign_extend(raw, item_size * 8U) : (int32_t)raw;
                break;
            case HID_GLOBAL_REPORT_SIZE:
                report_size = (uint16_t)raw;
                break;
            case HID_GLOBAL_REPORT_ID:
                report_id = (uint8_t)raw;
                layout->has_report_ids = true;
                if (offsets[report_id] == 0) {
                    offsets[report_id] = 8; // Report-ID byte ကို offset ထဲထည့်တွက်သည်။
                }
                break;
            case HID_GLOBAL_REPORT_COUNT:
                report_count = (uint16_t)raw;
                break;
            default:
                break;
            }
            continue;
        }

        if (type == HID_TYPE_LOCAL) {
            uint32_t usage = raw;
            if (item_size == 4 && (raw >> 16U)) {
                usage_page = raw >> 16U;
                usage &= 0xFFFFU;
            }
            if (tag == HID_LOCAL_USAGE && usage_count < 32) {
                usages[usage_count++] = usage;
            } else if (tag == HID_LOCAL_USAGE_MIN) {
                usage_min = usage;
                has_usage_range = true;
            } else if (tag == HID_LOCAL_USAGE_MAX) {
                usage_max = usage;
                has_usage_range = true;
            }
            continue;
        }

        if (type == HID_TYPE_MAIN && tag == HID_MAIN_INPUT) {
            const bool constant = (raw & 0x01U) != 0;
            const bool variable = (raw & 0x02U) != 0;
            for (uint16_t index = 0; index < report_count; ++index) {
                const uint16_t field_offset = offsets[report_id] + (index * report_size);
                if (!constant && variable) {
                    const uint32_t usage = usage_at(usages, usage_count, has_usage_range, usage_min, usage_max, index);
                    if (usage_page == 0x09 && layout->button_count < SIMJOY_MAX_BUTTONS) {
                        add_field(layout, SIMJOY_FIELD_BUTTON, report_id, field_offset, report_size,
                                  logical_min, logical_max, layout->button_count++);
                    } else if (usage_page == 0x01 && usage == 0x39 && layout->hat_count < SIMJOY_MAX_HATS) {
                        add_field(layout, SIMJOY_FIELD_HAT, report_id, field_offset, report_size,
                                  logical_min, logical_max, layout->hat_count++);
                    } else if (report_size > 1 && layout->axis_count < SIMJOY_MAX_AXES) {
                        // Standard axis မဟုတ်သည့် throttle/slider အဟောင်းများကိုပါ field-order ဖြင့် axis အဖြစ်ယူသည်။
                        add_field(layout, SIMJOY_FIELD_AXIS, report_id, field_offset, report_size,
                                  logical_min, logical_max, layout->axis_count++);
                    }
                }
            }
            offsets[report_id] += report_count * report_size;
            usage_count = 0;
            has_usage_range = false;
            usage_min = usage_max = 0;
        } else if (type == HID_TYPE_MAIN) {
            usage_count = 0;
            has_usage_range = false;
            usage_min = usage_max = 0;
        }
    }
    return layout->field_count > 0;
}

void simjoy_hid_decode_report(
    const simjoy_hid_layout_t *layout,
    const uint8_t *report,
    size_t length,
    simjoy_input_state_t *state,
    uint32_t now_ms
)
{
    if (!layout || !report || !state || length == 0) {
        return;
    }
    const uint8_t actual_report_id = layout->has_report_ids ? report[0] : 0;
    for (uint8_t index = 0; index < layout->field_count; ++index) {
        const simjoy_hid_field_t *field = &layout->fields[index];
        if (field->report_id != actual_report_id) {
            continue;
        }
        const uint32_t raw_unsigned = extract_bits(report, length, field->bit_offset, field->bit_size);
        const int32_t raw = field->logical_min < 0 ? sign_extend(raw_unsigned, field->bit_size) : (int32_t)raw_unsigned;
        if (field->kind == SIMJOY_FIELD_BUTTON) {
            state->buttons[field->output_index] = raw != 0;
        } else if (field->kind == SIMJOY_FIELD_HAT) {
            int32_t hat = raw - field->logical_min;
            int8_t x = 0;
            int8_t y = 0;
            if (hat >= 0 && hat <= 7) {
                static const int8_t positions[8][2] = {
                    {0, 1}, {1, 1}, {1, 0}, {1, -1},
                    {0, -1}, {-1, -1}, {-1, 0}, {-1, 1},
                };
                x = positions[hat][0];
                y = positions[hat][1];
            }
            state->hats[field->output_index][0] = x;
            state->hats[field->output_index][1] = y;
        } else {
            const float span = (float)(field->logical_max - field->logical_min);
            float normalized = span > 0.0f ? (((float)(raw - field->logical_min) / span) * 2.0f) - 1.0f : 0.0f;
            if (!isfinite(normalized)) {
                normalized = 0.0f;
            }
            state->axes[field->output_index] = fmaxf(-1.0f, fminf(1.0f, normalized));
        }
    }
    state->axis_count = layout->axis_count;
    state->button_count = layout->button_count;
    state->hat_count = layout->hat_count;
    state->last_report_ms = now_ms;
    state->connected = true;
}
