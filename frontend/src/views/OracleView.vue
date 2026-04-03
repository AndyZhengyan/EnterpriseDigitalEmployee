<!-- frontend/src/views/OracleView.vue -->
<!-- e-Agent-OS OpCenter — 档案中心 -->
<template>
  <div class="page">
    <div class="page-placeholder">
      <p class="placeholder-title">档案中心</p>
      <p class="placeholder-sub">岗位蓝图 · 版本配方 · 进化轨迹</p>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg);
  min-height: calc(100vh - 56px);
}
.page-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  gap: var(--space-sm);
}
.placeholder-title {
  font-family: var(--font-serif);
  font-size: 28px;
  color: var(--text-primary);
}
.placeholder-sub {
  font-size: 14px;
  color: var(--text-disabled);
}
</style>
