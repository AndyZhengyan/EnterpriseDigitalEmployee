<!-- frontend/src/components/dashboard/TokenChart.vue -->
<!-- e-Agent-OS OpCenter — Token Consumption Bar Chart -->
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
  data: { type: Array, default: () => [] },
});

const canvas = ref(null);
let chart = null;

function formatTick(v) {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  return v;
}

function renderChart() {
  if (!canvas.value) return;
  if (chart) { chart.destroy(); chart = null; }
  chart = new Chart(canvas.value, {
    type: 'bar',
    data: {
      labels: props.data.map(d => d.date),
      datasets: [{
        data: props.data.map(d => d.value),
        // Morandi terracotta
        backgroundColor: 'rgba(217, 119, 87, 0.65)',
        hoverBackgroundColor: 'rgba(217, 119, 87, 0.85)',
        borderRadius: 3,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
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
            label: (ctx) => ` ${formatTick(ctx.raw)} Token`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: { color: '#B0AA9F', font: { size: 11 } },
        },
        y: {
          grid: { display: false },
          border: { display: false },
          ticks: {
            color: '#B0AA9F',
            font: { family: 'JetBrains Mono', size: 11 },
            callback: (v) => formatTick(v),
          },
        },
      },
    },
  });
}

onMounted(() => { renderChart(); });
watch(() => props.data, () => { renderChart(); });
</script>

<template>
  <div class="chart-card">
    <div class="chart-title">近7天 Token 消耗</div>
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
  margin-bottom: 14px;
}
.chart-wrap { height: 170px; position: relative; }
</style>
