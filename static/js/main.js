// ===== AquaIntel — Smart Water Management System =====
// Complete UI Engine with Three.js 3D Background, Particles, and all 10 patent features

// ─── GLOBALS ───
let usageChart, predictionChart;
let simulationRunning = true;
let sensorData = {
  waterLevel: 85,
  flowRate: 24.5,
  soilMoisture: 67,
  waterTemperature: 22.5,
};
const sensorLimits = {
  waterLevel: { min: 20, max: 95 },
  flowRate: { min: 0, max: 50 },
  soilMoisture: { min: 30, max: 90 },
  waterTemperature: { min: 10, max: 35 },
};
let usageData = [],
  predictionData = [],
  timeLabels = [];
let maxDataPoints = 20;
let currentChartType = "water_flow";
let audioContext,
  isAlarmActive = false;
let alertCount = 0;

// ─── INIT ───
document.addEventListener("DOMContentLoaded", () => {
  init3DBackground();
  spawnParticles();
  initNavigation();
  initClock();
  initAudio();
  initCharts();
  initCardInteractions();
  initButtonEffects();
  loadInitialData();
  startRealTimeUpdates();
});

// ═══════════════════════════════════════════════════════════
// THREE.JS 3D ANIMATED BACKGROUND
// ═══════════════════════════════════════════════════════════
function init3DBackground() {
  const canvas = document.getElementById("bgCanvas");
  if (!canvas || typeof THREE === "undefined") return;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(
    75,
    window.innerWidth / window.innerHeight,
    0.1,
    1000,
  );
  const renderer = new THREE.WebGLRenderer({
    canvas,
    alpha: true,
    antialias: true,
  });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  // Animated water molecule cluster
  const molecules = [];
  const moleculeMat = new THREE.MeshPhongMaterial({
    color: 0x00d4ff,
    transparent: true,
    opacity: 0.08,
    shininess: 100,
    emissive: 0x003366,
    emissiveIntensity: 0.3,
  });

  for (let i = 0; i < 40; i++) {
    const geo = new THREE.IcosahedronGeometry(Math.random() * 1.5 + 0.3, 1);
    const mesh = new THREE.Mesh(geo, moleculeMat.clone());
    mesh.position.set(
      (Math.random() - 0.5) * 30,
      (Math.random() - 0.5) * 20,
      (Math.random() - 0.5) * 20 - 10,
    );
    mesh.userData = {
      speedX: (Math.random() - 0.5) * 0.005,
      speedY: (Math.random() - 0.5) * 0.005,
      speedZ: (Math.random() - 0.5) * 0.003,
      rotSpeed: Math.random() * 0.01 + 0.002,
    };
    scene.add(mesh);
    molecules.push(mesh);
  }

  // Connection lines between nearby molecules
  const lineMat = new THREE.LineBasicMaterial({
    color: 0x00d4ff,
    transparent: true,
    opacity: 0.04,
  });
  const connections = [];
  for (let i = 0; i < 20; i++) {
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(6);
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const line = new THREE.Line(geo, lineMat);
    scene.add(line);
    connections.push(line);
  }

  // Lighting
  const ambient = new THREE.AmbientLight(0x334466, 0.6);
  scene.add(ambient);
  const point = new THREE.PointLight(0x00d4ff, 1, 50);
  point.position.set(5, 5, 5);
  scene.add(point);
  const point2 = new THREE.PointLight(0xa78bfa, 0.5, 50);
  point2.position.set(-5, -5, 5);
  scene.add(point2);

  camera.position.z = 15;

  let mouseX = 0,
    mouseY = 0;
  document.addEventListener("mousemove", (e) => {
    mouseX = (e.clientX / window.innerWidth - 0.5) * 2;
    mouseY = (e.clientY / window.innerHeight - 0.5) * 2;
  });

  function animate() {
    requestAnimationFrame(animate);

    molecules.forEach((m) => {
      m.rotation.x += m.userData.rotSpeed;
      m.rotation.y += m.userData.rotSpeed * 0.7;
      m.position.x += m.userData.speedX;
      m.position.y += m.userData.speedY;
      m.position.z += m.userData.speedZ;

      // Wrap around
      if (m.position.x > 18) m.position.x = -18;
      if (m.position.x < -18) m.position.x = 18;
      if (m.position.y > 12) m.position.y = -12;
      if (m.position.y < -12) m.position.y = 12;
    });

    // Update connections
    let ci = 0;
    for (let i = 0; i < molecules.length && ci < connections.length; i++) {
      for (
        let j = i + 1;
        j < molecules.length && ci < connections.length;
        j++
      ) {
        const d = molecules[i].position.distanceTo(molecules[j].position);
        if (d < 6) {
          const pos = connections[ci].geometry.attributes.position.array;
          pos[0] = molecules[i].position.x;
          pos[1] = molecules[i].position.y;
          pos[2] = molecules[i].position.z;
          pos[3] = molecules[j].position.x;
          pos[4] = molecules[j].position.y;
          pos[5] = molecules[j].position.z;
          connections[ci].geometry.attributes.position.needsUpdate = true;
          connections[ci].material.opacity = 0.04 * (1 - d / 6);
          ci++;
        }
      }
    }

    // Mouse parallax
    camera.position.x += (mouseX * 1.5 - camera.position.x) * 0.02;
    camera.position.y += (-mouseY * 1.0 - camera.position.y) * 0.02;
    camera.lookAt(0, 0, 0);

    renderer.render(scene, camera);
  }
  animate();

  window.addEventListener("resize", () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });
}

// ═══════════════════════════════════════════════════════════
// FLOATING PARTICLES
// ═══════════════════════════════════════════════════════════
function spawnParticles() {
  const container = document.getElementById("particles");
  if (!container) return;

  for (let i = 0; i < 25; i++) {
    const p = document.createElement("div");
    p.className = "particle";
    const size = Math.random() * 6 + 2;
    p.style.width = size + "px";
    p.style.height = size + "px";
    p.style.left = Math.random() * 100 + "%";
    p.style.animationDuration = Math.random() * 15 + 10 + "s";
    p.style.animationDelay = Math.random() * 10 + "s";
    container.appendChild(p);
  }
}

// ═══════════════════════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════════════════════
function initNavigation() {
  const navItems = document.querySelectorAll(".nav-item");
  const sections = document.querySelectorAll(".content-section");
  const pageTitle = document.getElementById("pageTitle");
  const sidebar = document.getElementById("sidebar");
  const menuToggle = document.getElementById("menuToggle");

  const titles = {
    overview: "Dashboard Overview",
    analytics: "Real-time Analytics",
    intelligence: "AI Intelligence Engine",
    infrastructure: "System Infrastructure",
    alerts: "Alerts & Notifications",
  };

  navItems.forEach((item) => {
    item.addEventListener("click", () => {
      const target = item.dataset.section;
      navItems.forEach((n) => n.classList.remove("active"));
      item.classList.add("active");
      sections.forEach((s) => s.classList.remove("active"));
      const sec = document.getElementById("section-" + target);
      if (sec) sec.classList.add("active");
      if (pageTitle) pageTitle.textContent = titles[target] || "Dashboard";
      if (sidebar) sidebar.classList.remove("open");
    });
  });

  if (menuToggle && sidebar) {
    menuToggle.addEventListener("click", () =>
      sidebar.classList.toggle("open"),
    );
  }
}

// ═══════════════════════════════════════════════════════════
// LIVE CLOCK
// ═══════════════════════════════════════════════════════════
function initClock() {
  const el = document.getElementById("liveClock");
  if (!el) return;
  const update = () => {
    el.textContent = new Date().toLocaleTimeString();
  };
  update();
  setInterval(update, 1000);
}

// ═══════════════════════════════════════════════════════════
// AUDIO / ALARMS
// ═══════════════════════════════════════════════════════════
function initAudio() {
  try {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  } catch (e) {}
}

function playAlarmSound() {
  if (!audioContext || isAlarmActive) return;
  isAlarmActive = true;
  const osc = audioContext.createOscillator();
  const gain = audioContext.createGain();
  osc.connect(gain);
  gain.connect(audioContext.destination);
  osc.frequency.setValueAtTime(800, audioContext.currentTime);
  osc.frequency.setValueAtTime(400, audioContext.currentTime + 0.2);
  osc.frequency.setValueAtTime(800, audioContext.currentTime + 0.4);
  gain.gain.setValueAtTime(0.3, audioContext.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.6);
  osc.start();
  osc.stop(audioContext.currentTime + 0.6);
  setTimeout(() => {
    isAlarmActive = false;
  }, 1000);
}

function showAlarm(message) {
  const el = document.getElementById("alarmNotification");
  const msg = document.getElementById("alarmMessage");
  if (msg) msg.textContent = message;
  if (el) {
    el.style.display = "flex";
    el.classList.add("show");
  }
  playAlarmSound();
  setTimeout(() => closeAlarm(), 8000);
}

function closeAlarm() {
  const el = document.getElementById("alarmNotification");
  if (el) {
    el.style.display = "none";
    el.classList.remove("show");
  }
}

function testAlarm() {
  showAlarm("Test alarm — System functioning normally");
  addAlert("warn", "Alarm Test", "Test alarm triggered successfully");
}

function checkSensorLimits() {
  const v = [];
  if (sensorData.waterLevel < sensorLimits.waterLevel.min)
    v.push("Water Level Critical: " + sensorData.waterLevel + "%");
  else if (sensorData.waterLevel > sensorLimits.waterLevel.max)
    v.push("Water Level High: " + sensorData.waterLevel + "%");
  if (sensorData.flowRate > sensorLimits.flowRate.max)
    v.push("Flow Rate High: " + sensorData.flowRate + " L/min");
  if (sensorData.soilMoisture < sensorLimits.soilMoisture.min)
    v.push("Soil Moisture Low: " + sensorData.soilMoisture + "%");
  else if (sensorData.soilMoisture > sensorLimits.soilMoisture.max)
    v.push("Soil Moisture High: " + sensorData.soilMoisture + "%");
  if (sensorData.waterTemperature < sensorLimits.waterTemperature.min)
    v.push("Temp Low: " + sensorData.waterTemperature + "°C");
  else if (sensorData.waterTemperature > sensorLimits.waterTemperature.max)
    v.push("Temp High: " + sensorData.waterTemperature + "°C");
  v.forEach((msg) => {
    showAlarm(msg);
    addAlert("danger", "CRITICAL", msg);
  });
}

// ═══════════════════════════════════════════════════════════
// RING PROGRESS (SVG circle)
// ═══════════════════════════════════════════════════════════
function updateRing(id, value, maxValue) {
  const el = document.getElementById(id);
  if (!el) return;
  const circumference = 2 * Math.PI * 52; // r=52
  const pct = Math.min(Math.max(value / maxValue, 0), 1);
  el.style.strokeDashoffset = circumference * (1 - pct);
}

function updateSensorUI() {
  const setText = (id, v) => {
    const e = document.getElementById(id);
    if (e) e.textContent = v;
  };

  setText("waterLevel", Math.round(sensorData.waterLevel) + "%");
  setText("waterLevelText", Math.round(sensorData.waterLevel) + "%");
  setText("flowRate", sensorData.flowRate.toFixed(1) + " L/min");
  setText("flowRateText", sensorData.flowRate.toFixed(1));
  setText("soilMoisture", Math.round(sensorData.soilMoisture) + "%");
  setText("soilMoistureText", Math.round(sensorData.soilMoisture) + "%");
  setText("waterTemperature", sensorData.waterTemperature.toFixed(1) + "°C");
  setText("temperatureText", sensorData.waterTemperature.toFixed(1) + "°C");

  updateRing("ringWaterLevel", sensorData.waterLevel, 100);
  updateRing("ringFlowRate", sensorData.flowRate, sensorLimits.flowRate.max);
  updateRing("ringSoilMoisture", sensorData.soilMoisture, 100);
  updateRing(
    "ringTemperature",
    sensorData.waterTemperature,
    sensorLimits.waterTemperature.max,
  );

  checkSensorLimits();
}

// ═══════════════════════════════════════════════════════════
// CHARTS (Chart.js)
// ═══════════════════════════════════════════════════════════
function initCharts() {
  const now = new Date();
  for (let i = 0; i < 10; i++) {
    const t = new Date(now.getTime() - (9 - i) * 5000);
    timeLabels.push(t.toLocaleTimeString().slice(0, -3));
    usageData.push(Math.round(150 + Math.random() * 100));
    predictionData.push(Math.round(140 + Math.random() * 120));
  }

  // Global Chart.js dark config
  Chart.defaults.color = "#94a3b8";
  Chart.defaults.borderColor = "rgba(100,160,255,0.08)";
  Chart.defaults.font.family = "'Inter', sans-serif";

  const uCtx = document.getElementById("usageChart");
  if (uCtx) {
    usageChart = new Chart(uCtx.getContext("2d"), {
      type: "line",
      data: {
        labels: [...timeLabels],
        datasets: [
          {
            label: "Current Usage",
            data: [...usageData],
            borderColor: "#00d4ff",
            backgroundColor: "rgba(0,212,255,0.08)",
            tension: 0.4,
            fill: true,
            pointRadius: 3,
            pointHoverRadius: 6,
            pointBackgroundColor: "#00d4ff",
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 750, easing: "easeInOutQuart" },
        plugins: {
          title: {
            display: true,
            text: "Real-Time Water Usage",
            font: { size: 13, weight: "600" },
            color: "#e2e8f0",
          },
          legend: {
            display: true,
            position: "top",
            labels: { usePointStyle: true, pointStyle: "circle", padding: 16 },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: "rgba(100,160,255,0.06)" },
            ticks: { font: { size: 11 } },
          },
          x: {
            grid: { color: "rgba(100,160,255,0.04)" },
            ticks: { font: { size: 11 } },
          },
        },
      },
    });
  }

  const pCtx = document.getElementById("predictionChart");
  if (pCtx) {
    predictionChart = new Chart(pCtx.getContext("2d"), {
      type: "line",
      data: {
        labels: [...timeLabels],
        datasets: [
          {
            label: "Actual",
            data: usageData.map((v) => Math.round(v * 0.25)),
            borderColor: "#00ffa3",
            backgroundColor: "rgba(0,255,163,0.05)",
            tension: 0.4,
            pointRadius: 3,
            borderWidth: 2,
            pointBackgroundColor: "#00ffa3",
          },
          {
            label: "Predicted",
            data: generatePredictions(usageData),
            borderColor: "#ffb347",
            backgroundColor: "rgba(255,179,71,0.05)",
            borderDash: [5, 5],
            tension: 0.4,
            pointRadius: 2,
            borderWidth: 2,
            pointBackgroundColor: "#ffb347",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 750 },
        plugins: {
          title: {
            display: true,
            text: "Actual vs Predicted",
            font: { size: 13, weight: "600" },
            color: "#e2e8f0",
          },
          legend: {
            display: true,
            position: "top",
            labels: { usePointStyle: true, pointStyle: "circle", padding: 16 },
          },
        },
        scales: {
          y: { beginAtZero: true, grid: { color: "rgba(100,160,255,0.06)" } },
          x: { grid: { color: "rgba(100,160,255,0.04)" } },
        },
      },
    });
  }
}

function generatePredictions(data) {
  const preds = [];
  for (let i = 0; i < data.length; i++) {
    if (i < 3) {
      preds.push(Math.round(data[i] * 0.22 + (Math.random() - 0.5) * 5));
    } else {
      const avg = data.slice(i - 3, i).reduce((a, b) => a + b, 0) / 3;
      const trend = (data[i - 1] - data[i - 2]) * 0.5;
      const seasonal = 1 + Math.sin(i * 0.3) * 0.1;
      preds.push(Math.max(0, Math.round((avg * 0.22 + trend) * seasonal)));
    }
  }
  return preds;
}

// ═══════════════════════════════════════════════════════════
// DATA FETCHING
// ═══════════════════════════════════════════════════════════
async function fetchSensorData() {
  try {
    const r = await fetch("/api/sensors/current");
    if (r.ok) {
      const d = await r.json();
      sensorData.waterLevel = d.water_level;
      sensorData.flowRate = d.flow_rate;
      sensorData.soilMoisture = d.soil_moisture;
      sensorData.waterTemperature = d.water_temperature;
      setConnectionStatus(true);
    }
  } catch (e) {
    setConnectionStatus(false);
  }

  try {
    const r = await fetch("/api/metrics/current");
    if (r.ok) {
      const m = await r.json();
      setEl("avgUsageRate", sensorData.flowRate.toFixed(1) + " L/min");
      setEl("peakFlowRate", (sensorData.flowRate * 1.5).toFixed(1) + " L/min");
      setEl(
        "totalVolumeToday",
        Math.round(sensorData.flowRate * 60 * 24).toLocaleString() + " L",
      );
      setEl("predictionAccuracy", m.alert_accuracy.toFixed(1) + "%");
      setEl("avgWaterTemp", sensorData.waterTemperature.toFixed(1) + "°C");
      setEl("systemEfficiency", (100 - m.cpu_utilization / 2).toFixed(1) + "%");
    }
  } catch (e) {}

  try {
    const r = await fetch("/api/alerts");
    if (r.ok) {
      const alerts = await r.json();
      const panel = document.getElementById("alertsPanel");
      if (panel) {
        panel.innerHTML = "";
        alerts.forEach((a) => {
          const div = document.createElement("div");
          div.className =
            "feed-item " +
            (a.type === "danger"
              ? "danger"
              : a.type === "warning"
                ? "warn"
                : "ok");
          div.innerHTML =
            '<span class="fi-dot"></span><div class="fi-content"><div class="fi-title">' +
            a.title +
            '</div><div class="fi-time">' +
            new Date(a.timestamp).toLocaleTimeString() +
            "</div></div>";
          panel.appendChild(div);
        });
        alertCount = alerts.length;
        updateAlertBadge();
      }
    }
  } catch (e) {}
}

function setConnectionStatus(online) {
  const dot = document.querySelector(".conn-dot");
  const span = document.querySelector(".connection-status span");
  if (dot) dot.style.background = online ? "#00ffa3" : "#ff4757";
  if (span) span.textContent = online ? "Connected" : "Offline";
}

function setEl(id, val) {
  const e = document.getElementById(id);
  if (e) e.textContent = val;
}

function updateAlertBadge() {
  const b = document.getElementById("alertBadge");
  if (b) b.textContent = alertCount;
}

// ═══════════════════════════════════════════════════════════
// REAL-TIME LOOP
// ═══════════════════════════════════════════════════════════
function loadInitialData() {
  updateSensorUI();
  addAlert("ok", "System Initialized", "All sensors connected");
}

function startRealTimeUpdates() {
  setInterval(async () => {
    await fetchSensorData();
    updateSensorUI();
    await updateCharts();
  }, 5000);
}

async function updateCharts() {
  const now = new Date();
  const ts = now.toLocaleTimeString().slice(0, -3);
  let val;
  switch (currentChartType) {
    case "water_flow":
      val = sensorData.flowRate;
      break;
    case "water_level":
      val = sensorData.waterLevel;
      break;
    case "temperature":
      val = sensorData.waterTemperature;
      break;
    case "soil_moisture":
      val = sensorData.soilMoisture;
      break;
  }
  timeLabels.push(ts);
  usageData.push(Math.max(0, Math.round(val)));
  if (timeLabels.length > maxDataPoints) {
    timeLabels.shift();
    usageData.shift();
  }

  try {
    const r = await fetch("/api/sensors/predict");
    if (r.ok) {
      const d = await r.json();
      let p = [];
      if (currentChartType === "water_flow") p = d.flow_rate;
      else if (currentChartType === "water_level") p = d.water_level;
      else if (currentChartType === "temperature") p = d.water_temperature;
      else if (currentChartType === "soil_moisture") p = d.soil_moisture;
      if (p && p.length > 0) {
        let a = p.slice(0, usageData.length);
        while (a.length < usageData.length) a.unshift(null);
        predictionData = a;
      }
    }
  } catch (e) {}

  if (usageChart) {
    usageChart.data.labels = [...timeLabels];
    usageChart.data.datasets[0].data = [...usageData];
    usageChart.update("active");
  }
  if (predictionChart) {
    predictionChart.data.labels = [...timeLabels];
    predictionChart.data.datasets[0].data = [...usageData];
    predictionChart.data.datasets[1].data =
      predictionData.length > 0
        ? [...predictionData]
        : usageData.map((v) => v * 0.9);
    predictionChart.update("active");
  }
}

async function updateChartData() {
  const sel = document.getElementById("chartSelector");
  if (sel) currentChartType = sel.value;

  const configs = {
    water_flow: { title: "Water Flow Rate", color: "#00ffa3" },
    water_level: { title: "Water Level", color: "#00d4ff" },
    temperature: { title: "Temperature", color: "#ff6b6b" },
    soil_moisture: { title: "Soil Moisture", color: "#ff6bca" },
  };
  const c = configs[currentChartType];
  if (usageChart) {
    usageChart.options.plugins.title.text = "Real-Time " + c.title;
    usageChart.data.datasets[0].borderColor = c.color;
    usageChart.data.datasets[0].backgroundColor = c.color + "14";
    usageChart.data.datasets[0].pointBackgroundColor = c.color;
    usageChart.update();
  }
  if (predictionChart) {
    predictionChart.options.plugins.title.text =
      c.title + ": Actual vs Predicted";
    predictionChart.update();
  }
}

function updateTimeRange() {
  const tr = document.getElementById("timeRange");
  if (!tr) return;
  const ranges = {
    "1h": { pts: 12, int: 5 },
    "6h": { pts: 18, int: 20 },
    "24h": { pts: 24, int: 60 },
    "7d": { pts: 14, int: 720 },
  };
  const r = ranges[tr.value];
  maxDataPoints = r.pts;
  timeLabels = [];
  const now = new Date();
  for (let i = r.pts - 1; i >= 0; i--) {
    const t = new Date(now.getTime() - i * r.int * 60000);
    timeLabels.push(
      tr.value === "7d"
        ? t.toLocaleDateString().slice(0, -5)
        : t.toLocaleTimeString().slice(0, -3),
    );
  }
  updateChartData();
}

// ═══════════════════════════════════════════════════════════
// ALERTS
// ═══════════════════════════════════════════════════════════
function addAlert(type, title, message) {
  const panel = document.getElementById("alertsPanel");
  if (!panel) return;
  const div = document.createElement("div");
  div.className = "feed-item " + type;
  div.innerHTML =
    '<span class="fi-dot"></span><div class="fi-content"><div class="fi-title">' +
    title +
    '</div><div class="fi-time">' +
    new Date().toLocaleTimeString() +
    " — " +
    message +
    "</div></div>";
  panel.insertBefore(div, panel.firstChild);
  while (panel.children.length > 15) panel.removeChild(panel.lastChild);
  alertCount++;
  updateAlertBadge();
}

function clearAlerts() {
  const panel = document.getElementById("alertsPanel");
  if (panel) panel.innerHTML = "";
  alertCount = 0;
  updateAlertBadge();
  addAlert("ok", "Alerts Cleared", "History cleared");
}

// ═══════════════════════════════════════════════════════════
// CONTROLS
// ═══════════════════════════════════════════════════════════
async function refreshData() {
  addAlert("ok", "Refreshing", "Loading latest readings...");
  await fetchSensorData();
  updateSensorUI();
  addAlert("ok", "Data Refreshed", "All sensors updated");
}

async function exportData() {
  const d = {
    timestamp: new Date().toISOString(),
    sensors: sensorData,
    limits: sensorLimits,
    chartData: { timeLabels, usageData, predictionData },
  };
  const blob = new Blob([JSON.stringify(d, null, 2)], {
    type: "application/json",
  });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "aquaintel_" + new Date().toISOString().slice(0, 10) + ".json";
  a.click();
  URL.revokeObjectURL(a.href);
  addAlert("ok", "Data Exported", "Download started");
}

// ═══════════════════════════════════════════════════════════
// CARD INTERACTIONS — click to navigate
// ═══════════════════════════════════════════════════════════
function navigateToSection(sectionName) {
  const navItems = document.querySelectorAll(".nav-item");
  const sections = document.querySelectorAll(".content-section");
  const pageTitle = document.getElementById("pageTitle");
  const titles = {
    overview: "Dashboard Overview",
    analytics: "Real-time Analytics",
    intelligence: "AI Intelligence Engine",
    infrastructure: "System Infrastructure",
    alerts: "Alerts & Notifications",
  };

  navItems.forEach((n) => {
    n.classList.toggle("active", n.dataset.section === sectionName);
  });
  sections.forEach((s) => s.classList.remove("active"));
  const sec = document.getElementById("section-" + sectionName);
  if (sec) sec.classList.add("active");
  if (pageTitle) pageTitle.textContent = titles[sectionName] || "Dashboard";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function initCardInteractions() {
  // Sensor hero cards → Analytics
  document.querySelectorAll(".sensor-hero-card").forEach((card) => {
    card.title = "Click to view analytics";
    card.addEventListener("click", () => {
      const typeMap = {
        water: "water_level",
        flow: "water_flow",
        soil: "soil_moisture",
        temp: "temperature",
      };
      const type = card.dataset.type;
      const sel = document.getElementById("chartSelector");
      if (sel && typeMap[type]) {
        sel.value = typeMap[type];
        updateChartData();
      }
      navigateToSection("analytics");
    });
  });

  // Quick-status cards → Intelligence
  document.querySelectorAll(".qs-card").forEach((card) => {
    card.title = "Click to view details in AI Engine";
    card.addEventListener("click", () => navigateToSection("intelligence"));
  });

  // Metric pills → show tooltip flash
  document.querySelectorAll(".metric-pill").forEach((pill) => {
    pill.addEventListener("mouseenter", () => {
      pill.style.borderColor = "var(--accent-blue)";
    });
    pill.addEventListener("mouseleave", () => {
      pill.style.borderColor = "";
    });
  });
}

// ═══════════════════════════════════════════════════════════
// BUTTON RIPPLE EFFECT
// ═══════════════════════════════════════════════════════════
function initButtonEffects() {
  document.querySelectorAll(".ctrl-btn").forEach((btn) => {
    btn.addEventListener("mousemove", (e) => {
      const rect = btn.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      btn.style.setProperty("--x", x + "%");
      btn.style.setProperty("--y", y + "%");
    });

    btn.addEventListener("click", (e) => {
      const ripple = document.createElement("span");
      ripple.style.cssText = `
                position:absolute;
                border-radius:50%;
                background:rgba(255,255,255,0.15);
                width:10px;height:10px;
                left:${e.offsetX}px;top:${e.offsetY}px;
                transform:translate(-50%,-50%) scale(0);
                animation:ripple 0.6s ease-out forwards;
                pointer-events:none;
            `;
      btn.appendChild(ripple);
      setTimeout(() => ripple.remove(), 700);
    });
  });

  // Add ripple keyframes if not exists
  if (!document.getElementById("rippleStyle")) {
    const style = document.createElement("style");
    style.id = "rippleStyle";
    style.textContent =
      "@keyframes ripple{to{transform:translate(-50%,-50%) scale(30);opacity:0;}}";
    document.head.appendChild(style);
  }
}

// ═══════════════════════════════════════════════════════════
// INTELLIGENCE DASHBOARD (All 10 Patent Features)
// ═══════════════════════════════════════════════════════════
async function fetchIntelligenceDashboard() {
  try {
    const r = await fetch("/api/intelligence/dashboard");
    if (!r.ok) return;
    const data = await r.json();

    // --- Leak Detection ---
    if (data.leak_detection) {
      const ls = document.getElementById("leakStatus");
      const ld = document.getElementById("leakDetail");
      const lc = document.getElementById("leakCard");
      if (data.leak_detection.active_leaks > 0) {
        if (ls) {
          ls.textContent = data.leak_detection.active_leaks + " Leak(s)!";
          ls.style.color = "#ff4757";
        }
        const leak = data.leak_detection.leaks[0];
        if (ld)
          ld.textContent =
            leak.leak_type.replace(/_/g, " ") +
            " — " +
            (leak.confidence * 100).toFixed(0) +
            "% conf";
        if (lc) {
          const ind = lc.querySelector(".qs-indicator");
          if (ind) {
            ind.className = "qs-indicator danger";
          }
        }
      } else {
        if (ls) {
          ls.textContent = "No Leaks";
          ls.style.color = "#00ffa3";
        }
        if (ld) ld.textContent = "Multi-sensor fusion active";
        if (lc) {
          const ind = lc.querySelector(".qs-indicator");
          if (ind) {
            ind.className = "qs-indicator good";
          }
        }
      }
    }

    // --- Weather & Irrigation ---
    if (
      data.weather_irrigation &&
      data.weather_irrigation.weather &&
      !data.weather_irrigation.error
    ) {
      const wx = data.weather_irrigation.weather;
      const rec = data.weather_irrigation.recommendation;
      setEl("irrigationPct", (rec.irrigation_recommendation || 100) + "%");
      setEl("weatherDesc", wx.description || "N/A");
      setEl(
        "waterSaved",
        (data.weather_irrigation.savings.total_water_saved_liters || 0).toFixed(
          0,
        ) + "L",
      );
      setEl("wxTemp", wx.temperature + "°C");
      setEl("wxHumidity", wx.humidity + "%");
      setEl("wxRain", (wx.rain_probability * 100).toFixed(0) + "%");
      setEl("wxET", rec.evapotranspiration + "mm/day");
      setEl("wxRecommendation", rec.reasoning || "Analyzing...");
    }

    // --- Sensor Health ---
    if (data.sensor_health) {
      const sh = data.sensor_health;
      setEl(
        "sensorHealthStatus",
        sh.overall_status === "healthy" ? "Healthy" : "Issues Found",
      );
      const hEl = document.getElementById("sensorHealthStatus");
      if (hEl)
        hEl.style.color =
          sh.overall_status === "healthy" ? "#00ffa3" : "#ffb347";
      setEl(
        "healthDetail",
        sh.overall_status === "healthy"
          ? "All sensors cross-validated OK"
          : sh.total_issues_last_hour + " issue(s)",
      );

      const healthCard = document.getElementById("healthCard");
      if (healthCard) {
        const ind = healthCard.querySelector(".qs-indicator");
        if (ind)
          ind.className =
            "qs-indicator " +
            (sh.overall_status === "healthy" ? "good" : "warn");
      }

      const sMap = {
        water_level: "healthWaterLevel",
        flow_rate: "healthFlowRate",
        soil_moisture: "healthSoilMoisture",
        water_temperature: "healthTemperature",
      };
      for (const [s, eId] of Object.entries(sMap)) {
        const el = document.getElementById(eId);
        const sd = sh.sensors[s];
        if (el && sd) {
          if (sd.status === "healthy") {
            el.textContent = "✅ Healthy";
            el.style.color = "#00ffa3";
          } else if (sd.status === "degraded") {
            el.textContent = "⚠️ Degraded";
            el.style.color = "#ffb347";
          } else {
            el.textContent = "❌ Faulty";
            el.style.color = "#ff4757";
          }
        }
      }
    }

    // --- Anomaly Detection ---
    if (data.anomaly_detection) {
      setEl("anomalyAnalyzed", data.anomaly_detection.total_analyzed || 0);
      setEl("anomalyFound", data.anomaly_detection.anomalies_found || 0);
      setEl("anomalyRate", (data.anomaly_detection.anomaly_rate || 0) + "%");
      const panel = document.getElementById("anomalyPanel");
      if (panel) {
        panel.innerHTML = "";
        if (
          data.anomaly_detection.recent &&
          data.anomaly_detection.recent.length > 0
        ) {
          data.anomaly_detection.recent.forEach((a) => {
            const div = document.createElement("div");
            div.className = "feed-item danger";
            div.innerHTML =
              '<span class="fi-dot"></span><span>🧠 ' +
              a.description.substring(0, 80) +
              " (Score: " +
              a.anomaly_score +
              ")</span>";
            panel.appendChild(div);
          });
        } else {
          panel.innerHTML =
            '<div class="feed-item ok"><span class="fi-dot"></span><span>No anomalies — all patterns normal</span></div>';
        }
      }
    }

    // --- Valve Control ---
    if (data.valve_control) {
      const vc = data.valve_control;
      const vs = vc.valve_states || {};
      const fmtValve = (s) => (s === "open" ? "🟢 Open" : "🔴 Closed");
      setEl("valveZoneA", fmtValve(vs.zone_A || "open"));
      setEl("valveZoneB", fmtValve(vs.zone_B || "open"));
      setEl("valveMainSupply", fmtValve(vs.main_supply || "open"));

      // Update zone card styling
      document.querySelectorAll(".valve-zone").forEach((el, i) => {
        const states = [vs.zone_A, vs.zone_B, vs.main_supply];
        el.classList.toggle("closed", states[i] === "closed");
        el.classList.toggle("open", states[i] !== "closed");
      });

      setEl(
        "valveWaterSaved",
        (vc.water_saved_by_valves || 0).toFixed(0) + "L",
      );
      setEl("valveActiveClosures", vc.active_closures || 0);
      const autoEl = document.getElementById("valveAutoResponse");
      if (autoEl) {
        autoEl.textContent = vc.auto_response ? "AUTO ON" : "AUTO OFF";
        autoEl.className = "gc-badge " + (vc.auto_response ? "green" : "red");
      }
    }

    // --- Leak Localization ---
    if (data.leak_localization) {
      const loc = data.leak_localization;
      const z = loc.zones || {};
      if (z.zone_A)
        setEl(
          "locMoistureA",
          (z.zone_A.current_moisture || 0).toFixed(1) + "%",
        );
      if (z.zone_B)
        setEl(
          "locMoistureB",
          (z.zone_B.current_moisture || 0).toFixed(1) + "%",
        );
      if (z.zone_C)
        setEl(
          "locMoistureC",
          (z.zone_C.current_moisture || 0).toFixed(1) + "%",
        );
      if (loc.recent && loc.recent.length > 0) {
        const latest = loc.recent[0];
        setEl(
          "locEstimate",
          "Leak near: " +
            latest.estimated_zone.replace(/_/g, " ") +
            " (~" +
            latest.estimated_distance_m +
            "m)",
        );
      } else {
        setEl("locEstimate", "No active localizations");
      }
      setEl(
        "locTotal",
        (loc.total_localizations || 0) + " localizations recorded",
      );
    }

    // --- Calibration ---
    if (data.sensor_calibration) {
      const cal = data.sensor_calibration;
      const s = cal.sensors || {};
      if (s.water_level) {
        setEl("calScaleLevel", s.water_level.scale.toFixed(4));
        setEl("calOffsetLevel", s.water_level.offset.toFixed(4));
      }
      if (s.flow_rate) {
        setEl("calScaleFlow", s.flow_rate.scale.toFixed(4));
        setEl("calOffsetFlow", s.flow_rate.offset.toFixed(4));
      }
      if (s.soil_moisture) {
        setEl("calScaleMoisture", s.soil_moisture.scale.toFixed(4));
        setEl("calOffsetMoisture", s.soil_moisture.offset.toFixed(4));
      }
      if (s.water_temperature) {
        setEl("calScaleTemp", s.water_temperature.scale.toFixed(4));
        setEl("calOffsetTemp", s.water_temperature.offset.toFixed(4));
      }
      setEl("calTotal", cal.total_calibrations || 0);
      const autoEl = document.getElementById("calAuto");
      if (autoEl) {
        autoEl.textContent = cal.auto_enabled ? "AUTO ON" : "AUTO OFF";
        autoEl.className = "gc-badge " + (cal.auto_enabled ? "green" : "red");
      }
    }

    // --- Edge-Cloud ---
    if (data.edge_cloud) {
      setEl(
        "archDataReduction",
        (data.edge_cloud.data_reduction_pct || 0).toFixed(1) + "%",
      );
      setEl("archReadings", data.edge_cloud.readings_processed || 0);
      const cs = document.getElementById("cloudStatusText");
      if (cs) {
        cs.textContent =
          data.edge_cloud.cloud_status === "connected"
            ? "● Connected"
            : "● Disconnected";
        cs.className =
          "at-status " +
          (data.edge_cloud.cloud_status === "connected" ? "online" : "offline");
      }
    }

    // --- Energy Optimization ---
    if (data.energy_optimization) {
      const en = data.energy_optimization;
      const icons = {
        high_freq: "🔴",
        normal: "🔋",
        low_power: "🟢",
        deep_sleep: "😴",
      };
      const names = {
        high_freq: "High Frequency",
        normal: "Normal",
        low_power: "Low Power",
        deep_sleep: "Deep Sleep",
      };
      const descs = {
        high_freq: "Maximum monitoring — event detected",
        normal: "Standard monitoring — moderate activity",
        low_power: "Reduced sampling — stable environment",
        deep_sleep: "Minimal monitoring — ultra-stable",
      };
      setEl("energyModeIcon", icons[en.current_mode] || "🔋");
      setEl("energyMode", names[en.current_mode] || en.current_mode);
      setEl("energyModeDesc", descs[en.current_mode] || "");
      setEl("energyInterval", en.sampling_interval_s + "s");
      setEl("energySaved", (en.energy_saved_pct || 0).toFixed(0) + "%");
      setEl("energyBattery", (en.battery_hours || 0).toFixed(0) + "h");
      setEl("energyStability", (en.stability || 0).toFixed(3));
    }

    // --- Baseline Learning ---
    if (data.baseline_model) {
      const bl = data.baseline_model;
      const phaseEl = document.getElementById("baselinePhase");
      if (phaseEl)
        phaseEl.textContent =
          bl.learning_phase.charAt(0).toUpperCase() +
          bl.learning_phase.slice(1);
      setEl("baselineSamples", bl.samples_learned || 0);
      setEl("baselineAccuracy", (bl.prediction_accuracy || 0).toFixed(1) + "%");
      setEl("baselineVersion", "v" + (bl.model_version || 0));
      const prog = bl.phase_progress || {};
      let pct = 0;
      if (bl.learning_phase === "initial") pct = prog.initial || 0;
      else if (bl.learning_phase === "adapting") pct = prog.adapting || 0;
      else pct = prog.mature || 0;
      const bar = document.getElementById("baselineProgress");
      if (bar) bar.style.width = Math.min(100, pct).toFixed(0) + "%";
      setEl(
        "baselineProgressText",
        Math.min(100, pct).toFixed(0) +
          "% to " +
          (bl.learning_phase === "mature" ? "complete" : "next phase"),
      );
      setEl(
        "baselineCorrelations",
        bl.samples_learned > 50 ? "Active" : "Learning...",
      );
    }
  } catch (e) {
    console.error("Intelligence fetch error:", e);
  }
}

// Fetch intelligence every 15s, first at 3s
setInterval(fetchIntelligenceDashboard, 15000);
setTimeout(fetchIntelligenceDashboard, 3000);
