// Dragon PC Master Monitor - Core Frontend Controller
let soundEnabled = true;
let audioCtx = null;
let lastAlertSoundTime = 0;

// Rolling chart buffers (last 30 samples)
const MAX_SAMPLES = 30;
const historyCpu = [];
const historyTemp = [];
const historyGpu = [];
const historyMem = [];

// Game recording state
let isRecording = false;
let recordStartTime = null;
let recordTimerInterval = null;

// Tab switcher
function switchTab(tabId) {
  document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));

  const targetPane = document.getElementById('tab-' + tabId);
  if (targetPane) targetPane.classList.add('active');

  // Activate matching button
  const btns = document.querySelectorAll('.tab-btn');
  btns.forEach(btn => {
    if (btn.getAttribute('onclick').includes(tabId)) {
      btn.classList.add('active');
    }
  });

  // Trigger canvas resize
  setTimeout(resizeAllCanvases, 50);
}

// Web Audio API Synthesizer (No external file needed)
function initAudio() {
  if (!audioCtx) {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (AudioContext) audioCtx = new AudioContext();
  }
}

function playWarningSound(isCritical = false) {
  if (!soundEnabled) return;
  initAudio();
  if (!audioCtx || audioCtx.state === 'suspended') {
    audioCtx.resume();
  }

  const now = Date.now();
  if (now - lastAlertSoundTime < 2500) return; // cooldown
  lastAlertSoundTime = now;

  try {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();

    osc.type = isCritical ? 'sawtooth' : 'sine';
    osc.frequency.setValueAtTime(isCritical ? 880 : 660, audioCtx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(isCritical ? 440 : 520, audioCtx.currentTime + 0.35);

    gain.gain.setValueAtTime(0.18, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.35);

    osc.connect(gain);
    gain.connect(audioCtx.destination);

    osc.start();
    osc.stop(audioCtx.currentTime + 0.35);
  } catch (e) {
    console.error("Audio play failed:", e);
  }
}

function toggleAudioAlert() {
  soundEnabled = !soundEnabled;
  document.getElementById('soundStatusText').innerText = soundEnabled ? 'ON' : 'OFF';
  document.getElementById('soundIcon').innerText = soundEnabled ? '🔊' : '🔇';
  initAudio();
}

// Fetch Static Specs Once
async function loadStaticSpecs() {
  try {
    const res = await fetch('/api/specs');
    const specs = await res.json();

    // CPU specs
    document.getElementById('cpuModelShort').innerText = specs.cpu_name || 'AMD / Intel Processor';
    document.getElementById('detailCpuName').innerText = specs.cpu_name || '--';
    document.getElementById('detailCpuBase').innerText = (specs.cpu_base_mhz || '--') + ' MHz';
    document.getElementById('detailCpuCores').innerText = specs.cpu_physical_cores || '--';
    document.getElementById('detailCpuThreads').innerText = specs.cpu_threads || '--';
    document.getElementById('cpuThreadsTag').innerText = `${specs.cpu_physical_cores} コア / ${specs.cpu_threads} スレッド`;
    document.getElementById('detailCpuArch').innerText = specs.cpu_arch || '--';

    // GPU specs
    document.getElementById('gpuModelShort').innerText = specs.gpu_name || 'GPU';
    document.getElementById('detailGpuName').innerText = specs.gpu_name || '--';
    document.getElementById('detailGpuDriver').innerText = specs.gpu_driver || '--';
    document.getElementById('detailGpuVram').innerText = (specs.gpu_vram_mb || '--') + ' MB';
    document.getElementById('gpuVramTag').innerText = `VRAM ${specs.gpu_vram_mb || 0} MB`;

    // System Specs
    document.getElementById('specOsCaption').innerText = specs.os_caption || '--';
    document.getElementById('specOsBuild').innerText = specs.os_build || '--';
    document.getElementById('specBoardVendor').innerText = specs.board_vendor || '--';
    document.getElementById('specBoardModel').innerText = specs.board_model || '--';
    document.getElementById('specBiosVersion').innerText = specs.bios_version || '--';
  } catch (err) {
    console.warn("Failed to load static specs:", err);
  }
}

// Realtime Telemetry Loop
async function pollMetrics() {
  try {
    const res = await fetch('/api/metrics');
    const m = await res.json();

    updateDashboard(m);
    updateCpuGpuTab(m);
    updateSpecsTab(m);
    updateProcessesTab(m.top_processes || []);

    // Update rolling history
    pushHistory(m.cpu_percent, m.temperature_c, m.gpu_util, m.memory_percent);
    renderDashboardCharts();

  } catch (e) {
    console.error("Telemetry error:", e);
  } finally {
    setTimeout(pollMetrics, 1000);
  }
}

function updateDashboard(m) {
  // Session Uptime
  const s = m.session_uptime_seconds || 0;
  const h = Math.floor(s / 3600);
  const min = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  let uptimeStr = "";
  if (h > 0) uptimeStr += `${h}時間 `;
  uptimeStr += `${min}分 ${sec}秒`;

  document.getElementById('headerUptime').innerText = uptimeStr;

  // CPU
  document.getElementById('cpuPercentVal').innerText = m.cpu_percent + '%';
  document.getElementById('cpuBar').style.width = m.cpu_percent + '%';
  document.getElementById('cpuFreqBadge').innerText = (m.cpu_freq_mhz || 0) + ' MHz';

  // Memory
  document.getElementById('memPercentVal').innerText = m.memory_percent + '%';
  document.getElementById('memBar').style.width = m.memory_percent + '%';
  document.getElementById('memGbBadge').innerText = `${m.memory_used_gb} / ${m.memory_total_gb} GB`;
  document.getElementById('memAvailText').innerText = `空き: ${m.memory_available_gb} GB`;

  // GPU
  document.getElementById('gpuPercentVal').innerText = m.gpu_util + '%';
  document.getElementById('gpuBar').style.width = m.gpu_util + '%';
  document.getElementById('gpuTempBadge').innerText = (m.gpu_temp_c || 0) + ' ℃';

  // Temperature Hero Card
  const temp = m.temperature_c;
  document.getElementById('tempVal').innerHTML = `${temp}<span class="unit">℃</span>`;
  
  // Ring offset (Circumference ~ 264)
  const ring = document.getElementById('tempRingBar');
  const maxTemp = 100;
  const pct = Math.min(Math.max((temp - 30) / (maxTemp - 30), 0), 1);
  const offset = 264 - (pct * 264);
  ring.style.strokeDashoffset = offset;

  // Temperature Status & Alert Evaluation
  const statusTag = document.getElementById('tempStatusTag');
  const alertBanner = document.getElementById('thermalAlertBanner');
  const tempValEl = document.getElementById('tempVal');

  if (m.alert.level === 'critical') {
    statusTag.className = 'temp-status-tag critical';
    statusTag.innerText = 'CRITICAL OVERHEAT';
    ring.style.stroke = '#ff0055';
    tempValEl.style.color = '#ff0055';

    alertBanner.classList.remove('hidden');
    document.getElementById('alertTitle').innerText = '極度過熱 (CRITICAL OVERHEAT)';
    document.getElementById('alertMessage').innerText = m.alert.message;
    document.getElementById('alertTempDisplay').innerText = temp + '℃';
    playWarningSound(true);

  } else if (m.alert.level === 'warning') {
    statusTag.className = 'temp-status-tag warning';
    statusTag.innerText = 'WARNING';
    ring.style.stroke = '#ff5500';
    tempValEl.style.color = '#ff5500';

    alertBanner.classList.remove('hidden');
    document.getElementById('alertTitle').innerText = '高温警告 (WARNING)';
    document.getElementById('alertMessage').innerText = m.alert.message;
    document.getElementById('alertTempDisplay').innerText = temp + '℃';
    playWarningSound(false);

  } else if (m.alert.level === 'caution') {
    statusTag.className = 'temp-status-tag caution';
    statusTag.innerText = 'CAUTION';
    ring.style.stroke = '#ff9100';
    tempValEl.style.color = '#ff9100';
    alertBanner.classList.add('hidden');

  } else {
    statusTag.className = 'temp-status-tag';
    statusTag.innerText = 'NORMAL';
    ring.style.stroke = '#00ff9d';
    tempValEl.style.color = '#00ff9d';
    alertBanner.classList.add('hidden');
  }

  // Quick Disks
  const disksEl = document.getElementById('dashboardDisksList');
  if (m.disks && m.disks.length > 0) {
    disksEl.innerHTML = m.disks.map(d => `
      <div class="disk-item">
        <span>${d.mount} (${d.used_gb}/${d.total_gb} GB)</span>
        <div class="disk-mini-bar">
          <div class="disk-mini-fill" style="width: ${d.percent}%;"></div>
        </div>
        <span>${d.percent}%</span>
      </div>
    `).join('');
  }

  // Network & Disk I/O
  document.getElementById('netDownVal').innerText = formatSpeed(m.net_download_kbps);
  document.getElementById('netUpVal').innerText = formatSpeed(m.net_upload_kbps);
  document.getElementById('diskReadVal').innerText = formatSpeed(m.disk_read_kbps);
  document.getElementById('diskWriteVal').innerText = formatSpeed(m.disk_write_kbps);
}

function formatSpeed(kbps) {
  if (kbps >= 1024) {
    return (kbps / 1024).toFixed(1) + ' MB/s';
  }
  return kbps.toFixed(1) + ' KB/s';
}

function updateCpuGpuTab(m) {
  document.getElementById('detailCpuFreq').innerText = (m.cpu_freq_mhz || '--') + ' MHz';
  document.getElementById('detailCpuTemp').innerText = m.temperature_c + ' ℃';
  document.getElementById('detailGpuUtil').innerText = m.gpu_util + ' %';
  document.getElementById('detailGpuTemp').innerText = (m.gpu_temp_c || '--') + ' ℃';
  document.getElementById('gpuCircleVal').innerText = m.gpu_util + '%';

  // Per core bars
  const coresContainer = document.getElementById('coresBarContainer');
  if (m.cpu_per_core && m.cpu_per_core.length > 0) {
    coresContainer.innerHTML = m.cpu_per_core.map((coreVal, idx) => `
      <div class="core-item">
        <div class="core-header">
          <span>コア #${idx + 1}</span>
          <span>${coreVal}%</span>
        </div>
        <div class="core-bar-bg">
          <div class="core-bar-fill" style="width: ${coreVal}%;"></div>
        </div>
      </div>
    `).join('');
  }
}

function updateSpecsTab(m) {
  // Session Uptime & Kernel Uptime
  const s = m.session_uptime_seconds || 0;
  const h = Math.floor(s / 3600);
  const min = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  let sessionStr = "";
  if (h > 0) sessionStr += `${h}時間 `;
  sessionStr += `${min}分 ${sec}秒`;

  const specSession = document.getElementById('specSessionUptime');
  if (specSession) specSession.innerText = sessionStr;

  const specKernel = document.getElementById('specKernelUptime');
  if (specKernel) specKernel.innerText = `${m.kernel_uptime_hours || 0} 時間 (連続保持)`;

  // Battery
  const batEl = document.getElementById('specBattery');
  if (m.battery) {
    batEl.innerText = `${m.battery.percent}% (${m.battery.power_plugged ? 'AC電源接続中' : 'バッテリー駆動'})`;
  } else {
    batEl.innerText = 'デスクトップPC (AC給電)';
  }

  // Full Disks
  const fullDisks = document.getElementById('fullDisksContainer');
  if (m.disks && m.disks.length > 0) {
    fullDisks.innerHTML = m.disks.map(d => `
      <div class="disk-detail-card">
        <div class="card-header">
          <span class="card-title">${d.device} [${d.mount}]</span>
          <span class="card-badge">${d.fstype}</span>
        </div>
        <div class="spec-table">
          <div class="spec-row"><span class="k">総容量</span><span class="v">${d.total_gb} GB</span></div>
          <div class="spec-row"><span class="k">使用中</span><span class="v">${d.used_gb} GB (${d.percent}%)</span></div>
          <div class="spec-row"><span class="k">空き領域</span><span class="v highlight">${d.free_gb} GB</span></div>
        </div>
        <div class="progress-bar-bg" style="margin-top: 10px;">
          <div class="progress-bar-fill" style="width: ${d.percent}%;"></div>
        </div>
      </div>
    `).join('');
  }
}

function updateProcessesTab(procs) {
  const tbody = document.getElementById('processTableBody');
  if (!procs || procs.length === 0) return;

  tbody.innerHTML = procs.map(p => `
    <tr>
      <td>${p.pid}</td>
      <td><strong>${escapeHtml(p.name)}</strong></td>
      <td style="color: #00f0ff;">${p.cpu}%</td>
      <td style="color: #00ff9d;">${p.mem}%</td>
      <td>
        <div class="proc-bar-wrap">
          <div class="proc-bar-fill" style="width: ${Math.min(p.cpu + p.mem, 100)}%;"></div>
        </div>
      </td>
    </tr>
  `).join('');
}

function escapeHtml(str) {
  return (str || '').replace(/[&<>"']/g, function(m) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m];
  });
}

// Chart History & Canvas Rendering
function pushHistory(cpu, temp, gpu, mem) {
  historyCpu.push(cpu);
  historyTemp.push(temp);
  historyGpu.push(gpu);
  historyMem.push(mem);

  if (historyCpu.length > MAX_SAMPLES) historyCpu.shift();
  if (historyTemp.length > MAX_SAMPLES) historyTemp.shift();
  if (historyGpu.length > MAX_SAMPLES) historyGpu.shift();
  if (historyMem.length > MAX_SAMPLES) historyMem.shift();
}

function renderDashboardCharts() {
  drawDualLineChart('realtimeCpuTempCanvas', historyCpu, '#00f0ff', historyTemp, '#ff5500', 100);
  drawDualLineChart('realtimeGpuMemCanvas', historyGpu, '#00ff9d', historyMem, '#b026ff', 100);
}

function drawDualLineChart(canvasId, data1, color1, data2, color2, maxVal) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;

  if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
    canvas.width = w * dpr;
    canvas.height = h * dpr;
  }
  ctx.save();
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  // Grid lines
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
  ctx.lineWidth = 1;
  for (let y = 0.25; y <= 0.75; y += 0.25) {
    ctx.beginPath();
    ctx.moveTo(0, h * y);
    ctx.lineTo(w, h * y);
    ctx.stroke();
  }

  // Draw Series 2
  drawLine(ctx, data2, color2, maxVal, w, h);
  // Draw Series 1
  drawLine(ctx, data1, color1, maxVal, w, h);

  ctx.restore();
}

function drawLine(ctx, data, color, maxVal, w, h) {
  if (data.length < 2) return;
  const stepX = w / (MAX_SAMPLES - 1);

  ctx.beginPath();
  data.forEach((val, i) => {
    const x = i * stepX;
    const y = h - ((val / maxVal) * (h - 20) + 10);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.5;
  ctx.stroke();

  // Glow fill
  ctx.lineTo((data.length - 1) * stepX, h);
  ctx.lineTo(0, h);
  ctx.closePath();
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, color.replace(')', ', 0.18)').replace('rgb', 'rgba').replace('#', 'rgba('));
  grad.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = grad;
  ctx.fill();
}

function resizeAllCanvases() {
  renderDashboardCharts();
}
window.addEventListener('resize', resizeAllCanvases);

// Game Flight Recorder Functions
async function startGameRecording() {
  try {
    const res = await fetch('/api/game/start', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'recording_started') {
      isRecording = true;
      recordStartTime = Date.now();

      document.getElementById('btnStartRecord').classList.add('hidden');
      document.getElementById('btnStopRecord').classList.remove('hidden');
      document.getElementById('recordingLiveStatus').classList.remove('hidden');
      document.getElementById('recorderEmptyState').classList.add('hidden');
      document.getElementById('sessionResultContainer').classList.add('hidden');

      if (recordTimerInterval) clearInterval(recordTimerInterval);
      recordTimerInterval = setInterval(updateRecordTimer, 500);
    }
  } catch (err) {
    alert("記録開始に失敗しました: " + err);
  }
}

function updateRecordTimer() {
  if (!isRecording) return;
  const elapsed = ((Date.now() - recordStartTime) / 1000).toFixed(1);
  document.getElementById('recordDuration').innerText = elapsed;
  // Fetch live count
  fetch('/api/game/status').then(r => r.json()).then(s => {
    document.getElementById('recordSampleCount').innerText = s.samples || 0;
  }).catch(() => {});
}

async function stopGameRecording() {
  try {
    if (recordTimerInterval) clearInterval(recordTimerInterval);
    isRecording = false;

    const res = await fetch('/api/game/stop', { method: 'POST' });
    const summary = await res.json();

    document.getElementById('btnStartRecord').classList.remove('hidden');
    document.getElementById('btnStopRecord').classList.add('hidden');
    document.getElementById('recordingLiveStatus').classList.add('hidden');
    document.getElementById('sessionResultContainer').classList.remove('hidden');

    // Populate Report
    document.getElementById('resDuration').innerText = (summary.duration_sec || 0) + ' 秒';
    document.getElementById('resCpu').innerText = `${summary.avg_cpu}% / ${summary.max_cpu}%`;
    document.getElementById('resGpu').innerText = `${summary.avg_gpu}% / ${summary.max_gpu}%`;
    document.getElementById('resMaxTemp').innerText = (summary.max_temp || 0) + ' ℃';
    document.getElementById('resPeakMem').innerText = (summary.peak_mem || 0) + ' %';
    document.getElementById('resBottleneck').innerText = summary.bottleneck || '正常';

    // Draw Session Timeline Chart
    if (summary.timeline && summary.timeline.length > 0) {
      renderSessionTimelineChart(summary.timeline);
    }
  } catch (err) {
    alert("記録停止＆解析に失敗しました: " + err);
  }
}

function renderSessionTimelineChart(timeline) {
  const canvas = document.getElementById('sessionTimelineCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;

  canvas.width = w * dpr;
  canvas.height = h * dpr;
  ctx.save();
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  const n = timeline.length;
  if (n < 2) {
    ctx.restore();
    return;
  }
  const stepX = w / (n - 1);

  // Draw CPU line (Cyan)
  drawSessionSeries(ctx, timeline.map(p => p.cpu), '#00f0ff', 100, stepX, h);
  // Draw GPU line (Green)
  drawSessionSeries(ctx, timeline.map(p => p.gpu), '#00ff9d', 100, stepX, h);
  // Draw Temp line (Orange)
  drawSessionSeries(ctx, timeline.map(p => p.temp), '#ff5500', 100, stepX, h);

  ctx.restore();
}

function drawSessionSeries(ctx, data, color, maxVal, stepX, h) {
  ctx.beginPath();
  data.forEach((val, i) => {
    const x = i * stepX;
    const y = h - ((val / maxVal) * (h - 20) + 10);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.stroke();
}

// Initialization on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  loadStaticSpecs();
  pollMetrics();
});
