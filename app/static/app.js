const state = {
  charts: {
    queue: null,
    throughput: null,
    reward: null,
  },
  districts: [],
  districtById: {},
  activeDistrictId: null,
  latestResultsByDistrict: {},
  flow: {
    mode: "rl",
    step: 0,
    playing: false,
    timer: null,
  },
};

const metricMap = [
  { key: "avg_wait", label: "Average Wait Time", deltaKey: "avg_wait_pct" },
  { key: "avg_queue", label: "Average Queue Length", deltaKey: "avg_queue_pct" },
  { key: "throughput", label: "Total Throughput", deltaKey: "throughput_pct" },
  { key: "clearance_ratio", label: "Clearance Ratio", deltaKey: "clearance_ratio_pct" },
  { key: "emergency_avg_wait", label: "Emergency Avg Wait", deltaKey: "emergency_avg_wait_pct" },
  { key: "max_queue", label: "Max Queue", deltaKey: null },
  { key: "remaining_vehicles", label: "Remaining Vehicles", deltaKey: "remaining_vehicles_pct" },
];

const benchmarkMetricMap = [
  { key: "avg_wait", label: "Average Wait" },
  { key: "avg_queue", label: "Average Queue" },
  { key: "throughput", label: "Throughput" },
  { key: "emergency_avg_wait", label: "Emergency Avg Wait" },
  { key: "clearance_ratio", label: "Clearance Ratio" },
];

const inputIdsForActual = [
  "actual_avg_wait",
  "actual_avg_queue",
  "actual_throughput",
  "actual_emergency_avg_wait",
  "actual_clearance_ratio",
];

function fmt(value, digits = 3) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "-";
  }
  return value.toFixed(digits);
}

function fmtPct(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "-";
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function deltaClass(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "neutral";
  }
  if (value > 0.5) {
    return "good";
  }
  if (value < -0.5) {
    return "bad";
  }
  return "neutral";
}

function parseOptionalNumber(id) {
  const node = document.getElementById(id);
  const value = node.value.trim();
  if (value === "") {
    return null;
  }
  const parsed = Number(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function setStatus(message, isError = false) {
  const status = document.getElementById("status");
  status.textContent = message;
  status.style.color = isError ? "#b53a31" : "#50576a";
}

function destroyChart(existing) {
  if (existing) {
    existing.destroy();
  }
}

function toCumulative(values) {
  const output = [];
  let running = 0;
  for (const value of values) {
    running += value;
    output.push(running);
  }
  return output;
}

function baseChartOptions(xTitle, yTitle) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    resizeDelay: 80,
    animation: false,
    plugins: {
      legend: { position: "bottom" },
    },
    scales: {
      x: { title: { display: true, text: xTitle } },
      y: { title: { display: true, text: yTitle }, beginAtZero: true },
    },
  };
}

function renderCharts(data) {
  const rlSeries = data.time_series.rl;
  const fixedSeries = data.time_series.fixed;
  const labels = Array.from({ length: rlSeries.queue.length }, (_, idx) => idx + 1);

  destroyChart(state.charts.queue);
  state.charts.queue = new Chart(document.getElementById("queueChart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "RL Queue",
          data: rlSeries.queue,
          borderColor: "#008579",
          backgroundColor: "rgba(0, 133, 121, 0.12)",
          pointRadius: 0,
          borderWidth: 2,
          tension: 0.2,
        },
        {
          label: "Fixed Queue",
          data: fixedSeries.queue,
          borderColor: "#de6b1a",
          backgroundColor: "rgba(222, 107, 26, 0.12)",
          pointRadius: 0,
          borderWidth: 2,
          tension: 0.2,
        },
      ],
    },
    options: baseChartOptions("Step", "Queued Vehicles"),
  });

  destroyChart(state.charts.throughput);
  state.charts.throughput = new Chart(document.getElementById("throughputChart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "RL Cumulative Throughput",
          data: toCumulative(rlSeries.throughput),
          borderColor: "#2164d4",
          backgroundColor: "rgba(33, 100, 212, 0.12)",
          pointRadius: 0,
          borderWidth: 2,
          tension: 0.2,
        },
        {
          label: "Fixed Cumulative Throughput",
          data: toCumulative(fixedSeries.throughput),
          borderColor: "#de6b1a",
          backgroundColor: "rgba(222, 107, 26, 0.12)",
          pointRadius: 0,
          borderWidth: 2,
          tension: 0.2,
        },
      ],
    },
    options: baseChartOptions("Step", "Vehicles Served"),
  });

  const rewardLabels = Array.from(
    { length: data.training.moving_avg_rewards.length },
    (_, idx) => idx + 1,
  );

  destroyChart(state.charts.reward);
  state.charts.reward = new Chart(document.getElementById("rewardChart"), {
    type: "line",
    data: {
      labels: rewardLabels,
      datasets: [
        {
          label: "Episode Reward (Moving Avg)",
          data: data.training.moving_avg_rewards,
          borderColor: "#008579",
          backgroundColor: "rgba(0, 133, 121, 0.14)",
          pointRadius: 0,
          borderWidth: 2,
          tension: 0.25,
        },
      ],
    },
    options: baseChartOptions("Episode", "Reward"),
  });
}

function renderSummaryCards(improvements, benchmark) {
  const waitValue = document.getElementById("wait-improvement");
  const queueValue = document.getElementById("queue-improvement");
  const throughputValue = document.getElementById("throughput-improvement");
  const actualWaitValue = document.getElementById("actual-wait-improvement");

  const actualWaitDelta = benchmark?.rl_vs_actual_pct?.avg_wait_pct;

  waitValue.textContent = fmtPct(improvements.avg_wait_pct);
  queueValue.textContent = fmtPct(improvements.avg_queue_pct);
  throughputValue.textContent = fmtPct(improvements.throughput_pct);
  actualWaitValue.textContent = fmtPct(actualWaitDelta);

  waitValue.className = `stat-value ${deltaClass(improvements.avg_wait_pct)}`;
  queueValue.className = `stat-value ${deltaClass(improvements.avg_queue_pct)}`;
  throughputValue.className = `stat-value ${deltaClass(improvements.throughput_pct)}`;
  actualWaitValue.className = `stat-value ${deltaClass(actualWaitDelta)}`;
}

function renderMetricTable(data) {
  const body = document.getElementById("metric-table-body");
  body.innerHTML = "";

  const rl = data.comparison.rl;
  const fixed = data.comparison.fixed;
  const deltas = data.comparison.improvements;

  for (const metric of metricMap) {
    const row = document.createElement("tr");
    const delta = metric.deltaKey ? deltas[metric.deltaKey] : NaN;

    row.innerHTML = `
      <td>${metric.label}</td>
      <td>${fmt(rl[metric.key])}</td>
      <td>${fmt(fixed[metric.key])}</td>
      <td class="${deltaClass(delta)}">${metric.deltaKey ? fmtPct(delta) : "-"}</td>
    `;

    body.appendChild(row);
  }
}

function renderActualBenchmarkTable(benchmark) {
  const body = document.getElementById("actual-benchmark-body");
  body.innerHTML = "";

  for (const metric of benchmarkMetricMap) {
    const actualValue = benchmark.actual[metric.key];
    const rlDelta = benchmark.rl_vs_actual_pct?.[`${metric.key}_pct`];
    const fixedDelta = benchmark.fixed_vs_actual_pct?.[`${metric.key}_pct`];

    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${metric.label}</td>
      <td>${fmt(actualValue)}</td>
      <td class="${deltaClass(rlDelta)}">${fmtPct(rlDelta)}</td>
      <td class="${deltaClass(fixedDelta)}">${fmtPct(fixedDelta)}</td>
    `;
    body.appendChild(row);
  }
}

function clearResultPanels() {
  document.getElementById("wait-improvement").textContent = "-";
  document.getElementById("queue-improvement").textContent = "-";
  document.getElementById("throughput-improvement").textContent = "-";
  document.getElementById("actual-wait-improvement").textContent = "-";

  const metricBody = document.getElementById("metric-table-body");
  metricBody.innerHTML = "<tr><td colspan=\"4\" class=\"placeholder\">Run a simulation to populate results.</td></tr>";

  const benchmarkBody = document.getElementById("actual-benchmark-body");
  benchmarkBody.innerHTML =
    "<tr><td colspan=\"4\" class=\"placeholder\">Run a simulation to compare against district baseline flow.</td></tr>";

  destroyChart(state.charts.queue);
  destroyChart(state.charts.throughput);
  destroyChart(state.charts.reward);
  state.charts.queue = null;
  state.charts.throughput = null;
  state.charts.reward = null;
}

function buildDistrictMap() {
  state.districtById = {};
  for (const district of state.districts) {
    state.districtById[district.district_id] = district;
  }
}

function renderDistrictCards() {
  const cards = document.getElementById("district-cards");
  cards.innerHTML = "";

  for (const district of state.districts) {
    const card = document.createElement("article");
    card.className = `district-card ${district.district_id === state.activeDistrictId ? "active" : ""}`;
    card.innerHTML = `
      <h4>${district.name}</h4>
      <p class="desc">${district.description}</p>
      <p class="meta">Owner: ${district.manager.owner}</p>
      <p class="meta">Pattern: ${district.traffic_pattern}</p>
      <p class="meta">Default cycle: ${district.default_params.fixed_cycle} steps</p>
    `;
    cards.appendChild(card);
  }
}

function renderManagerFocus() {
  const district = state.districtById[state.activeDistrictId];
  if (!district) {
    return;
  }

  document.getElementById("manager-owner").textContent = district.manager.owner;
  document.getElementById("manager-team").textContent = district.manager.team;
  document.getElementById("manager-contact").textContent = district.manager.contact;
}

function applyDistrictDefaults(districtId) {
  const district = state.districtById[districtId];
  if (!district) {
    return;
  }

  document.getElementById("traffic_pattern").value = district.traffic_pattern;
  document.getElementById("fixed_cycle").value = district.default_params.fixed_cycle;
  document.getElementById("service_rate").value = district.default_params.service_rate;
  document.getElementById("emergency_rate").value = district.default_params.emergency_rate;

  document.getElementById("actual_avg_wait").placeholder = `Default: ${district.actual_metrics.avg_wait}`;
  document.getElementById("actual_avg_queue").placeholder = `Default: ${district.actual_metrics.avg_queue}`;
  document.getElementById("actual_throughput").placeholder = `Default: ${district.actual_metrics.throughput}`;
  document.getElementById("actual_emergency_avg_wait").placeholder =
    `Default: ${district.actual_metrics.emergency_avg_wait}`;
  document.getElementById("actual_clearance_ratio").placeholder =
    `Default: ${district.actual_metrics.clearance_ratio}`;
}

function setActiveDistrict(districtId) {
  state.activeDistrictId = districtId;
  document.getElementById("district_id").value = districtId;
  applyDistrictDefaults(districtId);
  renderDistrictCards();
  renderManagerFocus();
  const cached = state.latestResultsByDistrict[districtId];
  if (cached) {
    renderSummaryCards(cached.comparison.improvements, cached.benchmark);
    renderMetricTable(cached);
    renderActualBenchmarkTable(cached.benchmark);
    renderCharts(cached);
  } else {
    clearResultPanels();
  }
  drawFlowSnapshot();
  renderManagementTable();
}

function renderDistrictSelector() {
  const select = document.getElementById("district_id");
  select.innerHTML = "";

  for (const district of state.districts) {
    const option = document.createElement("option");
    option.value = district.district_id;
    option.textContent = district.name;
    select.appendChild(option);
  }

  select.value = state.activeDistrictId;
}

function renderManagementTable() {
  const body = document.getElementById("management-table-body");
  body.innerHTML = "";

  for (const district of state.districts) {
    const result = state.latestResultsByDistrict[district.district_id];
    const waitGain = result?.comparison?.improvements?.avg_wait_pct;
    const throughputGain = result?.comparison?.improvements?.throughput_pct;
    const rlVsActualWait = result?.benchmark?.rl_vs_actual_pct?.avg_wait_pct;

    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${district.name}${district.district_id === state.activeDistrictId ? " (active)" : ""}</td>
      <td>${district.manager.owner}</td>
      <td>${district.manager.team}</td>
      <td class="${deltaClass(waitGain)}">${fmtPct(waitGain)}</td>
      <td class="${deltaClass(throughputGain)}">${fmtPct(throughputGain)}</td>
      <td class="${deltaClass(rlVsActualWait)}">${fmtPct(rlVsActualWait)}</td>
    `;
    body.appendChild(row);
  }
}

async function fetchDistrictCatalog() {
  const response = await fetch("/api/districts");
  if (!response.ok) {
    throw new Error("Could not load district catalog");
  }
  return response.json();
}

function collectFormData() {
  return {
    district_id: document.getElementById("district_id").value,
    episodes: Number(document.getElementById("episodes").value),
    steps_per_episode: Number(document.getElementById("steps_per_episode").value),
    traffic_pattern: document.getElementById("traffic_pattern").value,
    fixed_cycle: Number(document.getElementById("fixed_cycle").value),
    service_rate: Number(document.getElementById("service_rate").value),
    emergency_rate: Number(document.getElementById("emergency_rate").value),
    learning_rate: Number(document.getElementById("learning_rate").value),
    discount_factor: Number(document.getElementById("discount_factor").value),
    epsilon_decay: Number(document.getElementById("epsilon_decay").value),
    seed: Number(document.getElementById("seed").value),
    actual_avg_wait: parseOptionalNumber("actual_avg_wait"),
    actual_avg_queue: parseOptionalNumber("actual_avg_queue"),
    actual_throughput: parseOptionalNumber("actual_throughput"),
    actual_emergency_avg_wait: parseOptionalNumber("actual_emergency_avg_wait"),
    actual_clearance_ratio: parseOptionalNumber("actual_clearance_ratio"),
  };
}

async function runSimulation(payload) {
  const response = await fetch("/api/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Simulation request failed");
  }

  return response.json();
}

function getActiveResult() {
  return state.latestResultsByDistrict[state.activeDistrictId] ?? null;
}

function getActiveSeries() {
  const activeResult = getActiveResult();
  if (!activeResult) {
    return null;
  }
  return activeResult.time_series[state.flow.mode];
}

function updateFlowKpi(stepIndex) {
  const series = getActiveSeries();
  if (!series) {
    return;
  }

  const queue = series.queue[stepIndex] ?? 0;
  const throughput = series.throughput[stepIndex] ?? 0;
  const emergency = series.emergency_queue[stepIndex] ?? 0;
  const phase = series.phase[stepIndex] ?? 0;

  document.getElementById("flow-kpi-queue").textContent = fmt(queue, 2);
  document.getElementById("flow-kpi-throughput").textContent = fmt(throughput, 2);
  document.getElementById("flow-kpi-emergency").textContent = fmt(emergency, 2);
  document.getElementById("flow-kpi-phase").textContent = phase === 0 ? "NS Green" : "EW Green";
}

function drawRoad(ctx, road) {
  const [x1, y1] = road.from;
  const [x2, y2] = road.to;

  ctx.strokeStyle = "#76839b";
  ctx.lineCap = "round";
  ctx.lineWidth = Math.max(6, road.lanes * 2.6);
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();

  ctx.setLineDash([10, 8]);
  ctx.strokeStyle = "rgba(255, 255, 255, 0.75)";
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
  ctx.setLineDash([]);
}

function drawWaterFeature(ctx, water) {
  ctx.fillStyle = "rgba(86, 153, 201, 0.36)";
  ctx.fillRect(water.x, water.y, water.w, water.h);

  ctx.strokeStyle = "rgba(38, 98, 150, 0.6)";
  ctx.lineWidth = 1.4;
  ctx.strokeRect(water.x, water.y, water.w, water.h);

  ctx.strokeStyle = "rgba(255, 255, 255, 0.42)";
  for (let offset = 12; offset < water.h - 10; offset += 24) {
    ctx.beginPath();
    ctx.moveTo(water.x + 10, water.y + offset);
    ctx.bezierCurveTo(
      water.x + water.w * 0.3,
      water.y + offset - 7,
      water.x + water.w * 0.6,
      water.y + offset + 7,
      water.x + water.w - 10,
      water.y + offset,
    );
    ctx.stroke();
  }

  if (water.label) {
    ctx.fillStyle = "rgba(22, 66, 108, 0.9)";
    ctx.font = "11px IBM Plex Mono";
    ctx.textAlign = "left";
    ctx.fillText(water.label, water.x + 10, water.y + 18);
  }
}

function drawGreenZone(ctx, zone) {
  ctx.fillStyle = "rgba(99, 164, 101, 0.24)";
  ctx.fillRect(zone.x, zone.y, zone.w, zone.h);
  ctx.strokeStyle = "rgba(68, 132, 75, 0.5)";
  ctx.lineWidth = 1.3;
  ctx.strokeRect(zone.x, zone.y, zone.w, zone.h);

  if (zone.id) {
    ctx.fillStyle = "rgba(40, 91, 47, 0.9)";
    ctx.font = "10px IBM Plex Mono";
    ctx.textAlign = "left";
    ctx.fillText(zone.id, zone.x + 8, zone.y + 16);
  }
}

function drawParkingLot(ctx, lot) {
  ctx.fillStyle = "rgba(71, 78, 95, 0.3)";
  ctx.fillRect(lot.x, lot.y, lot.w, lot.h);
  ctx.strokeStyle = "rgba(66, 73, 88, 0.62)";
  ctx.lineWidth = 1.2;
  ctx.strokeRect(lot.x, lot.y, lot.w, lot.h);

  const slots = Math.max(8, Math.min(48, lot.slots ?? 20));
  const split = lot.w >= lot.h;

  if (split) {
    const pitch = lot.w / slots;
    for (let i = 1; i < slots; i += 1) {
      const x = lot.x + i * pitch;
      ctx.strokeStyle = "rgba(240, 242, 245, 0.65)";
      ctx.beginPath();
      ctx.moveTo(x, lot.y + 5);
      ctx.lineTo(x, lot.y + lot.h - 5);
      ctx.stroke();
    }
  } else {
    const pitch = lot.h / slots;
    for (let i = 1; i < slots; i += 1) {
      const y = lot.y + i * pitch;
      ctx.strokeStyle = "rgba(240, 242, 245, 0.65)";
      ctx.beginPath();
      ctx.moveTo(lot.x + 5, y);
      ctx.lineTo(lot.x + lot.w - 5, y);
      ctx.stroke();
    }
  }

  if (lot.id) {
    ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
    ctx.font = "10px IBM Plex Mono";
    ctx.textAlign = "left";
    ctx.fillText(lot.id, lot.x + 6, lot.y + 15);
  }
}

function drawPortYard(ctx, yard) {
  ctx.fillStyle = "rgba(204, 182, 145, 0.34)";
  ctx.fillRect(yard.x, yard.y, yard.w, yard.h);
  ctx.strokeStyle = "rgba(141, 109, 65, 0.66)";
  ctx.lineWidth = 1.2;
  ctx.strokeRect(yard.x, yard.y, yard.w, yard.h);

  const cols = Math.max(4, Math.floor(yard.w / 36));
  const rows = Math.max(2, Math.floor(yard.h / 18));
  const blockW = Math.max(14, Math.floor((yard.w - 12) / cols));
  const blockH = Math.max(8, Math.floor((yard.h - 10) / rows));

  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const x = yard.x + 6 + col * blockW;
      const y = yard.y + 5 + row * blockH;
      const colorShade = (row + col) % 2 === 0 ? "rgba(168, 106, 51, 0.48)" : "rgba(120, 89, 49, 0.48)";
      ctx.fillStyle = colorShade;
      ctx.fillRect(x, y, blockW - 2, blockH - 2);
    }
  }

  if (yard.id) {
    ctx.fillStyle = "rgba(104, 73, 33, 0.92)";
    ctx.font = "10px IBM Plex Mono";
    ctx.textAlign = "left";
    ctx.fillText(yard.id, yard.x + 8, yard.y + 14);
  }
}

function drawDistrictFeatures(ctx, district) {
  const { layout, district_id: districtId } = district;

  if (districtId === "university_ring") {
    for (const zone of layout.green_zones ?? []) {
      drawGreenZone(ctx, zone);
    }
    for (const lot of layout.parking_lots ?? []) {
      drawParkingLot(ctx, lot);
    }
  }

  if (districtId === "industrial_port") {
    if (layout.water) {
      drawWaterFeature(ctx, layout.water);
    }
    for (const yard of layout.port_yards ?? []) {
      drawPortYard(ctx, yard);
    }
  }
}

function drawIntersection(ctx, node, phase) {
  ctx.fillStyle = phase === 0 ? "rgba(0, 133, 121, 0.9)" : "rgba(222, 107, 26, 0.9)";
  ctx.beginPath();
  ctx.arc(node.x, node.y, 9, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "#f8fbff";
  ctx.font = "10px IBM Plex Mono";
  ctx.textAlign = "center";
  ctx.fillText(node.id, node.x, node.y + 3);
}

function normalizedLoad(value, divisor = 6) {
  return Math.max(0, Math.min(24, Math.round(value / divisor)));
}

function drawCarsAlongRoad(ctx, road, step, positiveLoad, negativeLoad, emergencyShare) {
  const [x1, y1] = road.from;
  const [x2, y2] = road.to;

  const dx = x2 - x1;
  const dy = y2 - y1;
  const length = Math.max(1, Math.hypot(dx, dy));
  const nx = -dy / length;
  const ny = dx / length;

  function drawDirection(count, reverse, laneOffset, speed, color) {
    for (let i = 0; i < count; i += 1) {
      const seed = ((i * 0.173) + (road.lanes * 0.03)) % 1;
      let t = (step * speed * 0.01 + seed) % 1;
      if (reverse) {
        t = 1 - t;
      }
      const x = x1 + dx * t + nx * laneOffset;
      const y = y1 + dy * t + ny * laneOffset;

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, 2.4, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  const normalColor = "rgba(33, 100, 212, 0.9)";
  const emergencyColor = "rgba(197, 54, 46, 0.95)";

  const positiveCars = normalizedLoad(positiveLoad, 4.5);
  const negativeCars = normalizedLoad(negativeLoad, 4.5);
  const emergencyCars = Math.max(0, Math.min(6, Math.round(emergencyShare / 2)));

  drawDirection(positiveCars, false, 4, 1.4, normalColor);
  drawDirection(negativeCars, true, -4, 1.25, normalColor);
  drawDirection(emergencyCars, false, 8.5, 1.8, emergencyColor);
}

function drawFlowSnapshot() {
  const canvas = document.getElementById("districtFlowCanvas");
  const ctx = canvas.getContext("2d");
  const district = state.districtById[state.activeDistrictId];

  if (!district) {
    return;
  }

  const series = getActiveSeries();
  const maxStep = series ? Math.max(0, series.queue.length - 1) : 0;
  const stepIndex = Math.max(0, Math.min(state.flow.step, maxStep));

  state.flow.step = stepIndex;
  document.getElementById("flow-step").value = String(stepIndex);
  document.getElementById("flow-step-label").textContent = `Step ${stepIndex} / ${maxStep}`;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (district.district_id === "industrial_port") {
    ctx.fillStyle = "#edf2f8";
  } else if (district.district_id === "university_ring") {
    ctx.fillStyle = "#edf5ed";
  } else {
    ctx.fillStyle = "#f0f4f9";
  }
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = "rgba(31, 52, 86, 0.05)";
  for (let x = 0; x < canvas.width; x += 40) {
    ctx.fillRect(x, 0, 1, canvas.height);
  }
  for (let y = 0; y < canvas.height; y += 40) {
    ctx.fillRect(0, y, canvas.width, 1);
  }

  drawDistrictFeatures(ctx, district);

  for (const road of district.layout.roads) {
    drawRoad(ctx, road);
  }

  const phase = series ? series.phase[stepIndex] ?? 0 : 0;
  for (const intersection of district.layout.intersections) {
    drawIntersection(ctx, intersection, phase);
  }

  if (series) {
    const dq = series.directional_queue;
    const de = series.directional_emergency;

    for (const road of district.layout.roads) {
      const [x1, y1] = road.from;
      const [x2, y2] = road.to;
      const horizontal = Math.abs(y2 - y1) < Math.abs(x2 - x1);

      if (horizontal) {
        drawCarsAlongRoad(
          ctx,
          road,
          stepIndex,
          (dq.E[stepIndex] ?? 0) + (de.E[stepIndex] ?? 0),
          (dq.W[stepIndex] ?? 0) + (de.W[stepIndex] ?? 0),
          (de.E[stepIndex] ?? 0) + (de.W[stepIndex] ?? 0),
        );
      } else {
        drawCarsAlongRoad(
          ctx,
          road,
          stepIndex,
          (dq.S[stepIndex] ?? 0) + (de.S[stepIndex] ?? 0),
          (dq.N[stepIndex] ?? 0) + (de.N[stepIndex] ?? 0),
          (de.S[stepIndex] ?? 0) + (de.N[stepIndex] ?? 0),
        );
      }
    }
  }

  ctx.fillStyle = "#1f2940";
  ctx.font = "12px IBM Plex Mono";
  ctx.fillText(`${district.name} | ${state.flow.mode.toUpperCase()} Playback`, 16, 20);

  updateFlowKpi(stepIndex);
}

function stopFlowPlayback() {
  if (state.flow.timer) {
    window.clearInterval(state.flow.timer);
    state.flow.timer = null;
  }
  state.flow.playing = false;
  document.getElementById("flow-play").textContent = "Play";
}

function startFlowPlayback() {
  const series = getActiveSeries();
  if (!series || series.queue.length === 0) {
    return;
  }

  stopFlowPlayback();
  state.flow.playing = true;
  document.getElementById("flow-play").textContent = "Pause";

  const maxStep = series.queue.length - 1;
  state.flow.timer = window.setInterval(() => {
    state.flow.step = state.flow.step >= maxStep ? 0 : state.flow.step + 1;
    drawFlowSnapshot();
  }, 220);
}

function resetFlowSliderForResult() {
  const series = getActiveSeries();
  const slider = document.getElementById("flow-step");

  if (!series || series.queue.length === 0) {
    slider.max = "0";
    slider.value = "0";
    state.flow.step = 0;
    drawFlowSnapshot();
    return;
  }

  slider.max = String(Math.max(0, series.queue.length - 1));
  slider.value = "0";
  state.flow.step = 0;
  drawFlowSnapshot();
}

function clearActualOverrideInputs() {
  for (const id of inputIdsForActual) {
    document.getElementById(id).value = "";
  }
}

function bindDistrictControls() {
  const districtSelect = document.getElementById("district_id");
  districtSelect.addEventListener("change", (event) => {
    const districtId = event.target.value;
    setActiveDistrict(districtId);
    clearActualOverrideInputs();
    stopFlowPlayback();
    setStatus(`Switched to ${state.districtById[districtId].name}. Run simulation to refresh metrics.`);
  });
}

function bindFlowControls() {
  const modeSelect = document.getElementById("flow-mode");
  const slider = document.getElementById("flow-step");
  const playButton = document.getElementById("flow-play");

  modeSelect.addEventListener("change", (event) => {
    state.flow.mode = event.target.value;
    stopFlowPlayback();
    resetFlowSliderForResult();
  });

  slider.addEventListener("input", (event) => {
    state.flow.step = Number(event.target.value);
    drawFlowSnapshot();
  });

  playButton.addEventListener("click", () => {
    if (state.flow.playing) {
      stopFlowPlayback();
      return;
    }
    startFlowPlayback();
  });
}

function bindForm() {
  const form = document.getElementById("simulation-form");
  const runButton = document.getElementById("run-button");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    runButton.disabled = true;
    runButton.textContent = "Training and Evaluating...";
    setStatus("Simulation running. This can take a few seconds.");

    try {
      const payload = collectFormData();
      const data = await runSimulation(payload);

      state.latestResultsByDistrict[payload.district_id] = data;
      state.activeDistrictId = payload.district_id;

      renderSummaryCards(data.comparison.improvements, data.benchmark);
      renderMetricTable(data);
      renderActualBenchmarkTable(data.benchmark);
      renderCharts(data);
      renderManagementTable();
      resetFlowSliderForResult();

      setStatus(
        `Completed for ${data.district.name}. Final epsilon: ${fmt(data.training.final_epsilon, 4)} | Q-table states: ${data.training.q_table_size}`,
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setStatus(`Simulation failed: ${message}`, true);
    } finally {
      runButton.disabled = false;
      runButton.textContent = "Run Simulation";
    }
  });
}

async function initialize() {
  try {
    const payload = await fetchDistrictCatalog();
    state.districts = payload.districts;
    buildDistrictMap();

    if (state.districts.length === 0) {
      throw new Error("No districts configured");
    }

    state.activeDistrictId = state.districts[0].district_id;

    renderDistrictSelector();
    renderDistrictCards();
    renderManagerFocus();
    applyDistrictDefaults(state.activeDistrictId);
    renderManagementTable();
    drawFlowSnapshot();

    bindDistrictControls();
    bindFlowControls();
    bindForm();

    setStatus("Ready. Choose a district and run a simulation.");
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    setStatus(`Startup failed: ${message}`, true);
  }
}

initialize();
