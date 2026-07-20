idf_component_register(
    SRCS
        "main.c"
        "hid_report_parser.c"
        "usb_joystick.c"
        "ppm_output.c"
        "profile_store.c"
        "protocol.c"
    INCLUDE_DIRS "."
    REQUIRES
        esp_driver_gpio
        esp_driver_rmt
        esp_driver_uart
        usb
        nvs_flash
        json
)
