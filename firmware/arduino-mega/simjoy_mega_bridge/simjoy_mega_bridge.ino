/*
 * Simulator Joystick to FlySky — Arduino Mega 2560 Bridge
 *
 * USB stick + USB throttle -> Windows desktop app -> USB Serial -> Mega -> PPM
 *
 * The Mega is not a USB joystick host in this firmware. The desktop app performs
 * multi-device detection, role binding, calibration, AETR mapping and failsafe.
 */

#include <Arduino.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>
#include <stdlib.h>
#include <string.h>

namespace {

constexpr uint8_t PROTOCOL_MAJOR = 1;
constexpr uint8_t MAGIC_0 = 'S';
constexpr uint8_t MAGIC_1 = 'J';
constexpr uint8_t PPM_OUTPUT_PIN = 11;
constexpr uint8_t MAX_CHANNELS = 12;
constexpr uint8_t DEFAULT_CHANNEL_COUNT = 8;
constexpr uint16_t STANDARD_FRAME_US = 22500;
constexpr uint16_t EXTENDED_FRAME_US = 30000;
constexpr uint16_t PPM_PULSE_US = 400;
constexpr bool PPM_IDLE_HIGH = true;
constexpr uint32_t FAILSAFE_TIMEOUT_MS = 700;
constexpr uint32_t STATUS_INTERVAL_MS = 1000;
constexpr uint16_t CHANNEL_MIN_US = 800;
constexpr uint16_t CHANNEL_MAX_US = 2200;
constexpr size_t MAX_PAYLOAD = 768;

static_assert(EXTENDED_FRAME_US < 32768, "Timer1 interval must fit at 0.5 us/tick");

enum MessageType : uint8_t {
  MSG_HELLO = 1,
  MSG_HELLO_RESPONSE = 2,
  MSG_DEVICE_INFO = 3,
  MSG_STATUS = 4,
  MSG_LIVE_INPUT = 5,
  MSG_LIVE_CHANNELS = 6,
  MSG_PROFILE_LIST = 7,
  MSG_PROFILE_READ = 8,
  MSG_PROFILE_VALIDATE = 9,
  MSG_PROFILE_WRITE = 10,
  MSG_PROFILE_ACTIVATE = 11,
  MSG_CALIBRATION = 12,
  MSG_REBOOT = 13,
  MSG_BOOTLOADER = 14,
  MSG_ACK = 15,
  MSG_ERROR = 16,
  MSG_LOG = 17,
};

volatile uint16_t g_channels[MAX_CHANNELS];
volatile uint8_t g_channel_count = DEFAULT_CHANNEL_COUNT;
volatile bool g_begin_pulse = true;
volatile uint8_t g_interval_index = 0;
volatile uint32_t g_frame_used_us = 0;

bool g_stream_active = false;
uint32_t g_last_valid_channels_ms = 0;
uint32_t g_last_status_ms = 0;

uint16_t crc16Update(uint16_t crc, uint8_t value) {
  crc ^= static_cast<uint16_t>(value) << 8;
  for (uint8_t bit = 0; bit < 8; ++bit) {
    crc = (crc & 0x8000U) ? static_cast<uint16_t>((crc << 1U) ^ 0x1021U)
                          : static_cast<uint16_t>(crc << 1U);
  }
  return crc;
}

uint16_t clampChannel(long value) {
  if (value < CHANNEL_MIN_US) return CHANNEL_MIN_US;
  if (value > CHANNEL_MAX_US) return CHANNEL_MAX_US;
  return static_cast<uint16_t>(value);
}

void writePpmLevel(bool high) {
  digitalWrite(PPM_OUTPUT_PIN, high ? HIGH : LOW);
}

uint16_t microsecondsToTimerTicks(uint16_t microseconds) {
  return static_cast<uint16_t>(microseconds * 2U);
}

void makeFailsafe(uint16_t *values, uint8_t count) {
  for (uint8_t index = 0; index < count; ++index) {
    values[index] = (index == 2) ? 1000 : 1500;
  }
}

void applyChannels(const uint16_t *values, uint8_t count) {
  if (!values || count < 4) return;
  if (count > MAX_CHANNELS) count = MAX_CHANNELS;
  noInterrupts();
  g_channel_count = count;
  for (uint8_t index = 0; index < count; ++index) g_channels[index] = values[index];
  interrupts();
}

void applyFailsafe() {
  uint16_t safe[MAX_CHANNELS];
  uint8_t count;
  noInterrupts();
  count = g_channel_count;
  interrupts();
  makeFailsafe(safe, count);
  applyChannels(safe, count);
  g_stream_active = false;
}

ISR(TIMER1_COMPA_vect) {
  const bool active_level = !PPM_IDLE_HIGH;
  if (g_begin_pulse) {
    writePpmLevel(active_level);
    OCR1A = static_cast<uint16_t>(OCR1A + microsecondsToTimerTicks(PPM_PULSE_US));
    g_begin_pulse = false;
    return;
  }

  writePpmLevel(PPM_IDLE_HIGH);
  g_begin_pulse = true;
  uint16_t delay_us;
  const uint8_t count = g_channel_count;

  if (g_interval_index < count) {
    uint16_t channel_us = g_channels[g_interval_index];
    if (channel_us <= PPM_PULSE_US) channel_us = PPM_PULSE_US + 1;
    delay_us = static_cast<uint16_t>(channel_us - PPM_PULSE_US);
    g_frame_used_us += channel_us;
    ++g_interval_index;
  } else {
    uint32_t frame_us = count <= 8 ? STANDARD_FRAME_US : EXTENDED_FRAME_US;
    const uint32_t minimum_frame = g_frame_used_us + PPM_PULSE_US + 1000UL;
    if (frame_us < minimum_frame) frame_us = minimum_frame;
    delay_us = static_cast<uint16_t>(frame_us - g_frame_used_us - PPM_PULSE_US);
    g_frame_used_us = 0;
    g_interval_index = 0;
  }
  OCR1A = static_cast<uint16_t>(OCR1A + microsecondsToTimerTicks(delay_us));
}

void setupPpm() {
  pinMode(PPM_OUTPUT_PIN, OUTPUT);
  writePpmLevel(PPM_IDLE_HIGH);
  noInterrupts();
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1 = 0;
  OCR1A = 200;
  TCCR1B |= _BV(CS11);
  TIMSK1 |= _BV(OCIE1A);
  interrupts();
}

void sendFrame(uint8_t type, uint16_t sequence, const char *json) {
  if (!json) json = "{}";
  const size_t payload_length = strlen(json);
  if (payload_length > MAX_PAYLOAD) return;

  uint8_t header[6] = {
      PROTOCOL_MAJOR,
      type,
      static_cast<uint8_t>(sequence & 0xFFU),
      static_cast<uint8_t>(sequence >> 8U),
      static_cast<uint8_t>(payload_length & 0xFFU),
      static_cast<uint8_t>(payload_length >> 8U),
  };
  uint16_t crc = 0xFFFFU;
  for (uint8_t value : header) crc = crc16Update(crc, value);
  for (size_t index = 0; index < payload_length; ++index) {
    crc = crc16Update(crc, static_cast<uint8_t>(json[index]));
  }

  Serial.write(MAGIC_0);
  Serial.write(MAGIC_1);
  Serial.write(header, sizeof(header));
  Serial.write(reinterpret_cast<const uint8_t *>(json), payload_length);
  Serial.write(static_cast<uint8_t>(crc & 0xFFU));
  Serial.write(static_cast<uint8_t>(crc >> 8U));
}

void sendHello(uint16_t sequence) {
  sendFrame(
      MSG_HELLO_RESPONSE,
      sequence,
      "{\"protocol_major\":1,\"protocol_minor\":0,\"firmware_version\":\"0.2.0-arduino-mega\","
      "\"board\":\"Arduino Mega 2560\",\"hardware_revision\":\"bridge\","
      "\"capabilities\":[\"ppm\",\"desktop_stream\",\"failsafe\",\"stream_only\",\"12_channels\"]}");
}

void sendDeviceInfo(uint16_t sequence) {
  sendFrame(
      MSG_DEVICE_INFO,
      sequence,
      "{\"board\":\"Arduino Mega 2560\",\"firmware_version\":\"0.2.0-arduino-mega\","
      "\"ppm_gpio\":11,\"max_channels\":12,\"mode\":\"desktop_bridge\",\"persistent_profiles\":false}");
}

void sendAck(uint16_t sequence, const char *request) {
  char json[170];
  snprintf(json, sizeof(json),
           "{\"ok\":true,\"request\":\"%s\",\"mode\":\"desktop_bridge\",\"persistent\":false}",
           request ? request : "UNKNOWN");
  sendFrame(MSG_ACK, sequence, json);
}

void sendError(uint16_t sequence, const char *request, const char *message) {
  char json[220];
  snprintf(json, sizeof(json),
           "{\"ok\":false,\"request\":\"%s\",\"errors\":[\"%s\"]}",
           request ? request : "UNKNOWN", message ? message : "unknown error");
  sendFrame(MSG_ERROR, sequence, json);
}

void sendStatus(uint16_t sequence) {
  uint16_t snapshot[MAX_CHANNELS];
  uint8_t count;
  noInterrupts();
  count = g_channel_count;
  for (uint8_t index = 0; index < count; ++index) snapshot[index] = g_channels[index];
  interrupts();

  char json[430];
  int used = snprintf(
      json,
      sizeof(json),
      "{\"uptime_ms\":%lu,\"joystick_connected\":%s,\"ppm_active\":true,"
      "\"active_profile\":\"Desktop multi-device stream\",\"channels\":[",
      static_cast<unsigned long>(millis()),
      g_stream_active ? "true" : "false");
  if (used < 0) return;

  for (uint8_t index = 0; index < count && static_cast<size_t>(used) < sizeof(json); ++index) {
    const int written = snprintf(
        json + used,
        sizeof(json) - static_cast<size_t>(used),
        "%s%u",
        index ? "," : "",
        snapshot[index]);
    if (written < 0) return;
    used += written;
  }
  if (static_cast<size_t>(used) < sizeof(json)) {
    snprintf(json + used, sizeof(json) - static_cast<size_t>(used), "],\"faults\":[]}");
    sendFrame(MSG_STATUS, sequence, json);
  }
}

bool parseChannelArray(char *payload, uint16_t *values, uint8_t &count) {
  if (!payload || !values) return false;
  char *cursor = strstr(payload, "\"channels\"");
  if (!cursor) return false;
  cursor = strchr(cursor, '[');
  if (!cursor) return false;
  ++cursor;

  count = 0;
  while (*cursor && count < MAX_CHANNELS) {
    while (*cursor == ' ' || *cursor == '\t' || *cursor == '\r' || *cursor == '\n' || *cursor == ',') ++cursor;
    if (*cursor == ']') break;
    char *end = nullptr;
    const long value = strtol(cursor, &end, 10);
    if (end == cursor) return false;
    values[count++] = clampChannel(value);
    cursor = end;
    while (*cursor == ' ' || *cursor == '\t' || *cursor == '\r' || *cursor == '\n') ++cursor;
    if (*cursor == ']') break;
    if (*cursor != ',') return false;
  }
  return count >= 4;
}

void rebootBoard() {
  Serial.flush();
  delay(30);
  wdt_enable(WDTO_15MS);
  while (true) {}
}

void handleFrame(uint8_t major, uint8_t type, uint16_t sequence, char *payload) {
  if (major != PROTOCOL_MAJOR) {
    sendError(sequence, "PROTOCOL", "protocol major mismatch");
    return;
  }
  switch (type) {
    case MSG_HELLO:
      sendHello(sequence);
      break;
    case MSG_DEVICE_INFO:
      sendDeviceInfo(sequence);
      break;
    case MSG_STATUS:
      sendStatus(sequence);
      break;
    case MSG_LIVE_CHANNELS: {
      uint16_t values[MAX_CHANNELS];
      uint8_t count = 0;
      if (!parseChannelArray(payload, values, count)) {
        sendError(sequence, "LIVE_CHANNELS", "invalid or unsupported channel array");
        break;
      }
      applyChannels(values, count);
      g_last_valid_channels_ms = millis();
      g_stream_active = true;
      break;
    }
    case MSG_PROFILE_VALIDATE:
      sendAck(sequence, "PROFILE_VALIDATE");
      break;
    case MSG_PROFILE_WRITE:
      sendAck(sequence, "PROFILE_WRITE");
      break;
    case MSG_PROFILE_ACTIVATE:
      sendAck(sequence, "PROFILE_ACTIVATE");
      break;
    case MSG_REBOOT:
      sendAck(sequence, "REBOOT");
      rebootBoard();
      break;
    case MSG_BOOTLOADER:
      sendError(sequence, "BOOTLOADER", "automatic bootloader entry is not supported on Mega 2560");
      break;
    default:
      sendError(sequence, "UNKNOWN", "unsupported message type on Arduino Mega bridge");
      break;
  }
}

enum ParserState : uint8_t {
  WAIT_MAGIC_0,
  WAIT_MAGIC_1,
  READ_HEADER,
  READ_PAYLOAD,
  READ_CRC_LOW,
  READ_CRC_HIGH,
  DISCARD_OVERSIZE,
};

struct FrameParser {
  ParserState state = WAIT_MAGIC_0;
  uint8_t header[6] = {0};
  uint8_t header_index = 0;
  uint16_t payload_length = 0;
  uint16_t payload_index = 0;
  char payload[MAX_PAYLOAD + 1] = {0};
  uint16_t calculated_crc = 0xFFFFU;
  uint16_t received_crc = 0;
  uint16_t discard_remaining = 0;
};

FrameParser g_parser;

void resetParser() {
  g_parser.state = WAIT_MAGIC_0;
  g_parser.header_index = 0;
  g_parser.payload_length = 0;
  g_parser.payload_index = 0;
  g_parser.calculated_crc = 0xFFFFU;
  g_parser.received_crc = 0;
  g_parser.discard_remaining = 0;
}

void feedParser(uint8_t value) {
  switch (g_parser.state) {
    case WAIT_MAGIC_0:
      if (value == MAGIC_0) g_parser.state = WAIT_MAGIC_1;
      break;
    case WAIT_MAGIC_1:
      if (value == MAGIC_1) {
        g_parser.state = READ_HEADER;
        g_parser.header_index = 0;
        g_parser.calculated_crc = 0xFFFFU;
      } else {
        g_parser.state = value == MAGIC_0 ? WAIT_MAGIC_1 : WAIT_MAGIC_0;
      }
      break;
    case READ_HEADER:
      g_parser.header[g_parser.header_index++] = value;
      g_parser.calculated_crc = crc16Update(g_parser.calculated_crc, value);
      if (g_parser.header_index == sizeof(g_parser.header)) {
        g_parser.payload_length = static_cast<uint16_t>(g_parser.header[4]) |
                                  (static_cast<uint16_t>(g_parser.header[5]) << 8U);
        g_parser.payload_index = 0;
        if (g_parser.payload_length > MAX_PAYLOAD) {
          g_parser.discard_remaining = static_cast<uint16_t>(g_parser.payload_length + 2U);
          g_parser.state = DISCARD_OVERSIZE;
        } else if (g_parser.payload_length == 0) {
          g_parser.payload[0] = '\0';
          g_parser.state = READ_CRC_LOW;
        } else {
          g_parser.state = READ_PAYLOAD;
        }
      }
      break;
    case READ_PAYLOAD:
      g_parser.payload[g_parser.payload_index++] = static_cast<char>(value);
      g_parser.calculated_crc = crc16Update(g_parser.calculated_crc, value);
      if (g_parser.payload_index == g_parser.payload_length) {
        g_parser.payload[g_parser.payload_length] = '\0';
        g_parser.state = READ_CRC_LOW;
      }
      break;
    case READ_CRC_LOW:
      g_parser.received_crc = value;
      g_parser.state = READ_CRC_HIGH;
      break;
    case READ_CRC_HIGH: {
      g_parser.received_crc |= static_cast<uint16_t>(value) << 8U;
      if (g_parser.received_crc == g_parser.calculated_crc) {
        const uint16_t sequence = static_cast<uint16_t>(g_parser.header[2]) |
                                  (static_cast<uint16_t>(g_parser.header[3]) << 8U);
        handleFrame(g_parser.header[0], g_parser.header[1], sequence, g_parser.payload);
      }
      resetParser();
      break;
    }
    case DISCARD_OVERSIZE:
      if (g_parser.discard_remaining > 0) --g_parser.discard_remaining;
      if (g_parser.discard_remaining == 0) resetParser();
      break;
  }
}

}  // namespace

void setup() {
  uint16_t safe[MAX_CHANNELS];
  makeFailsafe(safe, DEFAULT_CHANNEL_COUNT);
  applyChannels(safe, DEFAULT_CHANNEL_COUNT);
  setupPpm();
  Serial.begin(115200);
  delay(80);
  sendHello(0);
  wdt_enable(WDTO_1S);
}

void loop() {
  wdt_reset();
  while (Serial.available() > 0) {
    const int value = Serial.read();
    if (value >= 0) feedParser(static_cast<uint8_t>(value));
  }

  const uint32_t now = millis();
  if (g_stream_active && static_cast<uint32_t>(now - g_last_valid_channels_ms) > FAILSAFE_TIMEOUT_MS) {
    applyFailsafe();
  }
  if (static_cast<uint32_t>(now - g_last_status_ms) >= STATUS_INTERVAL_MS) {
    g_last_status_ms = now;
    sendStatus(0);
  }
  delay(1);
}
