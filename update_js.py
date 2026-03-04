import re

css_path = 'static/css/style.css'
js_path = 'static/js/main.js'

with open(css_path, 'a', encoding='utf-8') as f:
    f.write('''\n
/* --- Dark Mode --- */
body.dark-mode { background: linear-gradient(135deg, #1e2024 0%, #2b2b36 100%); color: #f0f0f0; }
body.dark-mode .card, body.dark-mode .status-bar, body.dark-mode .controls-panel, body.dark-mode .header { background: rgba(30, 30, 40, 0.95); color: #e0e0e0; border-color: rgba(255, 255, 255, 0.1); }
body.dark-mode .card h3, body.dark-mode h1, body.dark-mode .header p { color: #f0f0f0; }
body.dark-mode .sensor-card, body.dark-mode .metric-card { background: linear-gradient(145deg, #2a2a35, #22222b); color: #e0e0e0; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
body.dark-mode .sensor-value, body.dark-mode .metric-value, body.dark-mode .dropdown-group label, body.dark-mode .last-update, body.dark-mode .alert-title { color: #f0f0f0; }
body.dark-mode .dropdown-group select { background: #333; color: #fff; border-color: #555; }
body.dark-mode .alert.success { background: rgba(40, 167, 69, 0.2); border-left-color: #28a745; }
body.dark-mode .alert.warning { background: rgba(255, 193, 7, 0.2); border-left-color: #ffc107; }
body.dark-mode .alert.danger { background: rgba(220, 53, 69, 0.2); border-left-color: #dc3545; }
body.dark-mode .metric-label, body.dark-mode .sensor-label, body.dark-mode .alert-time { color: #aaa; }
''')

with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

# Add Dark mode toggle in DOMContentLoaded
js_content = js_content.replace(
'''        document.addEventListener('DOMContentLoaded', function () {
            initAudio();
            initCharts();
            loadInitialData();
            startRealTimeUpdates();
            updateLastUpdateTime();
        });''',
'''        document.addEventListener('DOMContentLoaded', function () {
            initAudio();
            initCharts();
            loadInitialData();
            startRealTimeUpdates();
            updateLastUpdateTime();
            
            const btn = document.getElementById('darkModeToggle');
            if (btn) {
                btn.addEventListener('click', function() {
                    document.body.classList.toggle('dark-mode');
                    this.textContent = document.body.classList.contains('dark-mode') ? '☀️ Light Mode' : '🌙 Dark Mode';
                });
            }
        });'''
)

# Update JS to use backend predict correctly
new_update_charts = '''        async function updateCharts() {
            if (!simulationRunning) return;

            const now = new Date();
            const timeString = now.toLocaleTimeString().slice(0, -3);

            let newUsage;
            switch(currentChartType) {
                case 'water_flow': newUsage = sensorData.flowRate; break;
                case 'water_level': newUsage = sensorData.waterLevel; break;
                case 'temperature': newUsage = sensorData.waterTemperature; break;
                case 'soil_moisture': newUsage = sensorData.soilMoisture; break;
            }

            timeLabels.push(timeString);
            usageData.push(Math.max(0, Math.round(newUsage)));

            if (timeLabels.length > maxDataPoints) {
                timeLabels.shift();
                usageData.shift();
            }

            // Fetch predictions from backend
            try {
                const response = await fetch('/api/sensors/predict');
                if (response.ok) {
                    const data = await response.json();
                    let apiPredictions = [];
                    if (currentChartType === 'water_flow') apiPredictions = data.flow_rate;
                    else if (currentChartType === 'water_level') apiPredictions = data.water_level;
                    else if (currentChartType === 'temperature') apiPredictions = data.water_temperature;
                    else if (currentChartType === 'soil_moisture') apiPredictions = data.soil_moisture;
                    
                    if (apiPredictions && apiPredictions.length > 0) {
                        let alignedPreds = apiPredictions.slice(0, usageData.length);
                        // Pad array to match usageData
                        while (alignedPreds.length < usageData.length) { alignedPreds.unshift(null); }
                        predictionData = alignedPreds;
                    }
                }
            } catch (e) {
                console.error("Failed to fetch predictions", e);
            }

            usageChart.data.labels = [...timeLabels];
            usageChart.data.datasets[0].data = [...usageData];
            usageChart.update('active');

            predictionChart.data.labels = [...timeLabels];
            predictionChart.data.datasets[0].data = [...usageData];
            predictionChart.data.datasets[1].data = predictionData && predictionData.length > 0 ? [...predictionData] : usageData.map(val => val * 0.9);
            predictionChart.update('active');
        }'''

# Find the old updateCharts function block using regex and replace
js_content = re.sub(r'        function updateCharts\(\) \{.*?(?=        function updateChartData\(\))', new_update_charts + '\n\n', js_content, flags=re.DOTALL)

# Same for updateChartData to make it async and fetch predictions
new_update_chart_data = '''        async function updateChartData() {
            const selector = document.getElementById('chartSelector');
            currentChartType = selector.value;

            const chartConfigs = {
                water_flow: { title: 'Water Flow Rate', unit: 'L/min', color: '#43e97b', getData: () => sensorData.flowRate },
                water_level: { title: 'Water Level', unit: '%', color: '#4facfe', getData: () => sensorData.waterLevel },
                temperature: { title: 'Water Temperature', unit: '°C', color: '#ff6b6b', getData: () => sensorData.waterTemperature },
                soil_moisture: { title: 'Soil Moisture', unit: '%', color: '#fa709a', getData: () => sensorData.soilMoisture }
            };

            const config = chartConfigs[currentChartType];

            usageChart.options.plugins.title.text = `Real-Time ${config.title}`;
            predictionChart.options.plugins.title.text = `${config.title}: Actual vs Predicted`;

            usageChart.data.datasets[0].borderColor = config.color;
            usageChart.data.datasets[0].backgroundColor = config.color + '33';
            usageChart.data.datasets[0].label = `Current ${config.title}`;

            usageChart.options.scales.y.title.text = config.unit;
            predictionChart.options.scales.y.title.text = config.unit;

            const currentValue = config.getData();
            const newHistoricalData = [];
            for (let i = 0; i < maxDataPoints; i++) {
                const variation = (Math.random() - 0.5) * (currentValue * 0.2);
                newHistoricalData.push(Math.round(Math.max(0, currentValue + variation)));
            }

            usageData = [...newHistoricalData];
            
            // Fetch predictions from backend
            predictionData = [];
            try {
                const response = await fetch('/api/sensors/predict');
                if (response.ok) {
                    const data = await response.json();
                    let apiPredictions = [];
                    if (currentChartType === 'water_flow') apiPredictions = data.flow_rate;
                    else if (currentChartType === 'water_level') apiPredictions = data.water_level;
                    else if (currentChartType === 'temperature') apiPredictions = data.water_temperature;
                    else if (currentChartType === 'soil_moisture') apiPredictions = data.soil_moisture;
                    
                    if (apiPredictions && apiPredictions.length > 0) {
                        let alignedPreds = apiPredictions.slice(0, usageData.length);
                        // Pad array to match usageData
                        while (alignedPreds.length < usageData.length) { alignedPreds.unshift(null); }
                        predictionData = alignedPreds;
                    }
                }
            } catch (e) {}

            usageChart.data.datasets[0].data = [...usageData];
            predictionChart.data.datasets[0].data = [...usageData];
            predictionChart.data.datasets[1].data = predictionData.length > 0 ? [...predictionData] : usageData.map(val => val * 0.9);

            usageChart.update();
            predictionChart.update();

            addAlert('success', '📊', 'Chart Updated', `Now displaying ${config.title} data`);
        }'''

js_content = re.sub(r'        function updateChartData\(\) \{.*?(?=        function updateTimeRange\(\))', new_update_chart_data + '\n\n', js_content, flags=re.DOTALL)

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)
print("Updated JS successfully!")
