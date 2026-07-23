/*
 * Simulator Joystick to FlySky — Arduino UNO/Nano Bridge
 *
 * Signal path:
 *   USB flight controls -> Windows desktop app -> USB serial -> UNO/Nano
 *   -> PPM on D9 -> FlySky trainer port
 *
 * Safe PPM starts immediately at boot. Firmware 0.3.0 adds a compact binary
 * live-channel message so the desktop can update D9 without large JSON frames.
 */

#include <Arduino.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>
#include <stdlib.h>
#include <string.h>

#if !defined(__AVR_ATmega328P__)
#error "This sketch targets Arduino UNO/Nano boards using the ATmega328P."
#endif

namespace {

constexpr uint8_t PROTOCOL_MAJOR = 1;
constexpr uint8_t MAGIC_0 = 'S';
constexpr uint8_t MAGIC_1 = 'J';

constexpr uint8_t PPM_OUTPUT_PIN = 9;           // ATmega328P PB1
constexpr uint8_t HEARTBEAT_PIN = LED_BUILTIN;  // ATmega328P PB5 / D13
constexpr uint8_t MAX_CHANNELS = 8;
constexpr uint8_t DEFAULT_CHANNEL_COUNT = 8;
constexpr uint16_t PPM_FRAME_US = 22500;
constexpr uint16_t PPM_PULSE_US = 400;
constexpr bool PPM_IDLE_HIGH = true;

constexpr uint32_t FAILSAFE_TIMEOUT_MS = 700;
constexpr uint16_t CHANNEL_MIN_US = 800;
constexpr uint16_t CHANNEL_MAX_US = 2200;
constexpr size_t MAX_PAYLOAD = 384;

static_assert(PPM_FRAME_US < 32768, "Timer1 interval must fit at 0.5 us/tick");
static_assert(PPM_PULSE_US >= 100, "PPM separator pulse is unexpectedly short");

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
  MSG_LIVE_CHANNELS_FAST = 18,
};

volatile uint16_t g_channels[MAX_CHANNELS];
volatile uint8_t g_channel_count = DEFAULT_CHANNEL_COUNT;
volatile bool g_begin_pulse = true;
volatile uint8_t g_interval_index = 0;
volatile uint32_t g_frame_used_us = 0;
volatile uint32_t g_ppm_frame_count = 0;
volatile uint8_t g_heartbeat_divider = 0;

bool g_stream_active = false;
uint32_t g_last_valid_channels_ms = 0;

uint16_t crc16Update(uint16_t crc, uint8_t value) {
  crc ^= static_cast<uint16_t>(value) << 8;
  for (uint8_t bit = 0; bit < 8; ++bit) {
    crc = (crc & 0x8000U)
              ? static_cast<uint16_t>((crc << 1U) ^ 0x1021U)
              : static_cast<uint16_t>(crc << 1U);
  }
  return crc;
}

uint16_t clampChannel(long value) {
  if (value < CHANNEL_MIN_US) {
    return CHANNEL_MIN_US;
  }
  if (value > CHANNEL_MAX_US) {
    return CHANNEL_MAX_US;
  }
  return static_cast<uint16_t>(value);
}

inline void writePpmLevel(bool high) {
  if (high) {
    PORTB |= _BV(PORTB1);
  } else {
    PORTB &= static_cast<uint8_t>(~_BV(PORTB1));
  }
}

inline void scheduleTimerMicroseconds(uint16_t microseconds) {
  // Timer1 CTC, 16 MHz / 8 = 2 ticks/us. OCR1A is inclusive.
  uint32_t ticks = static_cast<uint32_t>(microseconds) * 2UL;
  if (ticks < 2UL) {
    ticks = 2UL;
  }
  if (ticks > 65535UL) {
    ticks = 65535UL;
  }
  OCR1A = static_cast<uint16_t>(ticks - 1UL);
}

void makeFailsafe(uint16_t *values, uint8_t count) {
  for (uint8_t index = 0; index < count; ++index) {
    values[index] = (index == 2) ? 1000 : 1500;
  }
}

void applyChannels(const uint16_t *values, uint8_t count) {
  if (!values || count < 4) {
    return;
  }
  if (count > MAX_CHANNELS) {
    count = MAX_CHANNELS;
  }

  noInterrupts();
  g_channel_count = count;
  for (uint8_t index = 0; index < count; ++index) {
    g_channels[index] = values[index];
  }
  interrupts();
}

void markValidStream() {
  g_last_valid_channels_ms = millis();
  g_stream_active = true;
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
    scheduleTimerMicroseconds(PPM_PULSE_US);
    g_begin_pulse = false;
    return;
  }

  writePpmLevel(PPM_IDLE_HIGH);
  g_begin_pulse = true;

  uint16_t delay_us = 1000;
  const uint8_t count = g_channel_count;

  if (g_interval_index < count) {
    uint16_t channel_us = g_channels[g_interval_index];
    if (channel_us <= PPM_PULSE_US) {
      channel_us = PPM_PULSE_US + 1;
    }
    delay_us = static_cast<uint16_t>(channel_us - PPM_PULSE_US);
    g_frame_used_us += channel_us;
    ++g_interval_index;
  } else {
    uint32_t frame_us = PPM_FRAME_US;
    const uint32_t minimum_frame = g_frame_used_us + PPM_PULSE_US + 1000UL;
    if (frame_us < minimum_frame) {
      frame_us = minimum_frame;
    }
    delay_us = static_cast<uint16_t>(frame_us - g_frame_used_us - PPM_PULSE_US);
    g_frame_used_us = 0;
    g_interval_index = 0;
    ++g_ppm_frame_count;

    // D13 blinks at roughly 0.9 Hz while the PPM engine is running.
    if (++g_heartbeat_divider >= 25) {
      g_heartbeat_divider = 0;
      PORTB ^= _BV(PORTB5);
    }
  }

  scheduleTimerMicroseconds(delay_us);
}

void setupPpm() {
  pinMode(PPM_OUTPUT_PIN, OUTPUT);
  pinMode(HEARTBEAT_PIN, OUTPUT);
  writePpmLevel(PPM_IDLE_HIGH);
  digitalWrite(HEARTBEAT_PIN, LOW);

  noInterrupts();
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1 = 0;
  scheduleTimerMicroseconds(100);
  TIFR1 = _BV(OCF1A);
  TIMSK1 = _BV(OCIE1A);
  TCCR1B = _BV(WGM12) | _BV(CS11);  // CTC mode, prescaler 8.
  interrupts();
}

void sendFrame(uint8_t type, uint16_t sequence, const char *json) {
  if (!json) {
    json = "{}";
  }
  const size_t payload_length = strlen(json);
  if (payload_length > MAX_PAYLOAD) {
    return;
  }

  uint8_t header[6] = {
      PROTOCOL_MAJOR,
      type,
      static_cast<uint8_t>(sequence & 0xFFU),
      static_cast<uint8_t>(sequence >> 8U),
      static_cast<uint8_t>(payload_length & 0xFFU),
      static_cast<uint8_t>(payload_length >> 8U),
  };

  uint16_t crc = 0xFFFFU;
  for (uint8_t index = 0; index < sizeof(header); ++index) {
    crc = crc16Update(crc, header[index]);
  }
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
      "{\"protocol_major\":1,\"protocol_minor\":0,\"firmware_version\":\"0.3.0-arduino-uno\","
      "\"board\":\"Arduino UNO/Nano ATmega328P\",\"hardware_revision\":\"bridge-d9-v3\","
      "\"capabilities\":[\"ppm\",\"desktop_stream\",\"failsafe\",\"stream_only\","
      "\"ppm_engine_status\",\"fast_channels_v1\"]}");
}

void sendDeviceInfo(uint16_t sequence) {
  sendFrame(
      MSG_DEVICE_INFO,
      sequence,
      "{\"board\":\"Arduino UNO/Nano ATmega328P\",\"firmware_version\":\"0.3.0-arduino-uno\","
      "\"ppm_gpio\":9,\"ppm_frame_us\":22500,\"ppm_pulse_us\":400,\"ppm_idle_high\":true,"
      "\"live_channel_encoding\":\"u16le-v1\",\"mode\":\"desktop_bridge\","
      "\"persistent_profiles\":false}");
}

void sendAck(uint16_t sequence, const char *request) {
  char json[150];
  snprintf(
      json,
      sizeof(json),
      "{\"ok\":true,\"request\":\"%s\",\"mode\":\"desktop_bridge\",\"persistent\":false}",
      request ? request : "UNKNOWN");
  sendFrame(MSG_ACK, sequence, json);
}

void sendError(uint16_t sequence, const char *request, const char *message) {
  char json[190];
  snprintf(
      json,
      sizeof(json),
      "{\"ok\":false,\"request\":\"%s\",\"errors\":[\"%s\"]}",
      request ? request : "UNKNOWN",
      message ? message : "unknown error");
  sendFrame(MSG_ERROR, sequence, json);
}

void sendStatus(uint16_t sequence) {
  uint16_t snapshot[MAX_CHANNELS];
  uint8_t count;
  uint32_t frame_count;

  noInterrupts();
  count = g_channel_count;
  frame_count = g_ppm_frame_count;
  for (uint8_t index = 0; index < count; ++index) {
    snapshot[index] = g_channels[index];
  }
  interrupts();

  const uint32_t now = millis();
  const uint32_t stream_age = g_last_valid_channels_ms
                                  ? static_cast<uint32_t>(now - g_last_valid_channels_ms)
                                  : 0UL;
  const bool ppm_active = frame_count > 0;
  const bool failsafe_active = !g_stream_active;

  char json[420];
  int used = snprintf(
      json,
      sizeof(json),
      "{\"uptime_ms\":%lu,\"stream_active\":%s,\"joystick_connected\":%s,"
      "\"failsafe_active\":%s,\"stream_age_ms\":%lu,\"ppm_active\":%s,"
      "\"ppm_gpio\":9,\"ppm_frame_count\":%lu,\"ppm_frame_us\":22500,"
      "\"ppm_pulse_us\":400,\"ppm_idle_high\":true,\"channels\":[",
      static_cast<unsigned long>(now),
      g_stream_active ? "true" : "false",
      g_stream_active ? "true" : "false",
      failsafe_active ? "true" : "false",
      static_cast<unsigned long>(stream_age),
      ppm_active ? "true" : "false",
      static_cast<unsigned long>(frame_count));

  if (used < 0 || static_cast<size_t>(used) >= sizeof(json)) {
    return;
  }

  for (uint8_t index = 0; index < count; ++index) {
    const int written = snprintf(
        json + used,
        sizeof(json) - static_cast<size_t>(used),
        "%s%u",
        index ? "," : "",
        snapshot[index]);
    if (written < 0 ||
        static_cast<size_t>(written) >= sizeof(json) - static_cast<size_t>(used)) {
      return;
    }
    used += written;
  }

  snprintf(
      json + used,
      sizeof(json) - static_cast<size_t>(used),
      "],\"active_profile\":\"Desktop stream\",\"faults\":%s}",
      failsafe_active ? "[\"desktop_stream_timeout\"]" : "[]");
  sendFrame(MSG_STATUS, sequence, json);
}

bool parseChannelArray(char *payload, uint16_t *values, uint8_t &count) {
  if (!payload || !values) {
    return false;
  }
  char *cursor = strstr(payload, "\"channels\"");
  if (!cursor) {
    return false;
  }
  cursor = strchr(cursor, '[');
  if (!cursor) {
    return false;
  }
  ++cursor;

  count = 0;
  while (*cursor && count < MAX_CHANNELS) {
    while (*cursor == ' ' || *cursor == '\t' || *cursor == '\r' ||
           *cursor == '\n' || *cursor == ',') {
      ++cursor;
    }
    if (*cursor == ']') {
      break;
    }

    char *end = nullptr;
    const long value = strtol(cursor, &end, 10);
    if (end == cursor) {
      return false;
    }
    values[count++] = clampChannel(value);
    cursor = end;

    while (*cursor == ' ' || *cursor == '\t' || *cursor == '\r' || *cursor == '\n') {
      ++cursor;
    }
    if (*cursor == ']') {
      break;
    }
    if (*cursor != ',') {
      return false;
    }
  }
  return count >= 4;
}

bool parseFastChannels(
    const uint8_t *payload,
    uint16_t payload_length,
    uint16_t *values,
    uint8_t &count) {
  if (!payload || !values || payload_length < 1) {
    return false;
  }

  count = payload[0];
  if (count < 4 || count > MAX_CHANNELS) {
    return false;
  }
  if (payload_length != static_cast<uint16_t>(1U + (count * 2U))) {
    return false;
  }

  for (uint8_t index = 0; index < count; ++index) {
    const uint8_t low = payload[1U + (index * 2U)];
    const uint8_t high = payload[2U + (index * 2U)];
    values[index] = clampChannel(
        static_cast<uint16_t>(low) |
        (static_cast<uint16_t>(high) << 8U));
  }
  return true;
}

void rebootBoard() {
  Serial.flush();
  delay(30);
  wdt_enable(WDTO_15MS);
  while (true) {
  }
}

void handleFrame(
    uint8_t major,
    uint8_t type,
    uint16_t sequence,
    char *payload,
    uint16_t payload_length) {
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
      // Status is request-driven. Avoid unsolicited large JSON telemetry while
      // realtime channel streaming is active.
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
      markValidStream();
      break;
    }
    case MSG_LIVE_CHANNELS_FAST: {
      uint16_t values[MAX_CHANNELS];
      uint8_t count = 0;
      if (!parseFastChannels(
              reinterpret_cast<const uint8_t *>(payload),
              payload_length,
              values,
              count)) {
        sendError(sequence, "LIVE_CHANNELS_FAST", "invalid binary channel payload");
        break;
      }
      applyChannels(values, count);
      markValidStream();
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
      sendError(sequence, "BOOTLOADER", "automatic bootloader entry is not supported on UNO/Nano");
      break;
    default:
      sendError(sequence, "UNKNOWN", "unsupported message type on Arduino bridge");
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
      if (value == MAGIC_0) {
        g_parser.state = WAIT_MAGIC_1;
      }
      break;

    case WAIT_MAGIC_1:
      if (value == MAGIC_1) {
        g_parser.state = READ_HEADER;
        g_parser.header_index = 0;
        g_parser.calculated_crc = 0xFFFFU;
      } else {
        g_parser.state = (value == MAGIC_0) ? WAIT_MAGIC_1 : WAIT_MAGIC_0;
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
        handleFrame(
            g_parser.header[0],
            g_parser.header[1],
            sequence,
            g_parser.payload,
            g_parser.payload_length);
      }
      resetParser();
      break;
    }

    case DISCARD_OVERSIZE:
      if (g_parser.discard_remaining > 0) {
        --g_parser.discard_remaining;
      }
      if (g_parser.discard_remaining == 0) {
        resetParser();
      }
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
  delay(50);
  sendHello(0);
  wdt_enable(WDTO_1S);
}

void loop() {
  wdt_reset();

  while (Serial.available() > 0) {
    const int value = Serial.read();
    if (value >= 0) {
      feedParser(static_cast<uint8_t>(value));
    }
  }

  const uint32_t now = millis();
  if (g_stream_active &&
      static_cast<uint32_t>(now - g_last_valid_channels_ms) > FAILSAFE_TIMEOUT_MS) {
    applyFailsafe();
  }

  // Do not emit periodic verbose status packets. On an ATmega328P the 64-byte
  // serial TX buffer can otherwise block input parsing long enough to create
  // visible control jitter. The desktop requests STATUS only when needed.
  delay(1);
}
