<!-- frontend/src/components/dashboard/TaskChart.vue -->
<!-- e-Agent-OS OpCenter — Task & Token Dual Bar Chart -->
<script setup>
import { ref, onMounted, watch } from 'vue';
import {
  Chart,
  BarController,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
} from 'chart.js';

Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip);

const props = defineProps({
  taskData:   { type: Array,  default: () => [] }, // [{ date, value }] — tasks
  tokenData:  { type: Array,  default: () => [] }, // [{ date, value }] — token M
});

const canvas = ref(null);
let chart = null;

function formatToken(v) {
  if (v >= 1000) return `${(v / 1000).toFixed(1)}K`;
  return v;
}

function renderChart() {
  if (!canvas.value) return;
  if (chart) { chart.destroy(); chart = null; }

  const labels = props.taskData.map(d => d.date);

  chart = new Chart(canvas.value, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: '任务',
          data: props.taskData.map(d => d.value),
          backgroundColor: 'rgba(217, 119, 87, 0.70)',
          hoverBackgroundColor: 'rgba(217, 119, 87, 0.88)',
          borderRadius: 3,
          borderSkipped: false,
          yAxisID: 'yTask',
        },
        {
          label: 'Token',
          data: props.tokenData.map(d => d.value),
          backgroundColor: 'rgba(142, 154, 175, 0.55)',
          hoverBackgroundColor: 'rgba(142, 154, 175, 0.75)',
          borderRadius: 3,
          borderSkipped: false,
          yAxisID: 'yToken',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#fff',
          titleColor: '#2C2A28',
          bodyColor: '#8A8279',
          borderColor: 'rgba(44,42,40,0.08)',
          borderWidth: 1,
          padding: 10,
          cornerRadius: 6,
          callbacks: {
            label: (ctx) => {
              if (ctx.datasetIndex === 0) return ` ${ctx.raw} 任务`;
              return ` ${ctx.raw.toFixed(2)} M Token`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: { color: '#B0AA9F', font: { size: 11 } },
        },
        yTask: {
          position: 'left',
          grid: { display: false },
          border: { display: false },
          ticks: {
            color: 'rgba(217, 119, 87, 0.70)',
            font: { family: 'JetBrains Mono', size: 11 },
            callback: (v) => formatToken(v),
          },
        },
        yToken: {
          position: 'right',
          grid: { display: false },
          border: { display: false },
          ticks: {
            color: 'rgba(142, 154, 175, 0.70)',
            font: { family: 'JetBrains Mono', size: 11 },
            callback: (v) => `${v}M`,
          },
        },
      },
    },
  });
}

onMounted(() => { renderChart(); });
watch([() => props.taskData, () => props.tokenData], () => { renderChart(); });
</script>

<template>
  <div class="chart-card">
    <div class="chart-title">近7天任务 &amp; Token 消耗</div>
    <!-- Custom dual-axis legend -->
    <div class="chart-legend">
      <span class="legend-item">
        <span class="legend-dot" style="background: rgba(217,119,87,0.70)"></span>
        任务数
      </span>
      <span class="legend-item">
        <span class="legend-dot" style="background: rgba(142,154,175,0.55)"></span>
        Token
      </span>
    </div>
    <div class="chart-wrap">
      <canvas ref="canvas"></canvas>
    </div>
  </div>
</template>

<style scoped>
.chart-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  padding: 14px 18px 12px;
  height: 100%;
}
.chart-title {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--text-disabled);
  margin-bottom: 8px;
}
.chart-legend {
  display: flex;
  gap: 16px;
  margin-bottom: 10px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--text-secondary);
}
.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  flex-shrink: 0;
}
.chart-wrap { height: 150px; position: relative; }
</style>
