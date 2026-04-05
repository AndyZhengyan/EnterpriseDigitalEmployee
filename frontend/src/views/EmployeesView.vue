<!-- frontend/src/views/EmployeesView.vue -->
<!-- e-Agent-OS OpCenter — Employee Gallery View -->
<script setup>
import { onMounted } from 'vue';
import { useEmployeeStore } from '../stores/employeeStore.js';
import EmployeeCard from '../components/employee/EmployeeCard.vue';
import EmployeeFilters from '../components/employee/EmployeeFilters.vue';

const store = useEmployeeStore();
onMounted(() => store.fetchEmployees());
</script>

<template>
  <div class="employees-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">数字员工</h1>
        <span class="page-count">{{ store.filteredEmployees.length }} 位</span>
      </div>
    </div>

    <!-- Filters -->
    <EmployeeFilters />

    <!-- Loading -->
    <div v-if="store.loading" class="loading-state">
      <div class="spinner"></div>
    </div>

    <!-- Grid -->
    <div v-else-if="store.filteredEmployees.length" class="employee-grid">
      <EmployeeCard
        v-for="emp in store.filteredEmployees"
        :key="emp.id"
        :employee="emp"
      />
    </div>

    <!-- Empty -->
    <div v-else class="empty-state">
      <p>没有符合条件的员工</p>
      <button class="btn btn-ghost" @click="store.resetFilters">清除筛选</button>
    </div>
  </div>
</template>

<style scoped>
.employees-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
  min-height: calc(100vh - 56px);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
}
.header-left {
  display: flex;
  align-items: baseline;
  gap: var(--space-md);
}
.page-title {
  font-family: var(--font-serif);
  font-size: 28px;
  color: var(--text-primary);
}
.page-count {
  font-size: 14px;
  color: var(--text-secondary);
}

.employee-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-md);
}

.loading-state,
.empty-state {
  text-align: center;
  padding: var(--space-2xl);
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
}
.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-subtle);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
