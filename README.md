# 🌊 Smart Water Management System (Clean Architecture Refactor)

A comprehensive, scalable IoT-based water management system with real-time monitoring, analytics, and alerting capabilities. Designed with Clean Architecture principles for easy scalability and maintenance.

## ✨ Features

- **Real-Time Monitoring**: Tracks water level, flow rate, soil moisture, and water temperature.
- **Robust Firmware**: ESP8266/Arduino firmware with non-blocking delays and Wi-Fi retry logic.
- **Clean Architecture Backend**: Flask application factored into blueprints, separate models, and controllers.
- **Centralized Alert Engine**: Smart debouncing logic config-driven threshold monitoring.
- **Advanced Dashboard**: Responsive UI, real-time polling with fallbacks, predictive analytics, and Dark Mode.

## 🏗️ Architecture

```text
Sensors -> ESP8266 Firmware -> REST API -> Flask (Blueprints) -> SQLite Database -> Frontend Dashboard
```

1. **Hardware / Firmware Layer (`/firmware`)**
2. **Configuration Layer (`.env`, `config/config.py`)**
3. **Application Layer (`/app`)**
   - Routes (`app/routes/`)
   - Services (`app/services/alert_engine.py`)
   - Models (`app/models/models.py`)
4. **Presentation Layer (`/templates`, `/static`)**

## 🔧 Hardware Wiring Guide (ESP8266 NodeMCU)

| Sensor | Pin on ESP8266 | Description |
|--------|----------------|-------------|
| **HC-SR04** (Water Level)| `D1` (Trig), `D2` (Echo)| Ultrasonic distance sensor |
| **YF-S201** (Flow Rate)| `D3` | Water flow meter (uses interrupt) |
| **YL-69** (Soil Moisture)| `A0` | Analog soil moisture sensor |
| **DS18B20** (Temperature)| `D4` | 1-Wire temperature sensor |

## 🚀 Quick Start & Deployment

### 1. Backend Setup

1. **Clone the repository**
2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment:**
    Review the `.env` file for database bounds and alert thresholds.
4. **Run the Server:**
   ```bash
   python run.py
   ```
   *Note: `run.py` will automatically create the database schemas and spin up dummy sensor data if the table is empty.*

### 2. Firmware Deployment

1. Open `firmware/SmartWaterNode/SmartWaterNode.ino` in the Arduino IDE.
2. Install dependencies via Library Manager:
   - `ArduinoJson` (by Benoit Blanchon)
   - `OneWire` (by Paul Stoffregen)
   - `DallasTemperature` (by Miles Burton)
3. Change `YOUR_WIFI_SSID` and `YOUR_WIFI_PASSWORD`.
4. Change `serverUrl` to point to the backend IPv4 Address (e.g., `http://192.168.1.100:5000/api/sensors`).
5. Flash to the ESP8266.

## 📡 API Endpoints Structure

- `GET /api/sensors/current` - Latest sensor data
- `GET /api/sensors/history` - Historical data for charts
- `POST /api/sensors` - Node endpoint for publishing telemetry
- `GET /api/sensors/predict` - Real predictive analysis
- `GET /api/alerts` - Active alerts list
- `GET /api/metrics/current` - System health stats

## 📈 Future Scalability

Built to easily swap out SQLite for PostgreSQL/MySQL via `.env` adjustments, and modular routes make expanding to MQTT or adding JWT authentication straightforward. All layers are decoupled ensuring a robust IoT system.