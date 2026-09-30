#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <DHTesp.h>
#include <time.h>

// =================================================
// CẤU HÌNH WI-FI
// =================================================
const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";

// =================================================
// CẤU HÌNH MQTT
// =================================================
const char* MQTT_SERVER = "broker.hivemq.com";
const int MQTT_PORT = 1883;

const char* MQTT_TOPIC = "ptit/iot/B23DCAT279/sensor";

// =================================================
// CẤU HÌNH NTP
// =================================================
const char* NTP_SERVER = "pool.ntp.org";

// Dùng UTC để tính latency.
// Không cần +7 vì ESP32 và Python chỉ cần cùng mốc Unix time.
const long GMT_OFFSET_SEC = 0;
const int DAYLIGHT_OFFSET_SEC = 0;

// =================================================
// CẤU HÌNH GPIO
// =================================================
const int DHT_PIN = 15;
const int TRIG_PIN = 5;
const int ECHO_PIN = 18;
const int LED_PIN = 2;

const unsigned long SEND_INTERVAL_MS = 5000;

// =================================================
// ĐỐI TƯỢNG VÀ BIẾN TOÀN CỤC
// =================================================
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

DHTesp dht;

unsigned long lastSend = 0;
unsigned long sequenceNo = 0;


// =================================================
// KẾT NỐI WI-FI
// =================================================
void connectWiFi() {

  Serial.println();
  Serial.println("Connecting to WiFi...");

  Serial.print("SSID        : ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);

  WiFi.begin(
    WIFI_SSID,
    WIFI_PASSWORD,
    6
  );

  while (WiFi.status() != WL_CONNECTED) {

    delay(500);
    Serial.print(".");
  }

  Serial.println();

  Serial.println("WiFi        : CONNECTED");

  Serial.print("IP address  : ");
  Serial.println(WiFi.localIP());

  Serial.print("WiFi RSSI   : ");
  Serial.print(WiFi.RSSI());
  Serial.println(" dBm");
}


// =================================================
// ĐỒNG BỘ THỜI GIAN NTP
// =================================================
void syncTime() {

  Serial.println();
  Serial.println("Synchronizing time with NTP...");

  configTime(
    GMT_OFFSET_SEC,
    DAYLIGHT_OFFSET_SEC,
    NTP_SERVER
  );

  struct tm timeInfo;

  int retry = 0;

  while (!getLocalTime(&timeInfo) && retry < 20) {

    Serial.print(".");
    delay(500);

    retry++;
  }

  Serial.println();

  if (retry < 20) {

    Serial.println("NTP         : SYNCHRONIZED");

    time_t now;
    time(&now);

    Serial.print("Unix time   : ");
    Serial.println((unsigned long)now);

  } else {

    Serial.println("NTP         : FAILED");
  }
}


// =================================================
// LẤY UNIX TIMESTAMP MILLISECONDS
// =================================================
uint64_t getTimestampMs() {

  struct timeval tv;

  gettimeofday(
    &tv,
    nullptr
  );

  uint64_t timestampMs =
    ((uint64_t)tv.tv_sec * 1000ULL)
    + ((uint64_t)tv.tv_usec / 1000ULL);

  return timestampMs;
}


// =================================================
// KẾT NỐI MQTT
// =================================================
void connectMQTT() {

  while (!mqttClient.connected()) {

    String clientId =
      "ESP32-B23DCAT279-" +
      String((uint32_t)ESP.getEfuseMac(), HEX);

    Serial.println();
    Serial.println("Connecting to MQTT Broker...");

    Serial.print("Broker      : ");
    Serial.println(MQTT_SERVER);

    Serial.print("Port        : ");
    Serial.println(MQTT_PORT);

    Serial.print("Topic       : ");
    Serial.println(MQTT_TOPIC);

    bool connected =
      mqttClient.connect(
        clientId.c_str()
      );

    if (connected) {

      Serial.println("MQTT        : CONNECTED");

    } else {

      Serial.print("MQTT        : FAILED");

      Serial.print(" | Code: ");
      Serial.println(mqttClient.state());

      Serial.println(
        "Retry after 2 seconds..."
      );

      delay(2000);
    }
  }
}


// =================================================
// ĐỌC KHOẢNG CÁCH HC-SR04
// =================================================
float readDistanceCm() {

  digitalWrite(
    TRIG_PIN,
    LOW
  );

  delayMicroseconds(5);

  digitalWrite(
    TRIG_PIN,
    HIGH
  );

  delayMicroseconds(10);

  digitalWrite(
    TRIG_PIN,
    LOW
  );

  unsigned long duration =
    pulseIn(
      ECHO_PIN,
      HIGH,
      40000UL
    );

  if (duration == 0) {

    return NAN;
  }

  return duration * 0.0343f / 2.0f;
}


// =================================================
// SETUP
// =================================================
void setup() {

  Serial.begin(115200);

  delay(1000);

  Serial.println();
  Serial.println("========================================");
  Serial.println("   BAI 2 - IOT DATA COLLECTION");
  Serial.println("========================================");

  // GPIO
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);

  digitalWrite(TRIG_PIN, LOW);
  digitalWrite(LED_PIN, LOW);

  // =================================================
  // DHT22
  // =================================================

  dht.setup(
    DHT_PIN,
    DHTesp::DHT22
  );

  delay(2000);

  // =================================================
  // WI-FI
  // =================================================

  connectWiFi();

  // =================================================
  // NTP
  // =================================================

  syncTime();

  // =================================================
  // MQTT
  // =================================================

  mqttClient.setServer(
    MQTT_SERVER,
    MQTT_PORT
  );

  // Payload giờ dài hơn nên tăng buffer
  mqttClient.setBufferSize(512);

  mqttClient.setKeepAlive(60);
}


// =================================================
// LOOP
// =================================================
void loop() {

  // =================================================
  // KIỂM TRA WI-FI
  // =================================================

  if (WiFi.status() != WL_CONNECTED) {

    connectWiFi();
  }

  // =================================================
  // KIỂM TRA MQTT
  // =================================================

  if (!mqttClient.connected()) {

    connectMQTT();
  }

  mqttClient.loop();

  unsigned long now = millis();

  // =================================================
  // CHU KỲ 5 GIÂY
  // =================================================

  if (now - lastSend < SEND_INTERVAL_MS) {

    return;
  }

  lastSend = now;

  // =================================================
  // ĐỌC CẢM BIẾN
  // =================================================

  TempAndHumidity dhtData =
    dht.getTempAndHumidity();

  float distance =
    readDistanceCm();

  // =================================================
  // HIỂN THỊ
  // =================================================

  Serial.println();

  Serial.println(
    "========== SENSOR DATA =========="
  );

  Serial.print("Temperature : ");
  Serial.print(dhtData.temperature, 2);
  Serial.println(" °C");

  Serial.print("Humidity    : ");
  Serial.print(dhtData.humidity, 2);
  Serial.println(" %RH");

  Serial.print("Distance    : ");
  Serial.print(distance, 2);
  Serial.println(" cm");

  Serial.print("WiFi RSSI   : ");
  Serial.print(WiFi.RSSI());
  Serial.println(" dBm");

  // =================================================
  // VALIDATE
  // =================================================

  if (
    !isfinite(dhtData.temperature) ||
    !isfinite(dhtData.humidity) ||
    !isfinite(distance)
  ) {

    Serial.print("DHT status  : ");
    Serial.println(
      dht.getStatusString()
    );

    Serial.println(
      "Result      : INVALID DATA"
    );

    Serial.println(
      "Publish     : SKIPPED"
    );

    Serial.println(
      "================================="
    );

    return;
  }

  // =================================================
  // SEQUENCE
  // =================================================

  sequenceNo++;

  // =================================================
  // TIMESTAMP
  // =================================================

  uint64_t timestampMs =
    getTimestampMs();

  // =================================================
  // TẠO JSON
  // =================================================

  char payload[384];

  snprintf(
    payload,
    sizeof(payload),

    "{"
      "\"temperature\":%.2f,"
      "\"humidity\":%.2f,"
      "\"distance_cm\":%.2f,"
      "\"rssi\":%d,"
      "\"sequence\":%lu,"
      "\"uptime_s\":%lu,"
      "\"timestamp_ms\":%llu"
    "}",

    dhtData.temperature,
    dhtData.humidity,
    distance,
    WiFi.RSSI(),
    sequenceNo,
    millis() / 1000,
    timestampMs
  );

  // =================================================
  // MQTT PUBLISH
  // =================================================

  bool publishOk =
    mqttClient.publish(
      MQTT_TOPIC,
      payload
    );

  // =================================================
  // HIỂN THỊ KẾT QUẢ
  // =================================================

  Serial.print("Sequence    : ");
  Serial.println(sequenceNo);

  Serial.print("Uptime      : ");
  Serial.print(millis() / 1000);
  Serial.println(" seconds");

  Serial.print("Timestamp   : ");
  Serial.print(timestampMs);
  Serial.println(" ms");

  Serial.print("Topic       : ");
  Serial.println(MQTT_TOPIC);

  Serial.print("JSON        : ");
  Serial.println(payload);

  Serial.print("Publish     : ");

  Serial.println(
    publishOk
      ? "OK"
      : "FAILED"
  );

  Serial.println(
    "================================="
  );

  // =================================================
  // LED
  // =================================================

  if (publishOk) {

    digitalWrite(
      LED_PIN,
      HIGH
    );

    delay(500);

    digitalWrite(
      LED_PIN,
      LOW
    );
  }
}