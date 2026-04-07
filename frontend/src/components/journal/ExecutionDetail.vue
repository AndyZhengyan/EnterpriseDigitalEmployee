<!-- frontend/src/components/journal/ExecutionDetail.vue -->
<!-- e-Agent-OS OpCenter — Journal Execution Detail -->
<script setup>
const props = defineProps({
  item: {
    type: Object,
    default: null,
  },
});

function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

function formatDuration(ms) {
  if (!ms) return '—';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatToken(n) {
  if (!n && n !== 0) return '—';
  return n.toLocaleString();
}
</script>

<template>
  <div class="detail-panel">
    <!-- 未选中状态 -->
    <div v-if="!item" class="detail-empty">
      <div class="empty-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/>
          <rect x="9" y="3" width="6" height="4" rx="1"/>
          <line x1="9" y1="12" x2="15" y2="12"/>
          <line x1="9" y1="15" x2="13" y2="15"/>
        </svg>
      </div>
      <p class="empty-text">选择一条记录查看详情</p>
    </div>

    <!-- 详情内容 -->
    <template v-else>
      <!-- 状态标签 + 标题 -->
      <div class="detail-header">
        <span class="status-badge" :class="item.status">
          {{ item.status === 'ok' ? '成功' : '失败' }}
        </span>
        <h2 class="detail-title">{{ item.message }}</h2>
      </div>

      <!-- 时间 -->
      <div class="detail-time">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        </svg>
        {{ formatTime(item.createdAt) }}
      </div>

      <!-- 字段网格 -->
      <div class="detail-grid">
        <div class="grid-item">
          <span class="grid-label">执行人</span>
          <span class="grid-value">{{ item.alias }}</span>
        </div>
        <div class="grid-item">
          <span class="grid-label">角色</span>
          <span class="grid-value">{{ item.role }}</span>
        </div>
        <div class="grid-item">
          <span class="grid-label">部门</span>
          <span class="grid-value">{{ item.dept }}</span>
        </div>
        <div class="grid-item">
          <span class="grid-label">Blueprint</span>
          <span class="grid-value mono">{{ item.blueprintId || '—' }}</span>
        </div>
        <div class="grid-item">
          <span class="grid-label">Token</span>
          <span class="grid-value mono">{{ formatToken(item.tokenTotal) }}</span>
        </div>
        <div class="grid-item">
          <span class="grid-label">耗时</span>
          <span class="grid-value mono">{{ formatDuration(item.durationMs) }}</span>
        </div>
      </div>

      <!-- 分割线 -->
      <div class="section-divider">
        <span class="divider-label">原始输入</span>
      </div>

      <!-- 原始输入 -->
      <div class="code-block">
        <pre>{{ item.input ?? '' }}</pre>
      </div>

      <!-- 分割线 -->
      <div class="section-divider">
        <span class="divider-label">输出摘要</span>
      </div>

      <!-- 输出摘要 -->
      <div class="code-block output-block">
        <pre>{{ item.summary ?? '' }}</pre>
      </div>
    </template>
  </div>
</template>

<style scoped>
.detail-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.detail-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
  color: var(--text-disabled);
}

.empty-icon {
  opacity: 0.4;
}

.empty-text {
  font-size: 14px;
  margin: 0;
}

.detail-header {
  padding: var(--space-lg) var(--space-lg) var(--space-sm);
  flex-shrink: 0;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: var(--space-sm);
}

.status-badge.ok {
  background: color-mix(in srgb, var(--accent-primary) 12%, transparent);
  color: var(--accent-primary);
}

.status-badge.error {
  background: color-mix(in srgb, #C0392B 12%, transparent);
  color: #C0392B;
}

.detail-title {
  font-family: var(--font-serif);
  font-size: 20px;
  font-weight: 400;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.4;
}

.detail-time {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 var(--space-lg) var(--space-md);
  font-size: 13px;
  color: var(--text-disabled);
  font-family: var(--font-mono);
  flex-shrink: 0;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1px;
  background: var(--border-subtle);
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.grid-item {
  background: var(--bg-card);
  padding: var(--space-sm) var(--space-md);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.grid-label {
  font-size: 11px;
  color: var(--text-disabled);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.grid-value {
  font-size: 13px;
  color: var(--text-primary);
}

.grid-value.mono {
  font-family: var(--font-mono);
}

.section-divider {
  padding: var(--space-md) var(--space-lg) 0;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.divider-label {
  font-size: 11px;
  color: var(--text-disabled);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: 500;
}

.code-block {
  margin: var(--space-sm) var(--space-lg);
  border: 1px solid var(--border-medium);
  border-radius: 8px;
  overflow: auto;
  flex: 1;
  min-height: 80px;
  max-height: 200px;
  background: var(--bg-elevated);
}

.code-block pre {
  margin: 0;
  padding: var(--space-md);
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-primary);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.output-block {
  flex: 1;
  max-height: none;
}
</style>
