<!-- frontend/src/components/dashboard/ActivityFeed.vue -->
<!-- e-Agent-OS OpCenter — Activity Feed Timeline -->
<script setup>
const props = defineProps({
  items: { type: Array, default: () => [] },
});

const TYPE_DOT = {
  task_completed:  'var(--success)',
  task_failed:     'var(--danger)',
  shadow_pass:     'var(--warning)',
  employee_joined: 'var(--accent-primary)',
  status_changed:  '#B0AA9F',
};

function relativeTime(iso) {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1) return '刚刚';
  if (m < 60) return `${m}分钟前`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}小时前`;
  return `${Math.floor(h / 24)}天前`;
}
</script>

<template>
  <div class="activity-feed">
    <div class="feed-title">最近动态</div>
    <ul class="feed-list">
      <li
        v-for="item in items"
        :key="item.id"
        class="feed-item"
        :class="{ 'feed-item--failed': item.type === 'task_failed' }"
      >
        <span class="feed-timeline">
          <span
            class="feed-dot"
            :style="{ background: TYPE_DOT[item.type] ?? '#B0AA9F' }"
          ></span>
        </span>
        <div class="feed-body">
          <div class="feed-avatar">
            <span class="feed-alias">{{ item.alias }}</span>
            <span class="feed-role">{{ item.role }} — {{ item.dept }}</span>
          </div>
          <div class="feed-content" :class="{ 'feed-content--failed': item.type === 'task_failed' }">
            {{ item.content }}
          </div>
        </div>
        <span class="feed-time">{{ relativeTime(item.timestamp) }}</span>
      </li>
      <li v-if="!items.length" class="feed-empty">暂无动态</li>
    </ul>
  </div>
</template>

<style scoped>
.activity-feed {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  padding: 16px 18px;
  height: 100%;
}

.feed-title {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--text-disabled);
  margin-bottom: 14px;
}

.feed-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
}

.feed-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-subtle);
}
.feed-item:last-child {
  border-bottom: none;
}

.feed-timeline {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 5px;
  flex-shrink: 0;
}

.feed-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}

.feed-body {
  flex: 1;
  font-size: 13px;
  line-height: 1.7;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.feed-avatar {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.feed-alias {
  font-family: var(--font-serif);
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
}

.feed-role {
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.feed-content {
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
}
.feed-content--failed {
  color: var(--danger);
}

.feed-item--failed .feed-dot {
  box-shadow: 0 0 0 2px rgba(184, 74, 60, 0.20);
}

.feed-time {
  font-size: 10px;
  color: var(--text-disabled);
  white-space: nowrap;
  flex-shrink: 0;
  align-self: center;
  margin-left: auto;
}

.feed-empty {
  font-size: 13px;
  color: var(--text-disabled);
  text-align: center;
  padding: 24px;
}
</style>
