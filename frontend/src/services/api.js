// frontend/src/services/api.js
// e-Agent-OS OpCenter — API Service Layer
import axios from 'axios';
import {
  MOCK_EMPLOYEES,
  MOCK_DASHBOARD_STATS,
  MOCK_STATUS_DIST,
  MOCK_TOKEN_TREND,
  MOCK_TASK_TREND,
  MOCK_TASK_DETAIL,
  MOCK_TOKEN_DAILY,
  MOCK_CAPABILITY_DIST,
  MOCK_ACTIVITY,
} from '../mock/data.js';
import { MOCK_BLUEPRINTS, DEPARTMENTS } from '../mock/blueprints.js';

const USE_MOCK = false; // 切换为真实后端

const api = axios.create({
  baseURL: '/api',
  timeout: 5000,
});

// ---- Mock Implementations ----

function mockGetEmployees({ status, department, title, search } = {}) {
  let result = [...MOCK_EMPLOYEES];
  if (status) result = result.filter(e => e.status === status);
  if (department) result = result.filter(e => e.department === department);
  if (title) result = result.filter(e => e.title === title);
  if (search) {
    const q = search.toLowerCase();
    result = result.filter(
      e =>
        e.name.toLowerCase().includes(q) ||
        e.id.toLowerCase().includes(q) ||
        e.title.toLowerCase().includes(q),
    );
  }
  return Promise.resolve({ data: result });
}

function mockGetEmployee(id) {
  const emp = MOCK_EMPLOYEES.find(e => e.id === id);
  if (!emp) return Promise.reject({ response: { status: 404 } });
  return Promise.resolve({ data: emp });
}

function mockGetDashboardStats() {
  return Promise.resolve({ data: MOCK_DASHBOARD_STATS });
}

function mockGetStatusDist() {
  return Promise.resolve({ data: MOCK_STATUS_DIST });
}

function mockGetTokenTrend() {
  return Promise.resolve({ data: MOCK_TOKEN_TREND });
}

function mockGetTaskTrend() {
  return Promise.resolve({ data: MOCK_TASK_TREND });
}

function mockGetActivity({ limit = 10 } = {}) {
  return Promise.resolve({ data: MOCK_ACTIVITY.slice(0, limit) });
}

function mockGetTaskDetail() {
  return Promise.resolve({ data: MOCK_TASK_DETAIL });
}

function mockGetTokenDaily() {
  return Promise.resolve({ data: MOCK_TOKEN_DAILY });
}

function mockGetCapabilityDist() {
  return Promise.resolve({ data: MOCK_CAPABILITY_DIST });
}

function mockGetBlueprints() {
  return Promise.resolve({ data: [...MOCK_BLUEPRINTS] });
}

// ---- Public API Functions ----

export const employeeApi = {
  list: (params) =>
    USE_MOCK ? mockGetEmployees(params) : api.get('/employees', { params }),
  get: (id) =>
    USE_MOCK ? mockGetEmployee(id) : api.get(`/employees/${id}`),
};

export const dashboardApi = {
  stats: () =>
    USE_MOCK ? mockGetDashboardStats() : api.get('/dashboard/stats'),
  statusDist: () =>
    USE_MOCK ? mockGetStatusDist() : api.get('/dashboard/status-dist'),
  tokenTrend: () =>
    USE_MOCK ? mockGetTokenTrend() : api.get('/dashboard/token-trend'),
  taskTrend: () =>
    USE_MOCK ? mockGetTaskTrend() : api.get('/dashboard/task-trend'),
  taskDetail: () =>
    USE_MOCK ? mockGetTaskDetail() : api.get('/dashboard/task-detail'),
  tokenDaily: () =>
    USE_MOCK ? mockGetTokenDaily() : api.get('/dashboard/token-daily'),
  capabilityDist: () =>
    USE_MOCK ? mockGetCapabilityDist() : api.get('/dashboard/capability-dist'),
  activity: (params) =>
    USE_MOCK ? mockGetActivity(params) : api.get('/dashboard/activity', { params }),
};

export const onboardingApi = {
  list: () =>
    USE_MOCK ? mockGetBlueprints() : api.get('/onboarding/blueprints'),
  deploy: (payload) =>
    USE_MOCK ? Promise.resolve({ data: null }) : api.post('/onboarding/deploy', payload),
  // Phase 2 新增：
  adjustTraffic: (blueprintId, versionIndex, traffic) =>
    api.put(`/onboarding/blueprints/${blueprintId}/traffic`, {
      version_index: versionIndex,
      traffic,
    }),
  deprecateVersion: (blueprintId, versionIndex) =>
    api.put(`/onboarding/blueprints/${blueprintId}/versions/${versionIndex}/deprecate`),
  deleteBlueprint: (blueprintId) =>
    api.delete(`/onboarding/blueprints/${blueprintId}`),
};

export const opsApi = {
  execute: (payload) =>
    USE_MOCK ? Promise.resolve({ data: { status: 'ok', summary: 'mock', tokenTotal: 100, durationMs: 2000 } })
      : api.post('/ops/execute', payload),
};

export { DEPARTMENTS };
export default api;
