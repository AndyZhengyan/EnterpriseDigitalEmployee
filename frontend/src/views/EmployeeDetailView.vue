<!-- frontend/src/views/EmployeeDetailView.vue -->
<!-- e-Agent-OS OpCenter — Employee Detail View -->
<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useEmployeeStore } from '../stores/employeeStore.js';
import { PRESET_AVATARS } from '../mock/data.js';
import EmployeeStatusBadge from '../components/employee/EmployeeStatusBadge.vue';

const route = useRoute();
const router = useRouter();
const store = useEmployeeStore();

const activeTab = ref('overview');

const employee = computed(() => store.getEmployee(route.params.id));
const avatarSvg = computed(() => {
  if (!employee.value) return '';
  return PRESET_AVATARS[employee.value.avatar] ?? PRESET_AVATARS['preset-1'];
});

onMounted(() => {
  if (!store.employees.length) store.fetchEmployees();
});

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' });
}

function formatToken(n) {
  if (!n && n !== 0) return '—';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

function lastActive(iso) {
  if (!iso) return '从未活跃';
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1) return '刚刚';
  if (m < 60) return `${m}分钟前`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}小时前`;
  return `${Math.floor(h / 24)}天前`;
}

const tabs = [
  { key: 'overview', label: '概览' },
  { key: 'stats', label: '运营数据' },
  { key: 'tasks', label: '历史任务' },
  { key: 'config', label: '配置' },
];
</script>

<template>
  <div class="detail-page" v-if="employee">
    <!-- Back -->
    <button class="back-btn btn btn-ghost" @click="router.push('/employees')">
      ← 返回列表
    </button>

    <!-- Profile Header -->
    <div class="profile-header card">
      <div class="profile-avatar" v-html="avatarSvg"></div>
      <div class="profile-info">
        <h1 class="profile-name serif">{{ employee.name }}</h1>
        <p class="profile-title">{{ employee.title }}</p>
        <p class="profile-dept">
          {{ employee.department }}
          <EmployeeStatusBadge :status="employee.status" />
        </p>
      </div>
      <div class="profile-meta">
        <div class="meta-item">
          <span class="meta-key">工号</span>
          <span class="meta-val">{{ employee.id }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-key">入职日期</span>
          <span class="meta-val">{{ formatDate(employee.joinedAt) }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-key">最后活跃</span>
          <span class="meta-val">{{ lastActive(employee.lastActiveAt) }}</span>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Tab: Overview -->
    <div v-if="activeTab === 'overview'" class="tab-content card">
      <div class="overview-section">
        <h3 class="section-title">技能标签</h3>
        <div class="skills-list">
          <span v-for="s in employee.skills" :key="s" class="skill-tag">{{ s }}</span>
        </div>
      </div>

      <div class="overview-section" v-if="employee.status !== 'sandbox'">
        <h3 class="section-title">本月概况</h3>
        <div class="overview-stats">
          <div class="overview-stat">
            <span class="o-val">{{ formatToken(employee.tokenUsage) }}</span>
            <span class="o-key">Token 消耗</span>
          </div>
          <div class="overview-stat">
            <span class="o-val">{{ employee.taskCount }}</span>
            <span class="o-key">完成任务</span>
          </div>
          <div class="overview-stat">
            <span class="o-val">
              {{ employee.avgResponseMs ? `${(employee.avgResponseMs / 1000).toFixed(1)}s` : '—' }}
            </span>
            <span class="o-key">平均响应</span>
          </div>
          <div class="overview-stat">
            <span class="o-val">
              {{ employee.successRate != null ? `${Math.round(employee.successRate * 100)}%` : '—' }}
            </span>
            <span class="o-key">成功率</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab: Stats -->
    <div v-if="activeTab === 'stats'" class="tab-content card">
      <p class="placeholder-text">Token 消耗趋势图表（Phase 1b 实现）</p>
    </div>

    <!-- Tab: Tasks -->
    <div v-if="activeTab === 'tasks'" class="tab-content card">
      <p class="placeholder-text">历史任务时间轴（Phase 1b 实现）</p>
    </div>

    <!-- Tab: Config -->
    <div v-if="activeTab === 'config'" class="tab-content card">
      <div class="config-row">
        <span class="config-label">当前状态</span>
        <EmployeeStatusBadge :status="employee.status" />
      </div>
      <div class="config-row">
        <span class="config-label">编辑技能</span>
        <button class="btn btn-ghost btn-sm">编辑</button>
      </div>
      <div class="config-row danger-zone" v-if="employee.status === 'archived'">
        <span class="config-label">删除员工</span>
        <button class="btn btn-sm btn-danger">删除</button>
      </div>
    </div>
  </div>

  <!-- Not found -->
  <div v-else class="not-found">
    <p>未找到该员工</p>
    <button class="btn btn-primary" @click="router.push('/employees')">返回列表</button>
  </div>
</template>

<style scoped>
.detail-page {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
  min-height: calc(100vh - 56px);
}

.back-btn { align-self: flex-start; }

.profile-header {
  display: flex;
  align-items: center;
  gap: var(--space-xl);
  flex-wrap: wrap;
  padding: var(--space-xl);
}
.profile-avatar { width: 80px; height: 80px; flex-shrink: 0; }
.profile-avatar :deep(svg) { width: 80px; height: 80px; border-radius: 50%; }
.profile-info { flex: 1; min-width: 200px; }
.profile-name {
  font-family: var(--font-serif);
  font-size: 26px;
  font-weight: 400;
  color: var(--text-primary);
}
.profile-title { font-size: 15px; color: var(--text-secondary); margin-top: 4px; }
.profile-dept {
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}
.profile-meta {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}
.meta-item { display: flex; flex-direction: column; gap: 2px; }
.meta-key {
  font-size: 11px;
  color: var(--text-disabled);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.meta-val {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--text-primary);
}

/* Tabs */
.tabs {
  display: flex;
  gap: 2px;
  border-bottom: 1px solid var(--border-subtle);
}
.tab-btn {
  padding: var(--space-sm) var(--space-md);
  border: none;
  background: none;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: color 150ms, border-color 150ms;
}
.tab-btn:hover { color: var(--text-primary); }
.tab-btn.active {
  color: var(--accent-primary);
  border-bottom-color: var(--accent-primary);
}

/* Tab Content */
.tab-content {
  padding: var(--space-xl);
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
}
.overview-section { display: flex; flex-direction: column; gap: var(--space-md); }
.section-title {
  font-family: var(--font-serif);
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
}
.skills-list { display: flex; flex-wrap: wrap; gap: var(--space-sm); }
.skill-tag {
  font-size: 13px;
  padding: 4px 10px;
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
}
.overview-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
}
@media (max-width: 600px) {
  .overview-stats { grid-template-columns: repeat(2, 1fr); }
}
.overview-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--space-md);
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
}
.o-val {
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 500;
  color: var(--accent-primary);
}
.o-key { font-size: 12px; color: var(--text-secondary); }
.placeholder-text { color: var(--text-secondary); font-size: 14px; }

/* Config */
.config-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md) 0;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 14px;
  color: var(--text-primary);
}
.config-label { color: var(--text-secondary); }
.danger-zone { color: var(--danger); }
.danger-zone .config-label { color: var(--danger); }
.btn-danger { background: var(--danger); color: white; }
.btn-sm { font-size: 13px; padding: 6px 12px; }

/* Not found */
.not-found {
  text-align: center;
  padding: var(--space-2xl);
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
}
</style>
