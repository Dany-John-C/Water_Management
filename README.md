# 🌊 Smart Water Management System

A comprehensive IoT-based water management system with real-time monitoring, analytics, and alerting capabilities. Features water level, flow rate, soil moisture, and **water temperature** tracking with a modern web dashboard.

## ✨ Features

### 🔧 Sensor Monitoring
- **Water Level**: Real-time tank level monitoring with visual progress indicator
- **Flow Rate**: Water flow measurement in L/min
- **Soil Moisture**: Irrigation monitoring and alerts
- **Water Temperature**: Temperature tracking with freeze/overheat alerts

### 📊 Analytics & Visualization
- Real-time charts with historical data
- Usage vs prediction analytics
- Performance metrics dashboard
- 24-hour data retention and analysis

### 🚨 Smart Alerts
- Automatic threshold-based alerting
- Temperature-based warnings (freeze/overheat)
- Flow rate anomaly detection
- Low moisture irrigation alerts

### 💾 Data Management
- SQLite database with full CRUD operations
- RESTful API for all data operations
- Data export functionality
- Historical data analysis

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- pip (Python package manager)

### Installation & Setup

1. **Clone or download the project files**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the complete system:**
   ```bash
   python run.py
   ```

4. **Access the dashboard:**
   Open your browser to `http://localhost:5000`

The system will automatically:
- Create the SQLite database
- Generate sample historical data
- Start the Flask web server
- Begin the data simulator for live updates

## 🏗️ Architecture

### Backend (Flask)
- **app.py**: Main Flask application with API endpoints
- **Database Models**: SQLAlchemy models for sensors, alerts, and metrics
- **RESTful API**: Complete CRUD operations for all data types

### Frontend (HTML/JavaScript)
- **Responsive Design**: Modern glassmorphism UI with mobile support
- **Real-time Updates**: Live data fetching every 5 seconds
- **Interactive Charts**: Chart.js integration for data visualization
- **Progressive Enhancement**: Works without JavaScript for basic functionality

### Data Simulation
- **data_simulator.py**: Realistic sensor data generation
- **Continuous Updates**: Simulates real IoT sensor behavior
- **Natural Variations**: Temperature cycles, flow patterns, moisture depletion

## 📡 API Endpoints

### Sensor Data
- `GET /api/sensors/current` - Latest sensor readings
- `GET /api/sensors/history` - Historical data (24 hours)
- `POST /api/sensors` - Add new sensor reading

### Alerts
- `GET /api/alerts` - Recent system alerts

### Metrics
- `GET /api/metrics/current` - Current system performance

### Data Export
- `GET /api/export` - Export all data as JSON

## 🗄️ Database Schema

### SensorReading
- `id`, `timestamp`, `water_level`, `flow_rate`, `soil_moisture`, `water_temperature`

### Alert
- `id`, `timestamp`, `alert_type`, `icon`, `title`, `message`, `is_active`

### SystemMetrics
- `id`, `timestamp`, `cpu_utilization`, `response_time`, `throughput`, `storage_util`, `energy_consumption`, `alert_accuracy`

## 🎛️ System Controls

- **Start/Pause**: Control data collection
- **Generate Report**: Create system performance reports
- **Export Data**: Download complete dataset
- **Reset System**: Clear alerts and reset to defaults

## 🔧 Configuration

### Simulation Parameters
Edit `data_simulator.py` to adjust:
- Update intervals
- Sensor value ranges
- Variation patterns
- Alert thresholds

### Database Configuration
Modify `app.py` for:
- Database URL (currently SQLite)
- Data retention periods
- Alert conditions

## 📱 Mobile Support

The dashboard is fully responsive and optimized for:
- Desktop browsers
- Tablets
- Mobile phones
- Touch interfaces

## 🛠️ Development

### Running Components Separately

**Flask Server Only:**
```bash
python app.py
```

**Data Simulator Only:**
```bash
python data_simulator.py
```

### Adding New Sensors
1. Update database models in `app.py`
2. Add API endpoints for new sensor types
3. Update frontend JavaScript to handle new data
4. Modify simulator to generate appropriate data

## 🔍 Troubleshooting

### Common Issues

**Port 5000 already in use:**
- Change the port in `app.py`: `app.run(port=5001)`

**Database errors:**
- Delete `water_management.db` and restart
- Check file permissions in the project directory

**Connection errors:**
- Ensure Flask server is running before starting simulator
- Check firewall settings for port 5000

### Logs & Debugging
- Flask debug mode: Set `debug=True` in `app.py`
- Simulator logs: Check console output for connection status
- Browser console: Check for JavaScript errors

## 📈 Future Enhancements

- [ ] Multi-location support
- [ ] Advanced ML predictions
- [ ] Mobile app integration
- [ ] Cloud database support
- [ ] Real IoT device integration
- [ ] User authentication
- [ ] Historical trend analysis
- [ ] Automated irrigation control

## 🤝 Contributing

Feel free to submit issues, feature requests, or pull requests to improve the system!

## 📄 License

This project is open source and available under the MIT License.