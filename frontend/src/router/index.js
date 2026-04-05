// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router';
import DashboardView from '../views/DashboardView.vue';
import OnboardingView from '../views/OnboardingView.vue';
import EnablementView from '../views/EnablementView.vue';
import OracleView from '../views/OracleView.vue';
import JournalView from '../views/JournalView.vue';
import EmployeesView from '../views/EmployeesView.vue';
import EmployeeDetailView from '../views/EmployeeDetailView.vue';

const routes = [
  { path: '/', redirect: '/performance' },
  { path: '/performance', name: 'dashboard', component: DashboardView },
  { path: '/onboarding', name: 'onboarding', component: OnboardingView },
  { path: '/enablement', name: 'enablement', component: EnablementView },
  { path: '/oracle', name: 'oracle', component: OracleView },
  { path: '/journal', name: 'journal', component: JournalView },
  { path: '/employees', name: 'employees', component: EmployeesView },
  { path: '/employees/:id', name: 'employee-detail', component: EmployeeDetailView },
];

export default createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
});
