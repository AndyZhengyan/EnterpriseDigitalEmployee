<!-- frontend/src/views/JournalView.vue -->
<!-- e-Agent-OS OpCenter — 工作日记 -->
<script setup>
import { onMounted } from 'vue';
import { useJournal } from '../composables/useJournal.js';
import FilterBar from '../components/journal/FilterBar.vue';
import ExecutionCard from '../components/journal/ExecutionCard.vue';
import ExecutionDetail from '../components/journal/ExecutionDetail.vue';

const {
  executions,
  selected,
  total,
  loading,
  error,
  filters,
  roles,
  depts,
  fetchExecutions,
  selectItem,
} = useJournal();

onMounted(() => {
  fetchExecutions();
});

function handleSearch() {
  fetchExecutions();
}
</script>

<template>
  <div class="page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <h1 class="page-title">工作日记</h1>
        <p class="page-sub">操作审计 &middot; 共 {{ total }} 条记录</p>
      </div>
    </div>

    <!-- 左右分栏主体 -->
    <div class="journal-body">
      <!-- 左面板：筛选栏 + 卡片列表 -->
      <div class="left-panel">
        <FilterBar
          :filters="filters"
          :roles="roles"
          :depts="depts"
          @search="handleSearch"
        />

        <!-- 加载状态 -->
        <div v-if="loading" class="list-loading">
          <div class="spinner"></div>
          <p>加载中…</p>
        </div>

        <!-- 空状态 -->
        <div v-else-if="executions.length === 0" class="list-empty">
          <p>暂无记录</p>
        </div>

        <!-- 错误状态 -->
        <div v-else-if="error" class="list-empty">
          <p>加载失败</p>
        </div>

        <!-- 卡片列表 -->
        <div v-else class="card-list">
          <ExecutionCard
            v-for="item in executions"
            :key="item.id"
            :item="item"
            :selected="selected && selected.id === item.id"
            @select="selectItem"
          />
        </div>
      </div>

      <!-- 右面板：详情 -->
      <div class="right-panel">
        <ExecutionDetail :item="selected" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg);
  min-height: calc(100vh - 56px);
  display: flex;
  flex-direction: column;
}

.page-header {
  margin-bottom: var(--space-lg);
  flex-shrink: 0;
}

.page-title {
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 400;
  color: var(--text-primary);
  margin: 0 0 4px;
}

.page-sub {
  font-size: 13px;
  color: var(--text-disabled);
  margin: 0;
}

/* 左右分栏 */
.journal-body {
  display: flex;
  gap: var(--space-lg);
  flex: 1;
  min-height: 0;
  height: calc(100vh - 160px);
}

/* 左面板：固定 400px + 可滚动 */
.left-panel {
  width: 400px;
  flex-shrink: 0;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.card-list {
  overflow-y: auto;
  flex: 1;
}

/* 右面板：flex:1 + 可滚动 */
.right-panel {
  flex: 1;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
  overflow-y: auto;
}

/* 列表内状态 */
.list-loading,
.list-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  color: var(--text-disabled);
  font-size: 13px;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-subtle);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.list-empty {
  text-align: center;
  padding: 40px;
  color: var(--text-disabled);
  font-size: 14px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .journal-body {
    flex-direction: column;
    height: auto;
  }

  .left-panel {
    width: 100%;
    height: 400px;
  }
}
</style>
