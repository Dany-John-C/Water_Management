/*
 * ═══════════════════════════════════════════════════════════════════
 * AquaIntel — Hardware Diagnostic Test Script
 * ═══════════════════════════════════════════════════════════════════
 * Use this script to test all physical connections.
 * It will cycle through testing the actuators (Buzzer, Servo, Pump)
 * and read all sensors, printing the output to the Serial Monitor.
 *
 * INSTRUCTIONS:
 * 1. Upload this code to your Arduino Uno.
 * 2. Open the Serial Monitor (Tools > Serial Monitor).
 * 3. Set the baud rate to 9600.
 * 4. Watch the outputs and physical hardware.
 * ═══════════════════════════════════════════════════════════════════
 */

#include <Servo.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ── PINS ──
#define ONEWIRE_PIN 2
#define FLOW_PIN 3
#define FLOW_VCC 4
#define FLOW_GND 5
#define ONEWIRE_VCC 6
#define ONEWIRE_GND 7
#define PUMP_IN1_PIN 8
#define PUMP_IN2_PIN 12
#define SERVO_PIN 9
#define BUZZER_PIN 10
#define BUZZER_GND 11
#define MOISTURE_PIN A0
#define MOISTURE_VCC A2
#define MOISTURE_GND A3
#define WATER_LEVEL_PIN A1
#define WATER_LEVEL_VCC A4
#define WATER_LEVEL_GND A5

Servo testServo;
OneWire oneWire(ONEWIRE_PIN);
DallasTemperature tempSensor(&oneWire);

volatile int flowPulses = 0;

void flowISR() {
  flowPulses++;
}

void setup() {
  Serial.begin(9600);
  
  // Power pins setup
  pinMode(FLOW_VCC, OUTPUT); digitalWrite(FLOW_VCC, HIGH);
  pinMode(FLOW_GND, OUTPUT); digitalWrite(FLOW_GND, LOW);
  
  pinMode(ONEWIRE_VCC, OUTPUT); digitalWrite(ONEWIRE_VCC, HIGH);
  pinMode(ONEWIRE_GND, OUTPUT); digitalWrite(ONEWIRE_GND, LOW);
  pinMode(ONEWIRE_PIN, INPUT_PULLUP);
  
  pinMode(BUZZER_GND, OUTPUT); digitalWrite(BUZZER_GND, LOW);
  pinMode(BUZZER_PIN, OUTPUT); digitalWrite(BUZZER_PIN, LOW);
  
  pinMode(MOISTURE_VCC, OUTPUT); digitalWrite(MOISTURE_VCC, LOW);
  pinMode(MOISTURE_GND, OUTPUT); digitalWrite(MOISTURE_GND, LOW);
  
  pinMode(WATER_LEVEL_VCC, OUTPUT); digitalWrite(WATER_LEVEL_VCC, LOW);
  pinMode(WATER_LEVEL_GND, OUTPUT); digitalWrite(WATER_LEVEL_GND, LOW);

  pinMode(PUMP_IN1_PIN, OUTPUT); digitalWrite(PUMP_IN1_PIN, LOW);
  pinMode(PUMP_IN2_PIN, OUTPUT); digitalWrite(PUMP_IN2_PIN, LOW);

  pinMode(FLOW_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(FLOW_PIN), flowISR, FALLING);

  testServo.attach(SERVO_PIN);
  tempSensor.begin();

  Serial.println("\n--- HARDWARE DIAGNOSTIC STARTED ---");
  delay(2000);
}

void loop() {
  Serial.println("\n==================================");
  
  // 1. ACTUATOR TESTS
  Serial.println("[TEST] Activating Buzzer...");
  digitalWrite(BUZZER_PIN, HIGH);
  delay(500);
  digitalWrite(BUZZER_PIN, LOW);

  Serial.println("[TEST] Moving Servo to 90 degrees...");
  testServo.write(90);
  delay(1000);
  Serial.println("[TEST] Moving Servo back to 0 degrees...");
  testServo.write(0);
  delay(1000);

  Serial.println("[TEST] Turning Pump ON for 2 seconds...");
  digitalWrite(PUMP_IN1_PIN, HIGH);
  digitalWrite(PUMP_IN2_PIN, LOW);
  delay(2000);
  Serial.println("[TEST] Turning Pump OFF...");
  digitalWrite(PUMP_IN1_PIN, LOW);
  digitalWrite(PUMP_IN2_PIN, LOW);
  delay(1000);

  // 2. SENSOR TESTS
  Serial.println("--- SENSOR READINGS ---");

  // Water Level
  digitalWrite(WATER_LEVEL_VCC, HIGH);
  delay(10);
  int wl_raw = analogRead(WATER_LEVEL_PIN);
  digitalWrite(WATER_LEVEL_VCC, LOW);
  Serial.print("Water Level Sensor Raw (0-1023): ");
  Serial.println(wl_raw);

  // Moisture
  digitalWrite(MOISTURE_VCC, HIGH);
  delay(10);
  int moist_raw = analogRead(MOISTURE_PIN);
  digitalWrite(MOISTURE_VCC, LOW);
  Serial.print("Soil Moisture Sensor Raw (0-1023): ");
  Serial.println(moist_raw);

  // Temperature
  tempSensor.requestTemperatures();
  float temp = tempSensor.getTempCByIndex(0);
  Serial.print("Temperature (DS18B20): ");
  if (temp == DEVICE_DISCONNECTED_C) {
    Serial.println("Disconnected / Error!");
  } else {
    Serial.print(temp); Serial.println(" °C");
  }

  // Flow Sensor
  noInterrupts();
  int pulses = flowPulses;
  flowPulses = 0;
  interrupts();
  Serial.print("Flow Sensor Pulses caught in last cycle: ");
  Serial.println(pulses);
  if(pulses == 0) {
    Serial.println("   (Try blowing into or running water through the flow sensor)");
  }

  Serial.println("==================================");
  Serial.println("Waiting 5 seconds before next cycle...");
  delay(5000);
}
