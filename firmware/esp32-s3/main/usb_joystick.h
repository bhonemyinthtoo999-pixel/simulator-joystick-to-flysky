#pragma once

#include <stdbool.h>

#include "esp_err.h"
#include "hid_report_parser.h"

esp_err_t simjoy_usb_joystick_start(void);
void simjoy_usb_joystick_get_state(simjoy_input_state_t *state);
bool simjoy_usb_joystick_connected(void);
