// frontend/src/composables/useDashboard.js
// e-Agent-OS OpCenter — Dashboard Composable
import { ref } from 'vue';
import { dashboardApi } from '../services/api.js';

export function useDashboard() {
  const stats = ref(null);
  const statusDist = ref([]);
  const tokenTrend = ref([]);
  const taskTrend = ref([]);
  const taskDetail = ref(null);
  const tokenDaily = ref([]);
  const capabilityDist = ref([]);
  const activity = ref([]);
  const loading = ref(false);
  const error = ref(null);

  async function fetchAll() {
    loading.value = true;
    error.value = null;
    try {
      const [statsRes, distRes, tokenRes, taskRes, taskDetailRes, tokenDailyRes, capRes, actRes] =
        await Promise.all([
          dashboardApi.stats(),
          dashboardApi.statusDist(),
          dashboardApi.tokenTrend(),
          dashboardApi.taskTrend(),
          dashboardApi.taskDetail(),
          dashboardApi.tokenDaily(),
          dashboardApi.capabilityDist(),
          dashboardApi.activity({ limit: 10 }),
        ]);
      stats.value = statsRes.data;
      statusDist.value = distRes.data;
      tokenTrend.value = tokenRes.data;
      taskTrend.value = taskRes.data;
      taskDetail.value = taskDetailRes.data;
      tokenDaily.value = tokenDailyRes.data;
      capabilityDist.value = capRes.data;
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
    taskDetail,
    tokenDaily,
    capabilityDist,
    activity,
    loading,
    error,
    fetchAll,
  };
}
