<!-- frontend/src/components/journal/FilterBar.vue -->
<!-- e-Agent-OS OpCenter — Journal Filter Bar -->
<script setup>
const props = defineProps({
  filters: {
    type: Object,
    required: true,
  },
  roles: {
    type: Array,
    required: true,
  },
  depts: {
    type: Array,
    required: true,
  },
});

const emit = defineEmits(['search']);

const STATUS_OPTIONS = [
  { label: '全部', value: 'all' },
  { label: '成功', value: 'ok' },
  { label: '失败', value: 'error' },
];

function emitSearch() {
  emit('search', props.filters);
}
</script>

<template>
  <div class="filter-bar">
    <!-- 第一行：状态 + 角色 + 部门 -->
    <div class="filter-row">
      <!-- 状态 -->
      <div class="filter-group">
        <label class="filter-label">状态</label>
        <select class="filter-select" v-model="filters.status" @change="emitSearch">
          <option v-for="opt in STATUS_OPTIONS" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </div>

      <!-- 角色 -->
      <div class="filter-group">
        <label class="filter-label">角色</label>
        <select class="filter-select" v-model="filters.role" @change="emitSearch">
          <option value="all">全部</option>
          <option v-for="r in (roles || [])" :key="r" :value="r">{{ r }}</option>
        </select>
      </div>

      <!-- 部门 -->
      <div class="filter-group">
        <label class="filter-label">部门</label>
        <select class="filter-select" v-model="filters.dept" @change="emitSearch">
          <option value="all">全部</option>
          <option v-for="d in (depts || [])" :key="d" :value="d">{{ d }}</option>
        </select>
      </div>
    </div>

    <!-- 第二行：搜索框 + 搜索按钮 -->
    <div class="filter-row search-row">
      <input
        class="filter-input"
        type="text"
        placeholder="搜索输入 / 输出关键词..."
        v-model="filters.q"
        @keyup.enter="emitSearch"
      />
      <button class="btn btn-primary" @click="emitSearch">搜索</button>
    </div>
  </div>
</template>

<style scoped>
.filter-bar {
  padding: var(--space-md);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  flex-shrink: 0;
}

.filter-row {
  display: flex;
  gap: var(--space-sm);
  align-items: center;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 120px;
}

.filter-label {
  font-size: 11px;
  color: var(--text-disabled);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: 500;
}

.filter-select {
  padding: 4px var(--space-sm);
  border: 1px solid var(--border-medium);
  border-radius: 6px;
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 13px;
  font-family: var(--font-sans);
  cursor: pointer;
  outline: none;
  transition: border-color 0.15s;
}

.filter-select:focus {
  border-color: var(--accent-primary);
}

.search-row {
  flex: 1;
}

.filter-input {
  flex: 1;
  padding: 6px var(--space-sm);
  border: 1px solid var(--border-medium);
  border-radius: 6px;
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 13px;
  font-family: var(--font-sans);
  outline: none;
  transition: border-color 0.15s;
}

.filter-input:focus {
  border-color: var(--accent-primary);
}

.filter-input::placeholder {
  color: var(--text-disabled);
}
</style>
