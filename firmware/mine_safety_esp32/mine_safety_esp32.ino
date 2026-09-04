#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <ArduinoJson.h>





const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SERVER_URL = "http://YOUR_LOCAL_IP:8000/api/telemetry";



// --- Hardware Pins ---
#define MQ2_PIN 34
#define LED_PIN 2
#define BUZZER_PIN 4

const int MPU_ADDR = 0x68;  // Scanner'ın bulduğu kesin adres
unsigned long immobilityStartTime = 0;
unsigned long lastImpactTime = 0;
bool impactDetected = false;

void setup() {
  Serial.begin(115200);

  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  delay(1000);

  // 1. I2C Bus Configuration
  Wire.begin(21, 22);
  Wire.setClock(100000);
  delay(100);

  // 2. MPU6050'yi Uyandırma (Power Management Register 0x6B)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);  // PWR_MGMT_1 register
  Wire.write(0);     // 0 yazarak uyku modundan çıkarıyoruz
  byte error = Wire.endTransmission();

  if (error == 0) {
    Serial.println("[+] MPU6050 successfully woken up and ready!");
  } else {
    Serial.println("[-] I2C Communication failed. Error code: " + String(error));
  }

  // 3. Wi-Fi Connection
  Serial.print("[*] Connecting to Wi-Fi: ");
  Serial.println(WIFI_SSID);

  WiFi.disconnect(true);
  delay(500);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long wifiStartTime = millis();

  while (WiFi.status() != WL_CONNECTED && millis() - wifiStartTime < 10000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[+] Wi-Fi connected successfully.");
    Serial.print("[+] Assigned ESP32 IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[-] Wi-Fi unavailable. Continuing in offline safety mode.");
  }
}

void loop() {
  // 1. Direct I2C Read from MPU6050 Registers (0x3B to 0x40)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);  // ACCEL_XOUT_H register
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 6, true);

  int16_t rawX = Wire.read() << 8 | Wire.read();
  int16_t rawY = Wire.read() << 8 | Wire.read();
  int16_t rawZ = Wire.read() << 8 | Wire.read();

  // Varsayılan ±2g aralığında 1g = 16384 LSB
  float ax = (float)rawX / 16384.0;
  float ay = (float)rawY / 16384.0;
  float az = (float)rawZ / 16384.0;

  // Toplam bileşke ivme
  float accelG = sqrt(sq(ax) + sq(ay) + sq(az));

  // 2. Read Gas Sensor Data
  int rawGas = analogRead(MQ2_PIN);
  float gasPpm = map(rawGas, 0, 4095, 150, 1000);


  // 3. Impact and Post-Impact Immobility Tracking
  bool gasDanger = gasPpm > 400.0;
  bool impactNow = accelG > 2.0;
  bool freeFall = accelG < 0.4;
  bool isStill = abs(accelG - 1.0) <= 0.08;

  if (impactNow) {
    impactDetected = true;
    lastImpactTime = millis();
    immobilityStartTime = 0;
  }


  if (impactDetected && millis() - lastImpactTime > 30000) {
    impactDetected = false;
    immobilityStartTime = 0;
  }

  float durationSec = 0.0;

  if (impactDetected && isStill) {
    if (immobilityStartTime == 0) {
      immobilityStartTime = millis();
    }

    durationSec =
      (float)(millis() - immobilityStartTime) / 1000.0;

    if (durationSec > 10.0) {
      durationSec = 10.0;
    }
  } else {
    immobilityStartTime = 0;
  }

  bool manDown = impactDetected && durationSec >= 10.0;
  bool isDanger = gasDanger || impactNow || freeFall || manDown;


  digitalWrite(LED_PIN, isDanger ? HIGH : LOW);
  digitalWrite(BUZZER_PIN, isDanger ? HIGH : LOW);

  // 4. Send Telemetry via HTTP POST
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(2500);


    StaticJsonDocument<256> doc;
    doc["gas_ppm"] = gasPpm;
    doc["accel_g"] = accelG;
    doc["duration_sec"] = durationSec;
    doc["miner_id"] = "MINER-ESP32";
    doc["zone"] = "Sector-3";



    String requestBody;
    serializeJson(doc, requestBody);

    Serial.println("\n[>] Sent Payload: " + requestBody);
    int httpResponseCode = http.POST(requestBody);

    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("[<] Server Response (" + String(httpResponseCode) + "): " + response);

      StaticJsonDocument<256> resDoc;
      DeserializationError err = deserializeJson(resDoc, response);

      if (!err) {
        bool actionRequired = resDoc["action_required"] | false;
        bool finalAlarm = isDanger || actionRequired;
        if (finalAlarm) {
          Serial.println("[!] ALARM ACTIVE!");
        }
        digitalWrite(LED_PIN, finalAlarm ? HIGH : LOW);
        digitalWrite(BUZZER_PIN, finalAlarm ? HIGH : LOW);
      }
    } else {
      Serial.println("[-] HTTP Request Error: " + http.errorToString(httpResponseCode));
    }

    http.end();
  } else {
    Serial.println("[-] Wi-Fi disconnected! Reconnecting...");
    WiFi.reconnect();
  }

  delay(1500);
}