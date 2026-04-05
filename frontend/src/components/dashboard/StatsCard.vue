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
  if (type === 'percent' || type === 'load') return `${val}`;
  if (typeof val === 'number' && val >= 1_000_000) return `${(val / 1_000_000).toFixed(1)}`;
  if (typeof val === 'number' && val >= 1_000) return `${(val / 1_000).toFixed(0)}`;
  return String(val);
}

function unitSuffix(type, val) {
  if (type === 'percent' || type === 'load') return '%';
  if (type === 'efficiency') return '任务/M';
  if (typeof val === 'number' && val >= 1_000_000) return 'M';
  if (typeof val === 'number' && val >= 1_000) return 'K';
  return '';
}

const trendColor = computed(() => (props.trendDir === 'up') ? 'var(--success)' : 'var(--danger)');
const trendArrow = computed(() => (props.trendDir === 'up') ? '↑' : '↓');

const loadBarColor = computed(() => {
  if (props.loadValue >= 80) return 'var(--danger)';
  if (props.loadValue >= 60) return 'var(--warning)';
  return 'var(--success)';
});
</script>

<template>
  <div class="stats-card">
    <div class="card-label">{{ label }}</div>
    <div class="card-value">
      <span class="number serif">{{ formatValue(type, value) }}</span>
      <span class="unit">{{ unitSuffix(type, value) }}</span>
    </div>
    <div class="card-meta">
      <span v-if="sub" class="sub">{{ sub }}</span>
      <span v-if="trend !== null" class="trend" :style="{ color: trendColor }">
        {{ trendArrow }} {{ trend }}%
      </span>
    </div>
    <!-- Load bar (only for type='load') -->
    <div v-if="type === 'load'" class="load-track">
      <div
        class="load-fill"
        :style="{ width: `${loadValue}%`, background: loadBarColor }"
      ></div>
    </div>
  </div>
</template>

<style scoped>
.stats-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-card);
  padding: 14px 18px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.card-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--text-disabled);
}

.card-value {
  display: flex;
  align-items: baseline;
  gap: 2px;
  line-height: 1;
  margin-top: 4px;
}

.number {
  font-size: 30px;
  font-weight: 400;
  color: var(--text-primary);
  letter-spacing: -1px;
}

.unit {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 400;
  color: var(--text-disabled);
  align-self: flex-end;
  margin-bottom: 3px;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}

.sub {
  font-size: 11px;
  color: var(--text-disabled);
}

.trend {
  font-size: 11px;
  font-weight: 600;
}

/* Load bar */
.load-track {
  height: 2px;
  background: var(--border-subtle);
  border-radius: 2px;
  overflow: hidden;
  margin-top: 8px;
}
.load-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 800ms ease-out;
}
</style>
