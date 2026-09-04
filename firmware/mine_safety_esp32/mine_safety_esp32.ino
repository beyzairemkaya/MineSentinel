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
#define MQ2_PIN    34
#define LED_PIN    2      
#define BUZZER_PIN 4      

const int MPU_ADDR = 0x68; // Scanner'ın bulduğu kesin adres
unsigned long eventStartTime = 0; 
bool hazardActive = false;     

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
  Wire.write(0x6B); // PWR_MGMT_1 register
  Wire.write(0);    // 0 yazarak uyku modundan çıkarıyoruz
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
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\n[+] Wi-Fi connected successfully.");
  Serial.print("[+] Assigned ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // 1. Direct I2C Read from MPU6050 Registers (0x3B to 0x40)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B); // ACCEL_XOUT_H register
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

  // 3. Hazard Duration Tracking
  bool isDanger = (gasPpm > 400.0 || accelG > 2.0 || accelG < 0.4);

  if (isDanger) {
    if (!hazardActive) {
      hazardActive = true;
      eventStartTime = millis();
    }
  } else {
    hazardActive = false;
  }

  float durationSec = 0.0;
  if (hazardActive) {
    durationSec = (float)(millis() - eventStartTime) / 1000.0;
    if (durationSec > 10.0) durationSec = 10.0;
  }

  // 4. Send Telemetry via HTTP POST
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(2500);

    /*
    StaticJsonDocument<256> doc;
    doc["gas_ppm"] = gasPpm;
    doc["accel_g"] = accelG;
    doc["duration_sec"] = durationSec;
    doc["miner_id"] = "MINER-ESP32";
    doc["zone"] = "Sector-3";
    */
    StaticJsonDocument<256> doc;
    doc["gas_ppm"] = gasPpm;
    doc["accel_g"] = 6.0;       // <-- Sabit yüksek darbe/çökme ivmesi
    doc["duration_sec"] = 10.0;  // <-- 6 saniyedir süren tehlike
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
        if (actionRequired) {
          Serial.println("[!] CRITICAL ALARM: Evacuate zone!");
          digitalWrite(LED_PIN, HIGH);
          digitalWrite(BUZZER_PIN, HIGH);
        } else {
          digitalWrite(LED_PIN, LOW);
          digitalWrite(BUZZER_PIN, LOW);
        }
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