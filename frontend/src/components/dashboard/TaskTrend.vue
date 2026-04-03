<!-- frontend/src/components/dashboard/TaskTrend.vue -->
<!-- e-Agent-OS OpCenter — Task Completion Trend Line Chart -->
<script setup>
import { ref, onMounted, watch } from 'vue';
import {
  Chart,
  LineController,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Filler,
} from 'chart.js';

Chart.register(LineController, LineElement, PointElement, CategoryScale, LinearScale, Tooltip, Filler);

const props = defineProps({
  data: { type: Array, default: () => [] },
});

const canvas = ref(null);
let chart = null;

function renderChart() {
  if (!canvas.value) return;
  if (chart) { chart.destroy(); chart = null; }
  chart = new Chart(canvas.value, {
    type: 'line',
    data: {
      labels: props.data.map(d => d.date),
      datasets: [{
        data: props.data.map(d => d.value),
        // Morandi dark teal
        borderColor: 'rgba(142, 154, 175, 0.85)',
        backgroundColor: 'rgba(142, 154, 175, 0.08)',
        fill: true,
        tension: 0.5,
        pointRadius: 3,
        pointBackgroundColor: 'rgba(142, 154, 175, 0.85)',
        pointBorderWidth: 0,
        borderWidth: 1.5,
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
          callbacks: { label: (ctx) => ` ${ctx.raw} 任务` },
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
          ticks: { color: '#B0AA9F', font: { family: 'JetBrains Mono', size: 11 } },
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
    <div class="chart-title">近7天任务完成趋势</div>
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
