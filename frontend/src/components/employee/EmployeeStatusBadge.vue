<!-- frontend/src/components/employee/EmployeeStatusBadge.vue -->
<!-- e-Agent-OS OpCenter — Employee Status Badge -->
<script setup>
const props = defineProps({
  status: {
    type: String,
    required: true,
    // 'sandbox' | 'shadow' | 'active' | 'archived'
  },
  size: { type: String, default: 'md' }, // 'sm' | 'md'
});

const STATUS_CONFIG = {
  sandbox:  { label: '沙盒态',  color: 'var(--status-sandbox)',  badge: false },
  shadow:   { label: '试用期',  color: 'var(--status-shadow)',   badge: true  },
  active:   { label: '正式上岗', color: 'var(--status-active)',  badge: false },
  archived: { label: '退役',    color: 'var(--status-archived)', badge: false },
};

const config = $derived(STATUS_CONFIG[props.status] ?? STATUS_CONFIG.sandbox);
</script>

<template>
  <span class="status-badge" :class="`size-${size}`">
    <span class="dot" :style="{ background: config.color }"></span>
    <span class="label" :style="{ color: config.color }">{{ config.label }}</span>
    <span v-if="config.badge" class="badge-tag">试</span>
  </span>
</template>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.label {
  font-size: 13px;
  font-weight: 500;
}
.size-sm .label {
  font-size: 12px;
}
.badge-tag {
  font-size: 10px;
  font-weight: 600;
  color: white;
  padding: 1px 5px;
  border-radius: 3px;
  letter-spacing: 0.5px;
  background: var(--status-shadow);
}
</style>
