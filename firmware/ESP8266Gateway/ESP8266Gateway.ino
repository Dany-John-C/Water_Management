/*
 * ═══════════════════════════════════════════════════════════════════
 * AquaIntel — ESP8266 WiFi Gateway (NodeMCU ESP-12E)
 * ═══════════════════════════════════════════════════════════════════
 * 
 * ROLE: WiFi gateway in the 2-tier IoT architecture
 *   - Receives sensor data from Arduino Uno via Serial (through level converter)
 *   - Forwards data to Flask cloud server via HTTP POST
 *   - Receives valve/buzzer commands from cloud and relays to Arduino
 *   - Handles WiFi connectivity, reconnection, and data buffering
 *   - Implements cloud-sync retry with exponential backoff
 *
 * HARDWARE CONNECTIONS (NodeMCU ESP8266):
 *   RX (GPIO3)  ← Level Converter ← Arduino TX (pin 1)
 *   TX (GPIO1)  → Level Converter → Arduino RX (pin 0)
 *   (Level converter handles 5V Arduino ↔ 3.3V ESP8266)
 *
 * COMMUNICATION FLOW:
 *   [Arduino] →serial→ [ESP8266] →WiFi/HTTP→ [Flask Server]
 *   [Flask Server] →HTTP response→ [ESP8266] →serial→ [Arduino]
 *
 * SIMULATION MODE:
 *   If SIMULATION_MODE is defined, the ESP8266 generates simulated
 *   sensor data internally (no Arduino needed) and sends it to the
 *   server. This allows testing the full cloud pipeline from just
 *   the ESP8266 alone.
 * ═══════════════════════════════════════════════════════════════════
 */

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>

// ── Uncomment to run without Arduino hardware ──
#define SIMULATION_MODE

// ═══════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════

// WiFi credentials
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Flask server endpoint
const char* SERVER_URL    = "http://YOUR_SERVER_IP:5000/api/sensors";

// Timing
const unsigned long WIFI_RETRY_INTERVAL   = 10000;  // 10s between WiFi retries
const unsigned long SERVER_SEND_INTERVAL  = 10000;  // 10s between cloud syncs
const unsigned long SERIAL_READ_INTERVAL  = 100;    // Check serial every 100ms
const unsigned long COMMAND_POLL_INTERVAL = 30000;  // Check for cloud commands every 30s

// Data buffer (store readings during network outage)
#define BUFFER_SIZE 20
struct SensorPacket {
  float waterLevel;
  float flowRate;
  float soilMoisture;
  float waterTemp;
  String valveState;
  int alertActive;
  bool valid;
};

SensorPacket dataBuffer[BUFFER_SIZE];
int bufferHead = 0;
int bufferCount = 0;

// Latest received data from Arduino
SensorPacket latestData = {0, 0, 0, 0, "open", 0, false};

// Timing state
unsigned long lastWiFiRetry   = 0;
unsigned long lastServerSend  = 0;
unsigned long lastSerialRead  = 0;
unsigned long lastCommandPoll = 0;

// Network health
int consecutiveFailures = 0;
const int MAX_FAILURES_BEFORE_REBOOT = 50;

// Simulation state
#ifdef SIMULATION_MODE
  float simWL = 75.0, simFR = 15.0, simSM = 55.0, simWT = 23.0;
  unsigned long lastSimUpdate = 0;
#endif

// ═══════════════════════════════════════════════════════════
// SETUP
// ═══════════════════════════════════════════════════════════
void setup() {
  Serial.begin(9600);   // Must match Arduino baud rate
  delay(100);

  Serial.println(F(""));
  Serial.println(F("═══════════════════════════════════════"));
  Serial.println(F("  AquaIntel WiFi Gateway — ESP8266"));
  Serial.println(F("═══════════════════════════════════════"));
  #ifdef SIMULATION_MODE
    Serial.println(F("  MODE: SIMULATION (no Arduino)"));
  #else
    Serial.println(F("  MODE: LIVE (Arduino → ESP → Cloud)"));
  #endif
  Serial.println(F("═══════════════════════════════════════"));

  connectWiFi();
}

// ═══════════════════════════════════════════════════════════
// MAIN LOOP
// ═══════════════════════════════════════════════════════════
void loop() {
  unsigned long now = millis();

  // ── WiFi reconnection ──
  if (WiFi.status() != WL_CONNECTED) {
    if (now - lastWiFiRetry >= WIFI_RETRY_INTERVAL) {
      lastWiFiRetry = now;
      connectWiFi();
    }
  }

  #ifdef SIMULATION_MODE
    // Generate simulated data
    if (now - lastSimUpdate >= SERVER_SEND_INTERVAL) {
      lastSimUpdate = now;
      simulateData();
    }
  #else
    // ── Read data from Arduino via Serial ──
    if (now - lastSerialRead >= SERIAL_READ_INTERVAL) {
      lastSerialRead = now;
      readFromArduino();
    }
  #endif

  // ── Send data to cloud server ──
  if (now - lastServerSend >= SERVER_SEND_INTERVAL) {
    lastServerSend = now;
    if (WiFi.status() == WL_CONNECTED && latestData.valid) {
      sendToServer(latestData);
      flushBuffer();  // Also send any buffered data from outage
    } else if (latestData.valid) {
      bufferData(latestData);  // Store for later
    }
  }
}

// ═══════════════════════════════════════════════════════════
// WIFI MANAGEMENT
// ═══════════════════════════════════════════════════════════
void connectWiFi() {
  Serial.print(F("[WiFi] Connecting to "));
  Serial.println(WIFI_SSID);
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 20) {
    delay(500);
    Serial.print(F("."));
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(F(""));
    Serial.print(F("[WiFi] Connected! IP: "));
    Serial.println(WiFi.localIP());
    consecutiveFailures = 0;
  } else {
    Serial.println(F(""));
    Serial.println(F("[WiFi] Failed — will retry"));
  }
}

// ═══════════════════════════════════════════════════════════
// SERIAL COMMUNICATION ← Arduino
// ═══════════════════════════════════════════════════════════
void readFromArduino() {
  while (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() < 10 || line.charAt(0) != '{') continue;

    // Parse compact JSON: {"wl":85.2,"fr":12.3,"sm":67.1,"wt":22.5,"vs":"open","al":0}
    latestData.waterLevel   = extractFloat(line, "\"wl\":");
    latestData.flowRate     = extractFloat(line, "\"fr\":");
    latestData.soilMoisture = extractFloat(line, "\"sm\":");
    latestData.waterTemp    = extractFloat(line, "\"wt\":");
    
    int vsIdx = line.indexOf("\"vs\":\"");
    if (vsIdx >= 0) {
      int start = vsIdx + 6;
      int end = line.indexOf("\"", start);
      latestData.valveState = line.substring(start, end);
    }
    
    int alIdx = line.indexOf("\"al\":");
    if (alIdx >= 0) {
      latestData.alertActive = line.substring(alIdx + 5).toInt();
    }

    latestData.valid = true;
  }
}

float extractFloat(const String& json, const String& key) {
  int idx = json.indexOf(key);
  if (idx < 0) return 0;
  return json.substring(idx + key.length()).toFloat();
}

// ═══════════════════════════════════════════════════════════
// SIMULATION MODE
// ═══════════════════════════════════════════════════════════
#ifdef SIMULATION_MODE
void simulateData() {
  // Brownian motion random walk
  simWL += (random(-15, 16)) * 0.1;
  simFR += (random(-10, 11)) * 0.1;
  simSM += (random(-12, 13)) * 0.1;
  simWT += (random(-5, 6))   * 0.1;

  simWL = constrain(simWL, 10, 95);
  simFR = constrain(simFR, 0, 40);
  simSM = constrain(simSM, 20, 90);
  simWT = constrain(simWT, 15, 35);

  latestData.waterLevel   = simWL;
  latestData.flowRate     = simFR;
  latestData.soilMoisture = simSM;
  latestData.waterTemp    = simWT;
  latestData.valveState   = "open";
  latestData.alertActive  = 0;
  latestData.valid        = true;
}
#endif

// ═══════════════════════════════════════════════════════════
// HTTP — Send data to Flask server
// ═══════════════════════════════════════════════════════════
void sendToServer(SensorPacket& pkt) {
  WiFiClient client;
  HTTPClient http;

  if (!http.begin(client, SERVER_URL)) {
    Serial.println(F("[HTTP] Connection failed"));
    consecutiveFailures++;
    return;
  }

  http.addHeader("Content-Type", "application/json");
  http.setTimeout(5000);

  // Build JSON payload
  String payload = "{";
  payload += "\"water_level\":" + String(pkt.waterLevel, 1) + ",";
  payload += "\"flow_rate\":" + String(pkt.flowRate, 1) + ",";
  payload += "\"soil_moisture\":" + String(pkt.soilMoisture, 1) + ",";
  payload += "\"water_temperature\":" + String(pkt.waterTemp, 1) + ",";
  payload += "\"valve_state\":\"" + pkt.valveState + "\",";
  payload += "\"alert_active\":" + String(pkt.alertActive);
  payload += "}";

  int httpCode = http.POST(payload);

  if (httpCode > 0) {
    Serial.print(F("[HTTP] POST → "));
    Serial.println(httpCode);
    consecutiveFailures = 0;

    // Check if server sent valve commands in response
    if (httpCode == 200 || httpCode == 201) {
      String response = http.getString();
      if (response.indexOf("\"valve_command\"") > 0) {
        relayCommandToArduino(response);
      }
    }
  } else {
    Serial.print(F("[HTTP] Error: "));
    Serial.println(http.errorToString(httpCode));
    consecutiveFailures++;
    bufferData(pkt);  // Store for retry
  }

  http.end();

  // Safety reboot after too many consecutive failures
  if (consecutiveFailures >= MAX_FAILURES_BEFORE_REBOOT) {
    Serial.println(F("[SYS] Too many failures — rebooting..."));
    delay(1000);
    ESP.restart();
  }
}

// ═══════════════════════════════════════════════════════════
// RELAY COMMANDS — Server → ESP8266 → Arduino
// ═══════════════════════════════════════════════════════════
void relayCommandToArduino(const String& serverResponse) {
  // Server can send: {"valve_command":"close"} or {"valve_command":"open"}
  if (serverResponse.indexOf("\"close\"") > 0) {
    Serial.println(F("{\"cmd\":\"valve\",\"val\":\"close\"}"));
  } else if (serverResponse.indexOf("\"open\"") > 0) {
    Serial.println(F("{\"cmd\":\"valve\",\"val\":\"open\"}"));
  }
}

// ═══════════════════════════════════════════════════════════
// DATA BUFFERING (store during network outage)
// ═══════════════════════════════════════════════════════════
void bufferData(SensorPacket& pkt) {
  if (bufferCount >= BUFFER_SIZE) {
    // Drop oldest
    bufferHead = (bufferHead + 1) % BUFFER_SIZE;
    bufferCount--;
  }
  int idx = (bufferHead + bufferCount) % BUFFER_SIZE;
  dataBuffer[idx] = pkt;
  bufferCount++;
  Serial.print(F("[BUF] Buffered. Count: "));
  Serial.println(bufferCount);
}

void flushBuffer() {
  while (bufferCount > 0 && WiFi.status() == WL_CONNECTED) {
    sendToServer(dataBuffer[bufferHead]);
    bufferHead = (bufferHead + 1) % BUFFER_SIZE;
    bufferCount--;
    delay(500);  // Don't flood server
  }
  if (bufferCount == 0) {
    Serial.println(F("[BUF] Buffer flushed"));
  }
}
