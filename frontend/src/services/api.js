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

function mockGetTaskDetail() {
  return Promise.resolve({ data: MOCK_TASK_DETAIL });
}

function mockGetTokenDaily() {
  return Promise.resolve({ data: MOCK_TOKEN_DAILY });
}

function mockGetCapabilityDist() {
  return Promise.resolve({ data: MOCK_CAPABILITY_DIST });
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
    USE_MOCK ? mockGetActivity(params) : api.get('/activity', { params }),
};

export default api;
