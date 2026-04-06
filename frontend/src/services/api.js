// frontend/src/services/api.js
// e-Agent-OS OpCenter — API Service Layer
import axios from 'axios';
import {
  MOCK_EMPLOYEES,
  MOCK_DASHBOARD_STATS,
  MOCK_STATUS_DIST,
  MOCK_TOKEN_TREND,
  MOCK_TASK_TREND,
  MOCK_ACTIVITY,
} from '../mock/data.js';
import {
  MOCK_BLUEPRINTS,
  DEPARTMENTS,
} from '../mock/blueprints.js';

const USE_MOCK = true; // flip to false when connecting to real backend

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

function mockGetBlueprints() {
  return Promise.resolve({ data: MOCK_BLUEPRINTS });
}

function mockDeploy(payload) {
  const id = `av-${payload.role}-${Date.now()}`;
  return Promise.resolve({
    data: {
      id,
      role: payload.role,
      alias: payload.alias || payload.role,
      department: payload.department,
      versions: [
        {
          version: 'v1.0.0',
          status: 'published',
          traffic: 100,
          replicas: payload.scaling?.minReplicas ?? 1,
          config: { soul: payload.soul || {}, skills: [], tools: [], model: '' },
          scaling: payload.scaling || { minReplicas: 1, maxReplicas: 5, targetLoad: 70 },
        },
      ],
      capacity: {
        used: payload.scaling?.minReplicas ?? 1,
        max: payload.scaling?.maxReplicas ?? 5,
      },
    },
  });
}

function mockAdjustTraffic(blueprintId, versionIndex, traffic) {
  return Promise.resolve({
    data: { blueprintId, versionIndex, traffic },
  });
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
  activity: (params) =>
    USE_MOCK ? mockGetActivity(params) : api.get('/activity', { params }),
};

export const opsApi = {
  execute: (payload) =>
    USE_MOCK
      ? Promise.resolve({
          data: {
            status: 'ok',
            summary: 'mock',
            tokenTotal: 100,
            durationMs: 2000,
          },
        })
      : api.post('/ops/execute', payload),
};

export const onboardingApi = {
  list: () =>
    USE_MOCK ? mockGetBlueprints() : api.get('/onboarding/blueprints'),
  deploy: (payload) =>
    USE_MOCK ? mockDeploy(payload) : api.post('/onboarding/deploy', payload),
  adjustTraffic: (blueprintId, versionIndex, traffic) =>
    USE_MOCK
      ? mockAdjustTraffic(blueprintId, versionIndex, traffic)
      : api.put(`/onboarding/blueprints/${blueprintId}/traffic`, {
          versionIndex,
          traffic,
        }),
  deprecateVersion: (blueprintId, versionIndex) =>
    api.put(`/onboarding/blueprints/${blueprintId}/deprecate`, {
      versionIndex,
    }),
};

export { DEPARTMENTS };
export default api;
