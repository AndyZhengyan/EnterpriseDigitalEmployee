<!-- frontend/src/components/dashboard/CapabilityChart.vue -->
<!-- e-Agent-OS OpCenter — Capability Distribution Horizontal Bar Chart -->
<script setup>
const props = defineProps({
  data: { type: Array, default: () => [] }, // [{ role, alias, dept, pct }]
});

const TOTAL = 100;

function barColor(index) {
  // Top item: full opacity, others: fading
  const opacities = [0.85, 0.60, 0.45, 0.32, 0.22, 0.15];
  return `rgba(217, 119, 87, ${opacities[index] ?? 0.15})`;
}
</script>

<template>
  <div class="capability-card">
    <div class="capability-title">能力分布</div>
    <ul class="capability-list">
      <li
        v-for="(item, i) in data"
        :key="item.role"
        class="capability-item"
      >
        <div class="cap-info">
          <span class="cap-alias">{{ item.alias }}</span>
          <span class="cap-role">{{ item.role }}</span>
        </div>
        <div class="cap-bar-row">
          <div class="cap-bar-track">
            <div
              class="cap-bar-fill"
              :style="{ width: `${item.pct}%`, background: barColor(i) }"
            ></div>
          </div>
          <span class="cap-pct">{{ item.pct }}%</span>
        </div>
      </li>
      <li v-if="!data.length" class="cap-empty">暂无数据</li>
    </ul>
  </div>
</template>

<style scoped>
.capability-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  padding: 14px 18px 12px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.capability-title {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--text-disabled);
  margin-bottom: 14px;
  flex-shrink: 0;
}

.capability-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  justify-content: center;
}

.capability-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cap-info {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.cap-alias {
  font-family: var(--font-serif);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
}

.cap-role {
  font-size: 11px;
  color: var(--text-disabled);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cap-bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cap-bar-track {
  flex: 1;
  height: 4px;
  background: var(--bg-elevated);
  border-radius: 2px;
  overflow: hidden;
}

.cap-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 600ms ease-out;
}

.cap-pct {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-secondary);
  min-width: 30px;
  text-align: right;
  flex-shrink: 0;
}

.cap-empty {
  font-size: 12px;
  color: var(--text-disabled);
  text-align: center;
  padding: 24px 0;
}
</style>
