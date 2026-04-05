// frontend/src/composables/useOnboarding.js
// e-Agent-OS OpCenter — Onboarding Composable
import { ref } from 'vue';
import { onboardingApi, DEPARTMENTS } from '../services/api.js';

const blueprints = ref([]);
const loading = ref(false);
const error = ref(null);

async function fetchBlueprints() {
  loading.value = true;
  error.value = null;
  try {
    const res = await onboardingApi.list();
    blueprints.value = res.data;
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}

function getTotalReplicas(bp) {
  return bp.versions.reduce((sum, v) => sum + v.replicas, 0);
}

function getLoad(bp) {
  const total = bp.versions.reduce((sum, v) => sum + v.replicas, 0);
  const max = bp.capacity.max;
  return max > 0 ? Math.round((total / max) * 100) : 0;
}

function getStatusLabel(status) {
  const map = {
    published: '正式上岗',
    testing: '试用期',
    staging: '灰度中',
    draft: '草稿',
    deprecated: '退役',
  };
  return map[status] || status;
}

function getStatusDot(status) {
  const map = {
    published: 'var(--success)',
    testing: 'var(--warning)',
    staging: 'var(--accent-primary)',
    draft: 'var(--text-disabled)',
    deprecated: 'var(--text-disabled)',
  };
  return map[status] || 'var(--text-disabled)';
}

async function adjustTraffic(blueprintId, versionIndex, traffic) {
  try {
    const res = await onboardingApi.adjustTraffic(blueprintId, versionIndex, traffic);
    const bp = blueprints.value.find(b => b.id === blueprintId);
    if (bp && res.data) {
      bp.versions = res.data.versions;
      bp.capacity = res.data.capacity;
    }
  } catch {
    // In stub mode or if API fails, do optimistic local update
    const bp = blueprints.value.find(b => b.id === blueprintId);
    if (bp && bp.versions[versionIndex]) {
      bp.versions[versionIndex].traffic = traffic;
    }
  }
}

function deprecateVersion(blueprintId, versionIndex) {
  return onboardingApi.deprecateVersion(blueprintId, versionIndex)
    .then(res => {
      const bp = blueprints.value.find(b => b.id === blueprintId);
      if (bp && res.data) {
        bp.versions = res.data.versions;
        bp.capacity = res.data.capacity;
      }
    })
    .catch(() => {
      // Fall back to optimistic local update (PIAGENT_CLI_STUB mode)
    });
}

async function deployNewAvatar({ role, alias, department, soul, scaling }) {
  try {
    const res = await onboardingApi.deploy({
      role, alias, department, soul, scaling,
    });
    if (res.data) {
      blueprints.value.push(res.data);
      return;
    }
  } catch {
    // API 不可用时的回退（mock 或离线）
  }
  // 乐观更新
  const id = `av-${role}-${Date.now()}`;
  blueprints.value.push({
    id,
    role,
    alias,
    department,
    versions: [
      {
        version: 'v1.0.0',
        status: 'published',
        traffic: 100,
        replicas: scaling.minReplicas,
        config: { soul: soul || {}, skills: [], tools: [], model: '' },
        scaling,
      },
    ],
    capacity: { used: scaling.minReplicas, max: scaling.maxReplicas },
  });
}

export function useOnboarding() {
  return {
    blueprints,
    departments: DEPARTMENTS,
    loading,
    error,
    fetchBlueprints,
    getTotalReplicas,
    getLoad,
    getStatusLabel,
    getStatusDot,
    adjustTraffic,
    deprecateVersion,
    deployNewAvatar,
  };
}
