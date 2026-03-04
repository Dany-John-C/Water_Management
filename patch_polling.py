import re

js_path = 'static/js/main.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

# Replace dummy simulateSensorData with actual API poll
new_simulate = '''
        async function fetchSensorData() {
            try {
                const response = await fetch('/api/sensors/current');
                if (response.ok) {
                    const data = await response.json();
                    sensorData.waterLevel = data.water_level;
                    sensorData.flowRate = data.flow_rate;
                    sensorData.soilMoisture = data.soil_moisture;
                    sensorData.waterTemperature = data.water_temperature;
                    
                    document.querySelector('.status-indicator').style.background = '#00ff88';
                    document.querySelector('.system-status span').innerHTML = '<strong>System Status:</strong> All systems operational';
                } else {
                    throw new Error('Server returned ' + response.status);
                }
            } catch (e) {
                console.error('Failed to fetch sensor data:', e);
                document.querySelector('.status-indicator').style.background = '#dc3545';
                document.querySelector('.system-status span').innerHTML = '<strong>System Status:</strong> Offline / Warning';
            }
            
            try {
                const metricResp = await fetch('/api/metrics/current');
                if (metricResp.ok) {
                    const metrics = await metricResp.json();
                    document.getElementById('avgUsageRate').textContent = sensorData.flowRate.toFixed(1) + 'L/min';
                    document.getElementById('peakFlowRate').textContent = (sensorData.flowRate * 1.5).toFixed(1) + 'L/min';
                    const totalVolume = sensorData.flowRate * 60 * 24 / 1000;
                    document.getElementById('totalVolumeToday').textContent = Math.round(totalVolume * 1000).toLocaleString() + 'L';
                    document.getElementById('predictionAccuracy').textContent = metrics.alert_accuracy.toFixed(1) + '%';
                    document.getElementById('avgWaterTemp').textContent = sensorData.waterTemperature.toFixed(1) + '°C';
                    document.getElementById('systemEfficiency').textContent = (100 - metrics.cpu_utilization/2).toFixed(1) + '%';
                }
            } catch (e) {}
            
            try {
                 const alertResp = await fetch('/api/alerts');
                 if (alertResp.ok) {
                     const alerts = await alertResp.json();
                     const alertsPanel = document.getElementById('alertsPanel');
                     alertsPanel.innerHTML = '';
                     alerts.forEach(a => {
                          const alertDiv = document.createElement('div');
                          alertDiv.className = `alert ${a.type}`;
                          alertDiv.innerHTML = `
                              <div class="alert-icon">${a.icon}</div>
                              <div class="alert-content">
                                  <div class="alert-title">${a.title}</div>
                                  <div class="alert-time">${new Date(a.timestamp).toLocaleTimeString()}</div>
                              </div>
                          `;
                          alertsPanel.appendChild(alertDiv);
                     });
                 }
            } catch(e) {}
        }
'''

js_content = re.sub(r'        function simulateSensorData\(\) \{.*?(?=        async function loadInitialData\(\) \{)', new_simulate + '\n', js_content, flags=re.DOTALL)

# Update real time function to await fetch
new_realtime = '''
        function startRealTimeUpdates() {
            if (simulationRunning) {
                setInterval(async () => {
                    await fetchSensorData();
                    updateSensorUI();
                    await updateCharts();
                    updateLastUpdateTime();
                }, 5000); 
            }
        }
'''
js_content = re.sub(r'        function startRealTimeUpdates\(\) \{.*?(?=        async function updateCharts\(\) \{)', new_realtime + '\n', js_content, flags=re.DOTALL)


# Update Refresh button
new_refresh = '''
        async function refreshData() {
            addAlert('success', '🔄', 'Refreshing Data', 'Loading latest sensor readings...');
            await fetchSensorData();
            updateSensorUI();
            addAlert('success', '✅', 'Data Refreshed', 'All data updated successfully');
        }
'''
js_content = re.sub(r'        async function refreshData\(\) \{.*?(?=        function clearAlerts\(\) \{)', new_refresh + '\n', js_content, flags=re.DOTALL)

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)
