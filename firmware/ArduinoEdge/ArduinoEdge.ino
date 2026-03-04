/*
 * ═══════════════════════════════════════════════════════════════════
 * AquaIntel — Arduino Uno R3 Edge Node
 * ═══════════════════════════════════════════════════════════════════
 * 
 * ROLE: Edge processor in the 2-tier IoT architecture
 *   - Reads all 4 sensors (HC-SR04, YF-S201, YL-69, DS18B20)
 *   - Controls actuators (SG90 servo valve, buzzer)
 *   - Performs LOCAL edge processing (threshold checks, delta filtering)
 *   - Sends filtered data to ESP8266 via Serial (through level converter)
 *   - Receives valve commands from ESP8266 (from cloud server)
 *
 * HARDWARE CONNECTIONS (Arduino Uno R3):
 *   Pin 2  → HC-SR04 TRIG  (ultrasonic water level)
 *   Pin 3  → HC-SR04 ECHO  (ultrasonic water level)
 *   Pin 4  → YF-S201 Signal (water flow, interrupt-capable via PCINT)
 *   Pin 5  → DS18B20 Data   (OneWire temperature)
 *   Pin 9  → SG90 Servo     (valve actuator, PWM)
 *   Pin 10 → Buzzer         (active buzzer, alert)
 *   A0     → YL-69/FC-28    (soil moisture, analog)
 *   TX/RX  → Level Converter → ESP8266 (Serial @ 9600 baud)
 *
 * COMMUNICATION PROTOCOL (Serial JSON):
 *   Arduino → ESP8266:  {"wl":85.2,"fr":12.3,"sm":67.1,"wt":22.5,"vs":"open","al":0}
 *   ESP8266 → Arduino:  {"cmd":"valve","val":"close"} or {"cmd":"valve","val":"open"}
 *                        {"cmd":"buzz","val":1}  (1=on, 0=off)
 *                        {"cmd":"interval","val":5000}  (adaptive sampling)
 *
 * SIMULATION MODE:
 *   If SIMULATION_MODE is defined, sensor reads are replaced with
 *   realistic random values so the full system works without hardware.
 *   Servo and buzzer commands are logged to Serial instead of actuated.
 * ═══════════════════════════════════════════════════════════════════
 */

#include <Servo.h>

// ── Uncomment this line to run in SIMULATION MODE (no hardware needed) ──
#define SIMULATION_MODE

#ifndef SIMULATION_MODE
  #include <OneWire.h>
  #include <DallasTemperature.h>
#endif

// ═══════════════════════════════════════════════════════════
// PIN DEFINITIONS
// ═══════════════════════════════════════════════════════════
#define TRIG_PIN      2     // HC-SR04 Trigger
#define ECHO_PIN      3     // HC-SR04 Echo
#define FLOW_PIN      4     // YF-S201 Signal (using pin-change interrupt)
#define ONEWIRE_PIN   5     // DS18B20 Data
#define SERVO_PIN     9     // SG90 Servo (valve)
#define BUZZER_PIN    10    // Active Buzzer
#define MOISTURE_PIN  A0    // YL-69 Analog

// ═══════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════
unsigned long sensorInterval = 5000;       // Default: read every 5 seconds
const unsigned long SERIAL_CHECK_INTERVAL = 100;  // Check serial every 100ms

// Edge processing thresholds (local alerts without cloud)
const float WATER_LEVEL_CRITICAL_LOW  = 15.0;   // % — buzz if below
const float WATER_LEVEL_CRITICAL_HIGH = 95.0;   // % — buzz if above
const float FLOW_RATE_MAX             = 45.0;   // L/min — possible pipe burst
const float SOIL_MOISTURE_FLOOD       = 92.0;   // % — possible flood/leak

// Delta compression (don't send if change is tiny)
const float DELTA_WATER_LEVEL  = 0.5;   // %
const float DELTA_FLOW_RATE    = 0.3;   // L/min
const float DELTA_MOISTURE     = 0.5;   // %
const float DELTA_TEMPERATURE  = 0.2;   // °C

// Tank physical dimensions
const float TANK_DEPTH_CM = 100.0;  // Ultrasonic: 100cm max depth

// ═══════════════════════════════════════════════════════════
// GLOBAL STATE
// ═══════════════════════════════════════════════════════════
Servo valveServo;

#ifndef SIMULATION_MODE
  OneWire oneWire(ONEWIRE_PIN);
  DallasTemperature tempSensor(&oneWire);
#endif

// Current sensor values
float waterLevel    = 0.0;
float flowRate      = 0.0;
float soilMoisture  = 0.0;
float waterTemp     = 0.0;

// Previous values for delta compression
float prevWaterLevel   = -999;
float prevFlowRate     = -999;
float prevSoilMoisture = -999;
float prevWaterTemp    = -999;

// Valve state
bool valveOpen = true;
const int VALVE_OPEN_ANGLE  = 0;    // Servo angle for open
const int VALVE_CLOSE_ANGLE = 90;   // Servo angle for closed

// Buzzer state
bool buzzerActive = false;

// Flow sensor interrupt
volatile unsigned int flowPulseCount = 0;
unsigned long lastFlowCalcTime = 0;

// Timing
unsigned long lastSensorRead  = 0;
unsigned long lastSerialCheck = 0;

// Simulation state
#ifdef SIMULATION_MODE
  float simWaterLevel   = 75.0;
  float simFlowRate     = 15.0;
  float simSoilMoisture = 55.0;
  float simWaterTemp    = 23.0;
#endif

// ═══════════════════════════════════════════════════════════
// INTERRUPT SERVICE ROUTINE — Flow Sensor
// ═══════════════════════════════════════════════════════════
void flowPulseISR() {
  flowPulseCount++;
}

// ═══════════════════════════════════════════════════════════
// SETUP
// ═══════════════════════════════════════════════════════════
void setup() {
  Serial.begin(9600);  // Matches ESP8266 baud rate through level converter
  delay(100);

  // Pin modes
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(FLOW_PIN, INPUT_PULLUP);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  // Servo
  valveServo.attach(SERVO_PIN);
  valveServo.write(VALVE_OPEN_ANGLE);  // Start with valve open

  // Flow sensor interrupt (Pin Change Interrupt for pin 4)
  attachInterrupt(digitalPinToInterrupt(FLOW_PIN), flowPulseISR, FALLING);

  // Temperature sensor
  #ifndef SIMULATION_MODE
    tempSensor.begin();
  #endif

  lastFlowCalcTime = millis();

  // Boot message (will be visible on serial monitor)
  Serial.println(F(""));
  Serial.println(F("═══════════════════════════════════════"));
  Serial.println(F("  AquaIntel Edge Node — Arduino Uno"));
  Serial.println(F("═══════════════════════════════════════"));
  #ifdef SIMULATION_MODE
    Serial.println(F("  MODE: SIMULATION (no hardware)"));
  #else
    Serial.println(F("  MODE: LIVE HARDWARE"));
  #endif
  Serial.println(F("═══════════════════════════════════════"));
  Serial.println(F(""));
}

// ═══════════════════════════════════════════════════════════
// MAIN LOOP
// ═══════════════════════════════════════════════════════════
void loop() {
  unsigned long now = millis();

  // ── Check for commands from ESP8266 ──
  if (now - lastSerialCheck >= SERIAL_CHECK_INTERVAL) {
    lastSerialCheck = now;
    checkIncomingCommands();
  }

  // ── Read sensors at configured interval ──
  if (now - lastSensorRead >= sensorInterval) {
    lastSensorRead = now;

    readAllSensors();
    edgeProcessing();    // Local threshold checks + buzzer
    
    if (shouldTransmit()) {
      transmitToESP8266();
      updatePreviousValues();
    }
  }
}

// ═══════════════════════════════════════════════════════════
// SENSOR READING
// ═══════════════════════════════════════════════════════════
void readAllSensors() {
  #ifdef SIMULATION_MODE
    simulateSensors();
  #else
    readUltrasonic();
    readSoilMoisture();
    readTemperature();
    calculateFlowRate();
  #endif
}

// ── Real hardware sensor reads ──
#ifndef SIMULATION_MODE

void readUltrasonic() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000); // 30ms timeout
  if (duration == 0) {
    // Sensor timeout — keep previous value
    return;
  }
  float distanceCm = duration * 0.034 / 2.0;
  waterLevel = constrain(((TANK_DEPTH_CM - distanceCm) / TANK_DEPTH_CM) * 100.0, 0, 100);
}

void readSoilMoisture() {
  int raw = analogRead(MOISTURE_PIN);
  // YL-69: 1023 = dry, ~300 = wet — map to 0-100%
  soilMoisture = constrain(map(raw, 1023, 300, 0, 100), 0, 100);
}

void readTemperature() {
  tempSensor.requestTemperatures();
  float t = tempSensor.getTempCByIndex(0);
  if (t != DEVICE_DISCONNECTED_C && t > -50 && t < 80) {
    waterTemp = t;
  }
  // else keep previous value (sensor error)
}

void calculateFlowRate() {
  unsigned long now = millis();
  unsigned long elapsed = now - lastFlowCalcTime;
  if (elapsed > 0) {
    // YF-S201: ~4.5 pulses per second per L/min
    noInterrupts();
    unsigned int pulses = flowPulseCount;
    flowPulseCount = 0;
    interrupts();

    flowRate = ((1000.0 / (float)elapsed) * (float)pulses) / 4.5;
    lastFlowCalcTime = now;
  }
}

#endif // !SIMULATION_MODE

// ── Simulation mode — realistic random sensor values ──
#ifdef SIMULATION_MODE

void simulateSensors() {
  // Brownian-motion style: small random walk around current value
  simWaterLevel   += random(-15, 16) * 0.1;
  simFlowRate     += random(-10, 11) * 0.1;
  simSoilMoisture += random(-12, 13) * 0.1;
  simWaterTemp    += random(-5, 6)   * 0.1;

  // Clamp to realistic ranges
  simWaterLevel   = constrain(simWaterLevel,   10, 95);
  simFlowRate     = constrain(simFlowRate,      0, 40);
  simSoilMoisture = constrain(simSoilMoisture, 20, 90);
  simWaterTemp    = constrain(simWaterTemp,     15, 35);

  waterLevel   = simWaterLevel;
  flowRate     = simFlowRate;
  soilMoisture = simSoilMoisture;
  waterTemp    = simWaterTemp;
}

#endif

// ═══════════════════════════════════════════════════════════
// EDGE PROCESSING (LOCAL — no cloud needed)
// ═══════════════════════════════════════════════════════════
void edgeProcessing() {
  bool alert = false;

  // Critical water level
  if (waterLevel < WATER_LEVEL_CRITICAL_LOW) {
    alert = true;
  }
  if (waterLevel > WATER_LEVEL_CRITICAL_HIGH) {
    alert = true;
  }

  // Possible pipe burst
  if (flowRate > FLOW_RATE_MAX) {
    alert = true;
    // Auto-close valve locally (edge decision — no cloud latency!)
    if (valveOpen) {
      closeValve();
    }
  }

  // Flood/leak detection
  if (soilMoisture > SOIL_MOISTURE_FLOOD && flowRate < 1.0) {
    // High moisture + no flow = possible underground leak
    alert = true;
  }

  // Activate buzzer on critical alert
  if (alert && !buzzerActive) {
    activateBuzzer();
  } else if (!alert && buzzerActive) {
    deactivateBuzzer();
  }
}

// ═══════════════════════════════════════════════════════════
// DELTA COMPRESSION — only transmit if values changed enough
// ═══════════════════════════════════════════════════════════
bool shouldTransmit() {
  if (prevWaterLevel < -900) return true;  // First reading — always send
  
  if (abs(waterLevel   - prevWaterLevel)   > DELTA_WATER_LEVEL)  return true;
  if (abs(flowRate     - prevFlowRate)     > DELTA_FLOW_RATE)    return true;
  if (abs(soilMoisture - prevSoilMoisture) > DELTA_MOISTURE)     return true;
  if (abs(waterTemp    - prevWaterTemp)    > DELTA_TEMPERATURE)  return true;

  return false;  // No significant change — save bandwidth
}

void updatePreviousValues() {
  prevWaterLevel   = waterLevel;
  prevFlowRate     = flowRate;
  prevSoilMoisture = soilMoisture;
  prevWaterTemp    = waterTemp;
}

// ═══════════════════════════════════════════════════════════
// SERIAL COMMUNICATION → ESP8266
// ═══════════════════════════════════════════════════════════
void transmitToESP8266() {
  // Compact JSON to minimize serial bandwidth
  // {"wl":85.2,"fr":12.3,"sm":67.1,"wt":22.5,"vs":"open","al":0}
  Serial.print(F("{\"wl\":"));
  Serial.print(waterLevel, 1);
  Serial.print(F(",\"fr\":"));
  Serial.print(flowRate, 1);
  Serial.print(F(",\"sm\":"));
  Serial.print(soilMoisture, 1);
  Serial.print(F(",\"wt\":"));
  Serial.print(waterTemp, 1);
  Serial.print(F(",\"vs\":\""));
  Serial.print(valveOpen ? F("open") : F("closed"));
  Serial.print(F("\",\"al\":"));
  Serial.print(buzzerActive ? 1 : 0);
  Serial.println(F("}"));
}

// ═══════════════════════════════════════════════════════════
// INCOMING COMMANDS FROM ESP8266 (from cloud server)
// ═══════════════════════════════════════════════════════════
void checkIncomingCommands() {
  if (!Serial.available()) return;

  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() < 5) return;

  // Parse simple command format: {"cmd":"valve","val":"close"}
  if (line.indexOf("\"valve\"") > 0) {
    if (line.indexOf("\"close\"") > 0) {
      closeValve();
    } else if (line.indexOf("\"open\"") > 0) {
      openValve();
    }
  }
  else if (line.indexOf("\"buzz\"") > 0) {
    if (line.indexOf("\"1\"") > 0 || line.indexOf(":1") > 0) {
      activateBuzzer();
    } else {
      deactivateBuzzer();
    }
  }
  else if (line.indexOf("\"interval\"") > 0) {
    // Adaptive sampling: cloud tells us to change read interval
    int valIdx = line.indexOf("\"val\":");
    if (valIdx > 0) {
      String valStr = line.substring(valIdx + 6);
      valStr.trim();
      unsigned long newInterval = valStr.toInt();
      if (newInterval >= 1000 && newInterval <= 60000) {
        sensorInterval = newInterval;
      }
    }
  }
}

// ═══════════════════════════════════════════════════════════
// ACTUATORS
// ═══════════════════════════════════════════════════════════
void closeValve() {
  #ifdef SIMULATION_MODE
    // Just update state, no hardware
  #else
    valveServo.write(VALVE_CLOSE_ANGLE);
  #endif
  valveOpen = false;
}

void openValve() {
  #ifdef SIMULATION_MODE
    // Just update state
  #else
    valveServo.write(VALVE_OPEN_ANGLE);
  #endif
  valveOpen = true;
}

void activateBuzzer() {
  #ifdef SIMULATION_MODE
    // Just update state
  #else
    digitalWrite(BUZZER_PIN, HIGH);
  #endif
  buzzerActive = true;
}

void deactivateBuzzer() {
  #ifdef SIMULATION_MODE
    // Just update state
  #else
    digitalWrite(BUZZER_PIN, LOW);
  #endif
  buzzerActive = false;
}
