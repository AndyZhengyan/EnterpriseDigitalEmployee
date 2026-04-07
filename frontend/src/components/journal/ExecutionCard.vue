<!-- frontend/src/components/journal/ExecutionCard.vue -->
<!-- e-Agent-OS OpCenter — Journal Execution Card -->
<script setup>
const props = defineProps({
  item: {
    type: Object,
    required: true,
  },
  selected: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['select']);

function formatTimeShort(iso) {
  const d = new Date(iso);
  return d.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

function formatDuration(ms) {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function truncate(text, maxLen = 60) {
  if (!text) return '';
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen) + '...';
}

function statusIcon(status) {
  return status === 'ok' ? '✓' : '✗';
}
</script>

<template>
  <div
    class="exec-card"
    :class="{ selected }"
    @click="emit('select', item)"
    role="button"
    :aria-selected="selected"
  >
    <!-- 卡片头部：时间 + 状态 -->
    <div class="card-header">
      <span class="card-time">{{ formatTimeShort(item.createdAt) }}</span>
      <span class="card-status" :class="item.status">
        {{ statusIcon(item.status) }}
      </span>
    </div>

    <!-- 主体：别名 + 角色 + 部门 -->
    <div class="card-meta">
      <span class="card-alias">{{ item.alias }}</span>
      <span class="card-sep">·</span>
      <span class="card-role">{{ item.role }}</span>
    </div>
    <div class="card-dept">{{ item.dept }}</div>

    <!-- 摘要 -->
    <div class="card-summary">{{ truncate(item.summary, 72) }}</div>

    <!-- 底部：token + 耗时 -->
    <div class="card-footer">
      <span class="card-stat">
        <span class="stat-label">Token</span>
        <span class="stat-value">{{ (item.tokenTotal ?? 0).toLocaleString() }}</span>
      </span>
      <span class="card-stat">
        <span class="stat-label">耗时</span>
        <span class="stat-value">{{ formatDuration(item.durationMs) }}</span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.exec-card {
  padding: var(--space-md);
  border-bottom: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: background-color 0.12s;
  border-left: 3px solid transparent;
  background: var(--bg-card);
}

.exec-card:hover {
  background: var(--bg-elevated);
}

.exec-card.selected {
  background: var(--bg-elevated);
  border-left-color: var(--accent-primary);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.card-time {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-disabled);
}

.card-status {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.card-status.ok {
  background: color-mix(in srgb, var(--accent-primary) 15%, transparent);
  color: var(--accent-primary);
}

.card-status.error {
  background: color-mix(in srgb, #C0392B 15%, transparent);
  color: #C0392B;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 2px;
}

.card-alias {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.card-sep {
  color: var(--text-disabled);
  font-size: 12px;
}

.card-role {
  font-size: 13px;
  color: var(--text-secondary);
}

.card-dept {
  font-size: 12px;
  color: var(--text-disabled);
  margin-bottom: 8px;
}

.card-summary {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 8px;
}

.card-footer {
  display: flex;
  gap: var(--space-md);
}

.card-stat {
  display: flex;
  gap: 4px;
  align-items: center;
}

.stat-label {
  font-size: 11px;
  color: var(--text-disabled);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.stat-value {
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--text-secondary);
}
</style>
