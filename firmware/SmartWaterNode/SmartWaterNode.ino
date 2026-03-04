/*
 * ═══════════════════════════════════════════════════════════════════
 * AquaIntel — Legacy Single-Board Firmware (ESP8266 Only)
 * ═══════════════════════════════════════════════════════════════════
 * 
 * NOTE: This is the LEGACY single-board version. For the full 
 * 2-tier edge-cloud architecture, see:
 *   firmware/ArduinoEdge/ArduinoEdge.ino     — Arduino Uno (Edge Node)
 *   firmware/ESP8266Gateway/ESP8266Gateway.ino — ESP8266 (WiFi Gateway)
 *
 * The 2-board design provides:
 *   ✅ SG90 servo valve control (Arduino pin 9)
 *   ✅ Buzzer alerts (Arduino pin 10)
 *   ✅ Edge-local processing (threshold checks without cloud)
 *   ✅ Delta compression (only transmit significant changes)
 *   ✅ Data buffering during network outages
 *   ✅ Adaptive sampling interval (cloud-controlled)
 * ═══════════════════════════════════════════════════════════════════
 */

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h>

// --- WiFi Credentials ---
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// --- Backend API ---
const String serverUrl = "http://YOUR_SERVER_IP:5000/api/sensors";

// --- Pin Definitions ---
// Ultrasonic Sensor (HC-SR04) - Water Level
#define TRIG_PIN D1
#define ECHO_PIN D2
// Flow Sensor (YF-S201)
#define FLOW_PIN D3
// Soil Moisture (YL-69)
#define MOISTURE_PIN A0
// DS18B20 Temperature Sensor
#define ONE_WIRE_BUS D4

// --- Global Variables ---
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature tempSensor(&oneWire);

// Non-blocking delay timers
unsigned long lastSensorReadTime = 0;
const unsigned long sensorInterval = 5000; // Read every 5 seconds
unsigned long lastWifiRetryTime = 0;
const unsigned long wifiRetryInterval = 10000; // Retry wifi every 10 seconds

// Sensor State Variables
float currentWaterLevel = 0.0;
float currentFlowRate = 0.0;
float currentSoilMoisture = 0.0;
float currentTemperature = 0.0;

// Flow Sensor Interrupt Variables
volatile int flowPulseCount = 0;
unsigned long oldFlowTime = 0;

// Interrupt Service Routine for Flow Sensor
ICACHE_RAM_ATTR void pulseCounter() {
  flowPulseCount++;
}

void setup() {
  Serial.begin(115200);
  delay(10);
  Serial.println("\n--- Smart Water Management Node Starting ---");

  // Init Pins
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(FLOW_PIN, INPUT_PULLUP);
  
  attachInterrupt(digitalPinToInterrupt(FLOW_PIN), pulseCounter, FALLING);

  // Init Temp Sensor
  tempSensor.begin();

  // Connect to WiFi
  connectWiFi();
}

void loop() {
  unsigned long currentMillis = millis();

  // Handle WiFi Reconnection Non-Blocking
  if (WiFi.status() != WL_CONNECTED) {
    if (currentMillis - lastWifiRetryTime >= wifiRetryInterval) {
      Serial.println("WiFi disconnected. Attempting to reconnect...");
      connectWiFi();
      lastWifiRetryTime = currentMillis;
    }
  }

  // Handle Sensor Reading Non-Blocking
  if (currentMillis - lastSensorReadTime >= sensorInterval) {
    lastSensorReadTime = currentMillis;
    
    readAllSensors();
    
    if (WiFi.status() == WL_CONNECTED) {
       sendDataToBackend();
    } else {
       Serial.println("Cannot send data: WiFi Disconnected.");
    }
  }
}

// --- Helper Functions ---

void connectWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  
  // Wait max 10 seconds for connection in setup, otherwise let loop handle non-blocking retry
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 20) {
    delay(500);
    Serial.print(".");
    retries++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected.");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWiFi connection failed. Will retry later.");
  }
}

void readAllSensors() {
  Serial.println("Reading Sensors...");
  currentWaterLevel = readUltrasonic();
  currentSoilMoisture = readSoilMoisture();
  currentTemperature = readTemperature();
  currentFlowRate = calculateFlowRate();
  
  Serial.printf("Level: %.1f%% | Flow: %.1f L/min | Moisture: %.1f%% | Temp: %.1fC\n", 
                currentWaterLevel, currentFlowRate, currentSoilMoisture, currentTemperature);
}

float readUltrasonic() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  long duration = pulseIn(ECHO_PIN, HIGH);
  float distanceCm = duration * 0.034 / 2;
  
  // Convert distance to a percentage (Assume tank depth is 100cm for example)
  float maxDepth = 100.0; 
  float percentage = ((maxDepth - distanceCm) / maxDepth) * 100.0;
  
  if(percentage < 0) percentage = 0;
  if(percentage > 100) percentage = 100;
  return percentage;
}

float readSoilMoisture() {
  int rawValue = analogRead(MOISTURE_PIN);
  // Map analog value 1024 (dry) to 0 (wet) to 0-100%
  // Calibrate these boundaries based on actual sensor
  float percentage = map(rawValue, 1024, 300, 0, 100); 
  if(percentage < 0) percentage = 0;
  if(percentage > 100) percentage = 100;
  return percentage;
}

float readTemperature() {
  tempSensor.requestTemperatures(); 
  return tempSensor.getTempCByIndex(0);
}

float calculateFlowRate() {
  unsigned long currentMillis = millis();
  unsigned long timePassed = currentMillis - oldFlowTime;
  float flowRate = 0.0;
  
  if (timePassed > 0) {
    // Calibration factor for YF-S201 is approx 4.5 pulses per second per liter/min
    flowRate = ((1000.0 / timePassed) * flowPulseCount) / 4.5;
    
    // Reset counters
    oldFlowTime = currentMillis;
    flowPulseCount = 0;
  }
  return flowRate;
}

void sendDataToBackend() {
  WiFiClient client;
  HTTPClient http;
  
  Serial.print("Sending POST request to ");
  Serial.println(serverUrl);
  
  if (http.begin(client, serverUrl)) {
    http.addHeader("Content-Type", "application/json");
    
    // Construct JSON Payload
    StaticJsonDocument<200> doc;
    doc["water_level"] = currentWaterLevel;
    doc["flow_rate"] = currentFlowRate;
    doc["soil_moisture"] = currentSoilMoisture;
    doc["water_temperature"] = currentTemperature;
    
    String jsonPayload;
    serializeJson(doc, jsonPayload);
    
    int httpResponseCode = http.POST(jsonPayload);
    
    if (httpResponseCode > 0) {
      Serial.print("HTTP Response code: ");
      Serial.println(httpResponseCode);
    } else {
      Serial.print("Error code: ");
      Serial.println(httpResponseCode);
      Serial.println(http.errorToString(httpResponseCode).c_str());
    }
    
    http.end();
  } else {
    Serial.println("Unable to connect to server");
  }
}
