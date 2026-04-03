<!-- frontend/src/components/dashboard/StatusDonut.vue -->
<!-- e-Agent-OS OpCenter — Status Distribution Donut Chart -->
<script setup>
import { computed } from 'vue';

const props = defineProps({
  data: { type: Array, default: () => [] }, // [{ status, label, count, color }]
});

const total = computed(() => props.data.reduce((s, d) => s + d.count, 0));

const CX = 58, CY = 58, R = 42;

const segments = computed(() => {
  const circumference = 2 * Math.PI * R;
  let offset = 0;
  return props.data.map(item => {
    const t = total.value;
    const pct = t > 0 ? item.count / t : 0;
    const dash = pct * circumference;
    const seg = { ...item, dash, offset, circumference };
    offset += dash;
    return seg;
  });
});
</script>

<template>
  <div class="donut-wrap">
    <div class="donut-svg-wrap">
      <svg viewBox="0 0 116 116" class="donut-svg">
        <!-- Background ring -->
        <circle
          :cx="CX" :cy="CY" :r="R"
          fill="none"
          stroke="var(--border-subtle)"
          stroke-width="13"
        />
        <!-- Segments -->
        <circle
          v-for="seg in segments"
          :key="seg.status"
          :cx="CX" :cy="CY" :r="R"
          fill="none"
          :stroke="seg.color"
          stroke-width="13"
          :stroke-dasharray="`${seg.dash} ${seg.circumference}`"
          :stroke-dashoffset="-seg.offset + seg.circumference * 0.25"
          stroke-linecap="butt"
          style="transition: stroke-dasharray 600ms ease"
        />
        <!-- Center text — big number + small label -->
        <text x="58" y="49" text-anchor="middle" class="donut-total serif">{{ total }}</text>
        <text x="58" y="65" text-anchor="middle" class="donut-sub">总员工</text>
      </svg>
    </div>

    <!-- Legend -->
    <div class="donut-legend">
      <div v-for="item in data" :key="item.status" class="legend-row">
        <span class="legend-dot" :style="{ background: item.color }"></span>
        <span class="legend-label">{{ item.label }}</span>
        <span class="legend-count">{{ item.count }}</span>
        <span class="legend-pct">{{ total > 0 ? Math.round(item.count / total * 100) : 0 }}%</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.donut-wrap {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  padding: 14px 18px;
  display: flex;
  align-items: center;
  gap: 20px;
  height: 100%;
}
.donut-svg-wrap { flex-shrink: 0; }
.donut-svg { width: 116px; height: 116px; }
.donut-total {
  font-family: var(--font-serif);
  font-size: 28px;
  font-weight: 400;
  fill: var(--text-primary);
}
.donut-sub {
  font-size: 9px;
  fill: var(--text-disabled);
  letter-spacing: 0.08em;
}
.donut-legend {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.legend-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.legend-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.legend-label {
  font-size: 12px;
  color: var(--text-secondary);
  flex: 1;
  white-space: nowrap;
}
.legend-count {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  min-width: 18px;
  text-align: right;
}
.legend-pct {
  font-size: 11px;
  color: var(--text-disabled);
  min-width: 26px;
  text-align: right;
}
</style>
