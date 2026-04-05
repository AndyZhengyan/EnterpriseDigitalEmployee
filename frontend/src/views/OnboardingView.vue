<!-- frontend/src/views/OnboardingView.vue -->
<!-- e-Agent-OS OpCenter — 入职中心 -->
<script setup>
import { ref } from 'vue';
import { useOnboarding } from '../composables/useOnboarding.js';
import AvatarCard from '../components/onboarding/AvatarCard.vue';
import DeployModal from '../components/onboarding/DeployModal.vue';

const {
  blueprints,
  departments,
  deployNewAvatar,
} = useOnboarding();

const showModal = ref(false);

function handleDeploy(payload) {
  deployNewAvatar(payload);
}

function handleDeployVersion(bp) {
  // 暂不实现，弹窗留空
}
</script>

<template>
  <div class="page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <h1 class="page-title">入职中心</h1>
        <p class="page-sub">Avatar 实例化与管理</p>
      </div>
      <button class="btn btn-primary" @click="showModal = true">
        + 部署新 Avatar
      </button>
    </div>

    <!-- Blueprint 卡片列表 -->
    <div class="card-grid">
      <AvatarCard
        v-for="bp in blueprints"
        :key="bp.id"
        :blueprint="bp"
        @deploy-version="handleDeployVersion"
      />
    </div>

    <!-- 部署弹窗 -->
    <Teleport to="body">
      <DeployModal
        v-if="showModal"
        :blueprints="blueprints"
        :departments="departments"
        @close="showModal = false"
        @deploy="handleDeploy"
      />
    </Teleport>
  </div>
</template>

<style scoped>
.page {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg);
  min-height: calc(100vh - 56px);
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--space-xl);
}

.page-title {
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 400;
  color: var(--text-primary);
  margin: 0 0 4px;
}

.page-sub {
  font-size: 13px;
  color: var(--text-disabled);
  margin: 0;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 20px;
}

@media (max-width: 600px) {
  .card-grid { grid-template-columns: 1fr; }
}
</style>
