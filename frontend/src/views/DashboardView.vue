<!-- frontend/src/views/DashboardView.vue -->
<!-- e-Agent-OS OpCenter — Dashboard / Command Center View -->
<script setup>
import { onMounted } from 'vue';
import { useDashboard } from '../composables/useDashboard.js';
import StatsCard from '../components/dashboard/StatsCard.vue';
import StatusDonut from '../components/dashboard/StatusDonut.vue';
import TokenChart from '../components/dashboard/TokenChart.vue';
import TaskTrend from '../components/dashboard/TaskTrend.vue';
import ActivityFeed from '../components/dashboard/ActivityFeed.vue';

const { stats, statusDist, tokenTrend, taskTrend, activity, loading, error, fetchAll } = useDashboard();

onMounted(fetchAll);
</script>

<template>
  <div class="dashboard">
    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中…</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-state">
      <p>加载失败：{{ error }}</p>
      <button class="btn btn-primary" @click="fetchAll">重试</button>
    </div>

    <!-- Content -->
    <template v-else-if="stats">
      <!-- Stats Row -->
      <section class="stats-row">
        <StatsCard
          label="在线员工"
          :value="stats.onlineCount"
          sub="正式上岗"
          type="number"
        />
        <StatsCard
          label="本月 Token 消耗"
          :value="stats.totalTokenUsage"
          type="number"
        />
        <StatsCard
          label="本月完成任务"
          :value="stats.monthlyTasks"
          :trend="stats.taskTrend.change"
          :trend-dir="stats.taskTrend.direction"
          type="number"
        />
        <StatsCard
          label="系统负载"
          :value="stats.systemLoad"
          type="load"
          :load-value="stats.systemLoad"
        />
      </section>

      <!-- Charts Row -->
      <section class="charts-row">
        <div class="donut-col">
          <StatusDonut :data="statusDist" />
        </div>
        <div class="charts-pair">
          <TokenChart :data="tokenTrend" />
          <TaskTrend :data="taskTrend" />
        </div>
      </section>

      <!-- Activity -->
      <section class="activity-row">
        <ActivityFeed :items="activity" />
      </section>
    </template>
  </div>
</template>

<style scoped>
.dashboard {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
  min-height: calc(100vh - 56px);
}

/* Stats grid: 4 columns desktop, 2 tablet, 1 mobile */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
}
@media (max-width: 900px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 500px) {
  .stats-row { grid-template-columns: 1fr; }
}

/* Charts row: donut left, charts right */
.charts-row {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: var(--space-md);
  align-items: start;
}
@media (max-width: 900px) {
  .charts-row { grid-template-columns: 1fr; }
}
.charts-row .donut-col {
  width: 100%;
  box-sizing: border-box;
}

.charts-pair {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-md);
}
@media (max-width: 700px) {
  .charts-pair { grid-template-columns: 1fr; }
}

/* Loading / Error */
.loading-state,
.error-state {
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
