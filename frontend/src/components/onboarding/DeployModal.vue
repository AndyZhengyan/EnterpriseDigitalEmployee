<!-- frontend/src/components/onboarding/DeployModal.vue -->
<!-- e-Agent-OS OpCenter — 部署新 Avatar 弹窗 -->
<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  blueprints: { type: Array, required: true },
  departments: { type: Array, required: true },
});

const emit = defineEmits(['close', 'deploy']);

const selectedRole = ref(props.blueprints[0]?.role || '');
const alias = ref('');
const department = ref(props.departments[0] || '');
const soulDescription = ref('');
const soulCommunicationStyle = ref('');
const minReplicas = ref(1);
const maxReplicas = ref(5);
const targetLoad = ref(60);

const selectedBlueprint = computed(() =>
  props.blueprints.find(b => b.role === selectedRole.value)
);

const defaultAlias = computed(() => selectedBlueprint.value?.alias || '');

function handleDeploy() {
  if (!selectedRole.value) return;
  emit('deploy', {
    role: selectedRole.value,
    alias: alias.value || defaultAlias.value,
    department: department.value,
    soul: {
      description: soulDescription.value || '',
      communication_style: soulCommunicationStyle.value || '',
    },
    scaling: {
      minReplicas: minReplicas.value,
      maxReplicas: maxReplicas.value,
      targetLoad: targetLoad.value,
    },
  });
  emit('close');
}
</script>

<template>
  <div class="modal-backdrop" @click.self="$emit('close')">
    <div class="modal">
      <!-- Header -->
      <div class="modal-header">
        <span class="modal-title">部署新 Avatar</span>
        <button class="modal-close" @click="$emit('close')">×</button>
      </div>

      <!-- Body -->
      <div class="modal-body">
        <div class="field">
          <label class="field-label">岗位</label>
          <select v-model="selectedRole" class="field-select">
            <option v-for="bp in blueprints" :key="bp.id" :value="bp.role">
              {{ bp.role }}
            </option>
          </select>
        </div>

        <div class="field">
          <label class="field-label">艺名</label>
          <div class="field-input-wrap">
            <input
              v-model="alias"
              class="field-input"
              :placeholder="`默认：「${defaultAlias}」`"
            />
          </div>
        </div>

        <div class="field">
          <label class="field-label">部门</label>
          <select v-model="department" class="field-select">
            <option v-for="d in departments" :key="d" :value="d">{{ d }}</option>
          </select>
        </div>

        <!-- 人格设定 -->
        <div class="field-group">
          <div class="field-group-label">
            <span>人格设定</span>
          </div>

          <div class="field">
            <label class="field-label">角色灵魂描述</label>
            <input
              v-model="soulDescription"
              class="field-input"
              placeholder="如：热情友好，专业细致"
            />
          </div>

          <div class="field">
            <label class="field-label">沟通风格</label>
            <input
              v-model="soulCommunicationStyle"
              class="field-input"
              placeholder="如：亲切简洁，条理分明"
            />
          </div>
        </div>

        <!-- 分身策略 -->
        <div class="field-group">
          <div class="field-group-label">
            <span>分身策略</span>
            <span class="field-group-hint">系统根据负载自动扩缩</span>
          </div>

          <div class="scaling-grid">
            <div class="scaling-item">
              <label class="scaling-label">最小分身</label>
              <div class="scaling-btn-group">
                <button
                  v-for="n in [1, 2, 3]"
                  :key="n"
                  class="scaling-btn"
                  :class="{ active: minReplicas === n }"
                  @click="minReplicas = n"
                >{{ n }}</button>
              </div>
            </div>

            <div class="scaling-item">
              <label class="scaling-label">最大分身</label>
              <div class="scaling-btn-group">
                <button
                  v-for="n in [3, 5, 10]"
                  :key="n"
                  class="scaling-btn"
                  :class="{ active: maxReplicas === n }"
                  @click="maxReplicas = n"
                >{{ n }}</button>
              </div>
            </div>

            <div class="scaling-item">
              <label class="scaling-label">期望负载</label>
              <div class="scaling-slider-wrap">
                <input
                  type="range"
                  v-model.number="targetLoad"
                  min="30"
                  max="90"
                  step="10"
                  class="scaling-slider"
                />
                <span class="scaling-slider-val">{{ targetLoad }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="modal-footer">
        <button class="btn btn-ghost" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" @click="handleDeploy">激活 Avatar</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(44, 42, 40, 0.30);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  backdrop-filter: blur(2px);
}

.modal {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-modal);
  width: 420px;
  max-width: 90vw;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px 12px;
  border-bottom: 1px solid var(--border-subtle);
}

.modal-title {
  font-family: var(--font-serif);
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
}

.modal-close {
  font-size: 20px;
  color: var(--text-disabled);
  background: none;
  border: none;
  cursor: pointer;
  line-height: 1;
  padding: 0 4px;
}
.modal-close:hover { color: var(--text-primary); }

.modal-body {
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-disabled);
}

.field-input,
.field-select {
  width: 100%;
  padding: 8px 10px;
  font-family: var(--font-sans);
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-page);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  outline: none;
  transition: border-color 150ms;
  appearance: none;
}
.field-input:focus,
.field-select:focus {
  border-color: var(--accent-primary);
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-group-label {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.field-group-label > span:first-child {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-disabled);
}
.field-group-hint {
  font-size: 11px;
  color: var(--text-disabled);
}

.scaling-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--bg-page);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 12px;
}

.scaling-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.scaling-label {
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 56px;
}

.scaling-btn-group {
  display: flex;
  gap: 4px;
}

.scaling-btn {
  padding: 4px 10px;
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--text-secondary);
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 120ms;
}
.scaling-btn:hover {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}
.scaling-btn.active {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: #fff;
}

.scaling-slider-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.scaling-slider {
  flex: 1;
  height: 3px;
  accent-color: var(--accent-primary);
  cursor: pointer;
}

.scaling-slider-val {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 32px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 18px 16px;
  border-top: 1px solid var(--border-subtle);
}
</style>
