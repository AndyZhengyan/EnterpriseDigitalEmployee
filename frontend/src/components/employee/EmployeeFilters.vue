<!-- frontend/src/components/employee/EmployeeFilters.vue -->
<!-- e-Agent-OS OpCenter — Employee Filter Bar -->
<script setup>
import { computed } from 'vue';
import { useEmployeeStore } from '../../stores/employeeStore.js';

const store = useEmployeeStore();

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'active', label: '正式上岗' },
  { value: 'shadow', label: '试用期' },
  { value: 'sandbox', label: '沙盒态' },
  { value: 'archived', label: '退役' },
];

const hasFilters = computed(
  () => store.filterSearch || store.filterStatus || store.filterDepartment || store.filterTitle
);
</script>

<template>
  <div class="filters">
    <!-- Search -->
    <div class="search-wrap">
      <svg class="search-icon" viewBox="0 0 20 20" fill="none">
        <circle cx="9" cy="9" r="6" stroke="currentColor" stroke-width="1.5"/>
        <path d="M14 14l3.5 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      <input
        v-model="store.filterSearch"
        class="search-input"
        type="text"
        placeholder="搜索花名、工号、岗位…"
      />
    </div>

    <!-- Status Select -->
    <select v-model="store.filterStatus" class="filter-select">
      <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
        {{ opt.label }}
      </option>
    </select>

    <!-- Department Select -->
    <select v-model="store.filterDepartment" class="filter-select">
      <option value="">全部部门</option>
      <option v-for="dept in store.departments" :key="dept" :value="dept">
        {{ dept }}
      </option>
    </select>

    <!-- Title Select -->
    <select v-model="store.filterTitle" class="filter-select">
      <option value="">全部岗位</option>
      <option v-for="t in store.titles" :key="t" :value="t">
        {{ t }}
      </option>
    </select>

    <!-- Reset -->
    <button
      v-if="hasFilters"
      class="btn btn-ghost btn-sm"
      @click="store.resetFilters"
    >
      重置
    </button>

    <!-- New Employee -->
    <router-link to="/forge" class="btn btn-primary ml-auto">
      + 新员工
    </router-link>
  </div>
</template>

<style scoped>
.filters {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  flex-wrap: wrap;
  padding: var(--space-lg);
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
}

.search-wrap {
  position: relative;
  flex: 1;
  min-width: 200px;
}
.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  color: var(--text-secondary);
  pointer-events: none;
}
.search-input {
  width: 100%;
  padding: 8px 12px 8px 34px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-page);
  font-family: var(--font-sans);
  font-size: 14px;
  color: var(--text-primary);
  outline: none;
  transition: border-color 150ms;
}
.search-input:focus { border-color: var(--accent-primary); }
.search-input::placeholder { color: var(--text-disabled); }

.filter-select {
  padding: 8px 32px 8px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-page);
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath d='M2 4l4 4 4-4' stroke='%238A8279' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  font-family: var(--font-sans);
  font-size: 14px;
  color: var(--text-primary);
  cursor: pointer;
  outline: none;
  appearance: none;
  transition: border-color 150ms;
}
.filter-select:focus { border-color: var(--accent-primary); }

.ml-auto { margin-left: auto; }
.btn-sm { font-size: 13px; padding: 6px 12px; }
</style>
