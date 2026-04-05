<!-- frontend/src/views/DashboardView.vue -->
<!-- e-Agent-OS OpCenter — 绩效看板 -->
<script setup>
import { onMounted } from 'vue';
import { useDashboard } from '../composables/useDashboard.js';
import StatsCard from '../components/dashboard/StatsCard.vue';
import StatusDonut from '../components/dashboard/StatusDonut.vue';
import TaskChart from '../components/dashboard/TaskChart.vue';
import TaskTrend from '../components/dashboard/TaskTrend.vue';
import CapabilityChart from '../components/dashboard/CapabilityChart.vue';
import ActivityFeed from '../components/dashboard/ActivityFeed.vue';

const {
  stats,
  statusDist,
  tokenTrend,
  taskTrend,
  taskDetail,
  tokenDaily,
  capabilityDist,
  activity,
  loading,
  error,
  fetchAll,
} = useDashboard();

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
      <!-- Stats Row — 4 张扁平卡片 -->
      <section class="stats-row">
        <StatsCard
          label="活跃 Avatar"
          :value="stats.onlineCount"
          sub="正式上岗"
          type="number"
        />
        <StatsCard
          label="任务完成"
          :value="stats.monthlyTasks"
          :trend="stats.taskTrend.change"
          :trend-dir="stats.taskTrend.direction"
          type="number"
        />
        <StatsCard
          label="任务成功率"
          :value="stats.taskSuccessRate"
          :trend="stats.successRateChange"
          trend-dir="up"
          type="percent"
        />
        <StatsCard
          label="Token 效率"
          :value="stats.tokenEfficiency"
          :trend="stats.tokenTrendChange"
          trend-dir="down"
          type="efficiency"
        />
      </section>

      <!-- Middle Row：环形图（50%）+ 双柱图（50%） -->
      <section class="middle-row">
        <div class="col-left">
          <StatusDonut :data="statusDist" />
        </div>
        <div class="col-right">
          <TaskChart :task-data="tokenTrend" :token-data="tokenDaily" />
        </div>
      </section>

      <!-- Bottom Row：能力分布（35%）+ 动态流（65%） -->
      <section class="bottom-row">
        <div class="col-left">
          <CapabilityChart :data="capabilityDist" />
        </div>
        <div class="col-right">
          <ActivityFeed :items="activity" />
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
  gap: 24px;
  min-height: calc(100vh - 56px);
}

/* Stats row */
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

/* Middle row：各 50% */
.middle-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  align-items: stretch;
}
@media (max-width: 900px) {
  .middle-row { grid-template-columns: 1fr; }
}

/* Bottom row：能力分布 35% / 动态流 65% */
.bottom-row {
  display: grid;
  grid-template-columns: 35fr 65fr;
  gap: 24px;
  align-items: stretch;
}
@media (max-width: 900px) {
  .bottom-row { grid-template-columns: 1fr; }
}

.col-left,
.col-right {
  display: flex;
  flex-direction: column;
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
