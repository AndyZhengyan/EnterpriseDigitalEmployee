<!-- frontend/src/components/layout/TopNav.vue -->
<!-- e-Agent-OS OpCenter — Top Navigation Bar -->
<script setup>
import { useRoute } from 'vue-router';

const route = useRoute();

const navItems = [
  { label: '绩效看板', path: '/performance' },
  { label: '入职中心', path: '/onboarding' },
  { label: '赋能中心', path: '/enablement' },
  { label: '档案中心', path: '/oracle' },
  { label: '审计中心', path: '/journal' },
];

function isActive(path) {
  if (path === '/') return route.path === '/';
  return route.path.startsWith(path);
}
</script>

<template>
  <header class="topnav">
    <!-- Logo -->
    <div class="topnav-left">
      <router-link to="/" class="logo">
        <svg width="26" height="26" viewBox="0 0 26 26" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="13" cy="8" r="4.5" fill="currentColor"/>
          <path d="M4 23c0-5 4-9 9-9s9 4 9 9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        <span class="logo-text">AvatarOS</span>
        <span class="logo-sub">企业数字员工中心</span>
      </router-link>
    </div>

    <!-- Center Nav -->
    <nav class="topnav-center">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ active: isActive(item.path) }"
      >
        {{ item.label }}
      </router-link>
    </nav>

    <!-- Right User -->
    <div class="topnav-right">
      <div class="user-avatar">
        <svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
          <rect width="32" height="32" rx="16" fill="var(--accent-primary)"/>
          <circle cx="16" cy="12" r="5.5" fill="white"/>
          <path d="M6 28c0-5.5 4.5-10 10-10s10 4.5 10 10" fill="white"/>
        </svg>
      </div>
    </div>
  </header>
</template>

<style scoped>
.topnav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: var(--nav-height);
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-lg);
  z-index: 100;
}

.topnav-left {
  display: flex;
  align-items: center;
  min-width: 180px;
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  color: var(--accent-primary);
  text-decoration: none;
}

.logo-text {
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 500;
  color: var(--text-primary);
  letter-spacing: -0.3px;
}

.logo-sub {
  font-size: 10px;
  color: var(--text-disabled);
  letter-spacing: 0.03em;
  padding-left: 6px;
  border-left: 1px solid var(--border-subtle);
  margin-left: 6px;
  line-height: 1;
}

.topnav-center {
  display: flex;
  align-items: center;
  gap: var(--space-xl);
}

.nav-item {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  text-decoration: none;
  padding-bottom: 3px;
  position: relative;
  transition: color 150ms ease;
}
.nav-item:hover {
  color: var(--text-primary);
}
.nav-item.active {
  color: var(--accent-warm);
}
.nav-item.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 50%;
  transform: translateX(-50%);
  width: 60%;
  height: 2px;
  background: var(--accent-warm);
  border-radius: 1px;
}

.topnav-right {
  display: flex;
  align-items: center;
  min-width: 180px;
  justify-content: flex-end;
}

.user-avatar svg {
  width: 32px;
  height: 32px;
  display: block;
  border-radius: 50%;
}
</style>
