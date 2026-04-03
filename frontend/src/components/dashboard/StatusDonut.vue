<!-- frontend/src/components/dashboard/StatusDonut.vue -->
<!-- e-Agent-OS OpCenter — Status Distribution Donut Chart -->
<script setup>
import { computed } from 'vue';

const props = defineProps({
  data: { type: Array, default: () => [] }, // [{ status, label, count, color }]
});

const total = computed(() => props.data.reduce((s, d) => s + d.count, 0));

const CX = 60, CY = 60, R = 40;

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
  <div class="donut-wrap card">
    <div class="donut-svg-wrap">
      <svg viewBox="0 0 120 120" class="donut-svg">
        <!-- Background ring -->
        <circle
          :cx="CX" :cy="CY" :r="R"
          fill="none"
          stroke="var(--border-subtle)"
          stroke-width="14"
        />
        <!-- Segments -->
        <circle
          v-for="seg in segments"
          :key="seg.status"
          :cx="CX" :cy="CY" :r="R"
          fill="none"
          :stroke="seg.color"
          stroke-width="14"
          :stroke-dasharray="`${seg.dash} ${seg.circumference}`"
          :stroke-dashoffset="-seg.offset + seg.circumference * 0.25"
          stroke-linecap="butt"
          style="transition: stroke-dasharray 600ms ease"
        />
        <!-- Center text -->
        <text x="60" y="55" text-anchor="middle" class="donut-total">{{ total }}</text>
        <text x="60" y="70" text-anchor="middle" class="donut-sub">总员工</text>
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
  padding: var(--space-lg);
  display: flex;
  align-items: center;
  gap: var(--space-xl);
}
.donut-svg-wrap { flex-shrink: 0; }
.donut-svg { width: 120px; height: 120px; }
.donut-total {
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 500;
  fill: var(--text-primary);
}
.donut-sub { font-size: 10px; fill: var(--text-secondary); }
.donut-legend {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}
.legend-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.legend-label { font-size: 13px; color: var(--text-secondary); flex: 1; }
.legend-count {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  min-width: 24px;
  text-align: right;
}
.legend-pct { font-size: 12px; color: var(--text-secondary); min-width: 32px; text-align: right; }
</style>
