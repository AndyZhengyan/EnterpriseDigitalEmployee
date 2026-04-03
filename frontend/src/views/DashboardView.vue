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
      <!-- Stats Row — flat, compressed cards -->
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

      <!-- Middle Row: donut (1 part) + token chart (2 parts) -->
      <section class="middle-row">
        <div class="donut-col">
          <StatusDonut :data="statusDist" />
        </div>
        <div class="token-col">
          <TokenChart :data="tokenTrend" />
        </div>
      </section>

      <!-- Bottom Row: activity (65%) + task trend (35%) -->
      <section class="bottom-row">
        <div class="activity-col">
          <ActivityFeed :items="activity" />
        </div>
        <div class="trend-col">
          <TaskTrend :data="taskTrend" />
        </div>
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
  gap: 24px; /* unified gap */
  min-height: calc(100vh - 56px);
}

/* Stats row: flat cards, 4 columns */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}
@media (max-width: 900px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 500px) {
  .stats-row { grid-template-columns: 1fr; }
}

/* Middle row: donut (1) + token chart (2) = 1:2 ratio */
.middle-row {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 24px;
  align-items: stretch;
}
@media (max-width: 900px) {
  .middle-row { grid-template-columns: 1fr; }
}

/* Bottom row: activity (65%) + trend (35%) */
.bottom-row {
  display: grid;
  grid-template-columns: 65fr 35fr;
  gap: 24px;
  align-items: stretch;
}
@media (max-width: 900px) {
  .bottom-row { grid-template-columns: 1fr; }
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
  border: 2px solid var(--border-subtle);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
