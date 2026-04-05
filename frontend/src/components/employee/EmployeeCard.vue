<!-- frontend/src/components/employee/EmployeeCard.vue -->
<!-- e-Agent-OS OpCenter — Employee Card -->
<script setup>
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { PRESET_AVATARS } from '../../mock/data.js';
import EmployeeStatusBadge from './EmployeeStatusBadge.vue';

const props = defineProps({
  employee: { type: Object, required: true },
});

const router = useRouter();

const avatarSvg = computed(() => PRESET_AVATARS[props.employee.avatar] ?? PRESET_AVATARS['preset-1']);
const visibleSkills = computed(() => props.employee.skills.slice(0, 3));
const extraSkillCount = computed(() => Math.max(0, props.employee.skills.length - 3));

const workloadColor = computed(() => {
  const w = props.employee.workload;
  if (w >= 80) return 'var(--danger)';
  if (w >= 60) return 'var(--warning)';
  return 'var(--success)';
});

const workloadWidth = computed(() => `${Math.min(100, props.employee.workload)}%`);

function formatToken(n) {
  if (!n) return '0';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

function goDetail() {
  router.push({ name: 'employee-detail', params: { id: props.employee.id } });
}
</script>

<template>
  <article
    class="employee-card"
    :class="`status-${employee.status}`"
    @click="goDetail"
    role="button"
    tabindex="0"
    @keydown.enter="goDetail"
  >
    <!-- Avatar -->
    <div class="card-avatar" v-html="avatarSvg"></div>

    <!-- Identity -->
    <h3 class="card-name">{{ employee.name }}</h3>
    <p class="card-title">{{ employee.title }}</p>
    <p class="card-dept">
      {{ employee.department }}
      <EmployeeStatusBadge :status="employee.status" size="sm" />
    </p>

    <!-- Skills -->
    <div class="card-skills" v-if="visibleSkills.length">
      <span v-for="skill in visibleSkills" :key="skill" class="skill-tag">{{ skill }}</span>
      <span v-if="extraSkillCount > 0" class="skill-tag extra">+{{ extraSkillCount }}</span>
    </div>

    <!-- Workload Bar -->
    <div
      class="workload-row"
      v-if="employee.status !== 'sandbox' && employee.status !== 'archived'"
    >
      <span class="workload-label">负荷</span>
      <div class="workload-track">
        <div class="workload-fill" :style="{ width: workloadWidth, background: workloadColor }"></div>
      </div>
      <span class="workload-pct" :style="{ color: workloadColor }">{{ employee.workload }}%</span>
    </div>

    <!-- Stats -->
    <div class="card-stats">
      <div class="stat">
        <span class="stat-val">{{ formatToken(employee.tokenUsage) }}</span>
        <span class="stat-key">Token</span>
      </div>
      <div class="stat">
        <span class="stat-val">{{ employee.taskCount }}</span>
        <span class="stat-key">任务</span>
      </div>
    </div>

    <!-- Actions -->
    <div class="card-actions">
      <button class="btn btn-ghost btn-sm" @click.stop="goDetail">查看详情</button>
      <button class="btn btn-primary btn-sm" @click.stop>指派任务 →</button>
    </div>
  </article>
</template>

<style scoped>
.employee-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  padding: var(--space-lg);
  cursor: pointer;
  transition: transform 150ms ease, box-shadow 150ms ease, border-color 150ms ease;
  border: 1px solid transparent;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  outline: none;
}
.employee-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-elevated);
  border-color: var(--accent-primary);
}
.employee-card:focus-visible {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(45, 91, 123, 0.2);
}

/* Status variants */
.status-sandbox {
  border-style: dashed;
  border-color: var(--status-sandbox);
  opacity: 0.75;
}
.status-archived .card-name {
  text-decoration: line-through;
  color: var(--text-secondary);
}
.status-archived { opacity: 0.6; }

/* Avatar */
.card-avatar { width: 64px; height: 64px; }
.card-avatar :deep(svg) { width: 64px; height: 64px; border-radius: 50%; }

/* Identity */
.card-name {
  font-family: var(--font-serif);
  font-size: 20px;
  font-weight: 400;
  color: var(--text-primary);
  margin-top: var(--space-xs);
}
.card-title {
  font-size: 14px;
  color: var(--text-secondary);
}
.card-dept {
  font-size: 13px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

/* Skills */
.card-skills {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
  margin-top: var(--space-xs);
}
.skill-tag {
  font-size: 12px;
  padding: 2px 8px;
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
}
.skill-tag.extra { color: var(--accent-primary); }

/* Workload */
.workload-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-top: var(--space-sm);
}
.workload-label { font-size: 12px; color: var(--text-secondary); min-width: 24px; }
.workload-track {
  flex: 1;
  height: 4px;
  background: var(--bg-elevated);
  border-radius: 2px;
  overflow: hidden;
}
.workload-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 600ms ease;
}
.workload-pct { font-size: 12px; font-family: var(--font-mono); min-width: 34px; text-align: right; }

/* Stats */
.card-stats {
  display: flex;
  gap: var(--space-lg);
  padding: var(--space-sm) 0;
  border-top: 1px solid var(--border-subtle);
  margin-top: var(--space-xs);
}
.stat { display: flex; flex-direction: column; gap: 2px; }
.stat-val {
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: 500;
  color: var(--accent-primary);
}
.stat-key { font-size: 12px; color: var(--text-secondary); }

/* Actions */
.card-actions {
  display: flex;
  gap: var(--space-sm);
  margin-top: var(--space-xs);
}
.btn-sm { font-size: 13px; padding: 6px 12px; }
</style>
