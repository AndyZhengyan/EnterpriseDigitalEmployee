// frontend/src/composables/useDashboard.js
// e-Agent-OS OpCenter — Dashboard Composable
import { ref } from 'vue';
import { dashboardApi } from '../services/api.js';

export function useDashboard() {
  const stats = ref(null);
  const statusDist = ref([]);
  const tokenTrend = ref([]);
  const taskTrend = ref([]);
  const activity = ref([]);
  const loading = ref(false);
  const error = ref(null);

  async function fetchAll() {
    loading.value = true;
    error.value = null;
    try {
      const [statsRes, distRes, tokenRes, taskRes, actRes] = await Promise.all([
        dashboardApi.stats(),
        dashboardApi.statusDist(),
        dashboardApi.tokenTrend(),
        dashboardApi.taskTrend(),
        dashboardApi.activity({ limit: 10 }),
      ]);
      stats.value = statsRes.data;
      statusDist.value = distRes.data;
      tokenTrend.value = tokenRes.data;
      taskTrend.value = taskRes.data;
      activity.value = actRes.data;
    } catch (e) {
      error.value = e.message;
    } finally {
      loading.value = false;
    }
  }

  return {
    stats,
    statusDist,
    tokenTrend,
    taskTrend,
    activity,
    loading,
    error,
    fetchAll,
  };
}
