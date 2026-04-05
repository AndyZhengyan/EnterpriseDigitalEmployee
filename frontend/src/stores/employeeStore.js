// frontend/src/stores/employeeStore.js
// e-Agent-OS OpCenter — Employee Pinia Store
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { employeeApi } from '../services/api.js';

export const useEmployeeStore = defineStore('employees', () => {
  // State
  const employees = ref([]);
  const loading = ref(false);
  const error = ref(null);

  // Filters
  const filterStatus = ref('');
  const filterDepartment = ref('');
  const filterTitle = ref('');
  const filterSearch = ref('');

  // Computed
  const filteredEmployees = computed(() => {
    let result = employees.value;
    if (filterStatus.value) result = result.filter(e => e.status === filterStatus.value);
    if (filterDepartment.value) result = result.filter(e => e.department === filterDepartment.value);
    if (filterTitle.value) result = result.filter(e => e.title === filterTitle.value);
    if (filterSearch.value) {
      const q = filterSearch.value.toLowerCase();
      result = result.filter(
        e =>
          e.name.toLowerCase().includes(q) ||
          e.id.toLowerCase().includes(q) ||
          e.title.toLowerCase().includes(q),
      );
    }
    return result;
  });

  const departments = computed(() =>
    [...new Set(employees.value.map(e => e.department))].sort()
  );

  const titles = computed(() =>
    [...new Set(employees.value.map(e => e.title))].sort()
  );

  // Actions
  async function fetchEmployees() {
    loading.value = true;
    error.value = null;
    try {
      const res = await employeeApi.list();
      employees.value = res.data;
    } catch (e) {
      error.value = e.message;
    } finally {
      loading.value = false;
    }
  }

  function getEmployee(id) {
    return employees.value.find(e => e.id === id) ?? null;
  }

  function resetFilters() {
    filterStatus.value = '';
    filterDepartment.value = '';
    filterTitle.value = '';
    filterSearch.value = '';
  }

  return {
    employees,
    filteredEmployees,
    departments,
    titles,
    loading,
    error,
    filterStatus,
    filterDepartment,
    filterTitle,
    filterSearch,
    fetchEmployees,
    getEmployee,
    resetFilters,
  };
});
