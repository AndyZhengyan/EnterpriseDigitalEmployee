<!-- frontend/src/components/dashboard/StatsCard.vue -->
<!-- e-Agent-OS OpCenter — Dashboard Stats Card -->
<script setup>
import { computed } from 'vue';

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  sub: { type: String, default: '' },
  trend: { type: Number, default: null },
  trendDir: { type: String, default: null },
  type: { type: String, default: 'number' },
  loadValue: { type: Number, default: null },
});

function formatValue(type, val) {
  if (type === 'percent' || type === 'load') return `${val}%`;
  if (typeof val === 'number' && val >= 1_000_000) return `${(val / 1_000_000).toFixed(1)}M`;
  if (typeof val === 'number' && val >= 1_000) return `${(val / 1_000).toFixed(0)}K`;
  return String(val);
}

function trendColor(dir) {
  return dir === 'up' ? 'var(--success)' : 'var(--danger)';
}

function trendArrow(dir) {
  return dir === 'up' ? '↑' : '↓';
}

const loadBarColor = computed(() => {
  if (props.loadValue >= 80) return 'var(--danger)';
  if (props.loadValue >= 60) return 'var(--warning)';
  return 'var(--success)';
});
</script>

<template>
  <div class="stats-card card">
    <div class="stats-top">
      <span class="stats-label">{{ label }}</span>
      <span
        v-if="trend !== null"
        class="stats-trend"
        :style="{ color: trendColor(trendDir) }"
      >
        {{ trendArrow(trendDir) }} {{ trend }}%
      </span>
    </div>

    <div class="stats-value">{{ formatValue(type, value) }}</div>

    <div v-if="sub" class="stats-sub">{{ sub }}</div>

    <!-- Load bar (only for type='load') -->
    <div v-if="type === 'load'" class="load-track">
      <div
        class="load-fill"
        :style="{
          width: `${loadValue}%`,
          background: loadBarColor
        }"
      ></div>
    </div>
  </div>
</template>

<style scoped>
.stats-card {
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}
.stats-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.stats-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.stats-trend {
  font-size: 13px;
  font-weight: 600;
}
.stats-value {
  font-family: var(--font-mono);
  font-size: 32px;
  font-weight: 500;
  color: var(--accent-primary);
  line-height: 1;
  margin-top: 2px;
}
.stats-sub {
  font-size: 13px;
  color: var(--text-secondary);
}
.load-track {
  height: 6px;
  background: var(--bg-elevated);
  border-radius: 3px;
  overflow: hidden;
  margin-top: var(--space-sm);
}
.load-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 800ms ease-out;
}
</style>
