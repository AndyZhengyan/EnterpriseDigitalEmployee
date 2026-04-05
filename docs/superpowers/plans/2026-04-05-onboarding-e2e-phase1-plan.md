# Onboarding E2E 测试 Phase 1 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为入职中心页面建立 Playwright E2E 测试体系，跑通已实现的 4 个核心功能（加载列表、部署新 Avatar、部署新版本、任务执行），Vue bug 同步修复。

**Architecture:** 前端用 `USE_MOCK=true`，Playwright 直接访问 `vite dev server`，无需启动后端。测试用例用 Playwright TypeScript 写，放在 `frontend/tests/e2e/`。

**Tech Stack:** Playwright (TypeScript)、Vite dev server、Vue 3 (mock mode)

---

## 文件变更概览

| 操作 | 文件 |
|------|------|
| 修改 | `frontend/src/components/onboarding/AvatarCard.vue` — 修复 $index bug |
| 创建 | `frontend/playwright.config.ts` — Playwright 配置 |
| 创建 | `frontend/tests/e2e/onboarding.spec.ts` — E2E 测试用例 |
| 创建 | `frontend/tests/e2e/page-objects/onboarding.page.ts` — Page Object |
| 修改 | `frontend/package.json` — 添加 Playwright dev 依赖 |

---

## Task 1: 修复 Vue $index Bug

**文件:** `frontend/src/components/onboarding/AvatarCard.vue`

当前问题：`adjustingIndices` 是 `ref(new Set())`，`deprecatingIndices` 是 `ref(new Set())`，但模板中用 `!adjustingIndices.has($index)` 判断时 Vue 响应式追踪失败，导致所有行同时显示编辑状态。

根因：`adjustingIndices.value` 是 Set，在模板中直接调用 `.has()` Vue 无法建立依赖追踪。

修复方案：用两个独立的 `ref<number | null>` 替代 Set，每次只允许一个索引进入编辑状态。

- [ ] **Step 1: 查看当前 AvatarCard.vue script setup 部分**

确认当前 `adjustingIndices` 和 `deprecatingIndices` 的定义方式。

- [ ] **Step 2: 替换为两个独立的 nullable number ref**

修改 `frontend/src/components/onboarding/AvatarCard.vue` script setup 部分：

```typescript
// 替换原有的 Set 方案
const adjustingIdx = ref<number | null>(null);
const _adjustingTraffic = ref(0);

const deprecatingIdx = ref<number | null>(null);

function startAdjustTraffic(v: any, idx: number) {
  adjustingIdx.value = idx;
  _adjustingTraffic.value = v.traffic;
}

function confirmTrafficAdjustment(v: any) {
  v.traffic = _adjustingTraffic.value;
  adjustingIdx.value = null;
}

function cancelTrafficAdjustment() {
  adjustingIdx.value = null;
}

function startDeprecate(idx: number) {
  deprecatingIdx.value = idx;
}

function confirmDeprecate(v: any) {
  v.traffic = 0;
  v.status = 'deprecated';
  deprecatingIdx.value = null;
}
```

- [ ] **Step 3: 更新模板判断逻辑**

替换模板中所有 `adjustingIndices.has($index)` → `adjustingIdx === $index`
替换模板中所有 `deprecatingIndices.has($index)` → `deprecatingIdx === $index`

滑块 v-model 替换为 `_adjustingTraffic`：
```html
<input type="range" ... v-model.number="_adjustingTraffic" />
```

下线按钮 @click 替换为 `startDeprecate($index)`，确认按钮改为 `confirmDeprecate(v)`。

- [ ] **Step 4: build 验证**

```bash
cd frontend && npm run build
```
Expected: `✓ built` 无 error

- [ ] **Step 5: 手动验证（Playwright 截图）**

启动 dev server，访问 /onboarding，点击第一个"调流"按钮，确认只有该行出现滑块，其他行不变。

---

## Task 2: 安装 Playwright

**文件:** `frontend/package.json`

- [ ] **Step 1: 安装 Playwright + TypeScript 依赖**

```bash
cd frontend
npm install --save-dev @playwright/test playwright
npm install --save-dev typescript @types/node
```

- [ ] **Step 2: 确认 package.json 更新**

`devDependencies` 中应有 `@playwright/test` 和 `playwright`。

- [ ] **Step 3: 初始化 TypeScript 配置**

```bash
cd frontend
npx tsc --init --target ES2020 --module ESNext --moduleResolution node --strict --esModuleInterop --skipLibCheck
```

---

## Task 3: 创建 Playwright 配置

**文件:** `frontend/playwright.config.ts`

- [ ] **Step 1: 写入 Playwright 配置**

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
```

- [ ] **Step 2: 验证配置语法**

```bash
cd frontend
npx playwright --version
```

---

## Task 4: 创建 Page Object

**文件:** `frontend/tests/e2e/page-objects/onboarding.page.ts`

- [ ] **Step 1: 创建 Page Object 类**

```typescript
import { type Page, type Locator, expect } from '@playwright/test';

export class OnboardingPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly blueprintCards: Locator;
  readonly deployButton: Locator;
  readonly deployModal: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: '入职中心' });
    this.blueprintCards = page.locator('.avatar-card');
    this.deployButton = page.getByRole('button', { name: '+ 部署新 Avatar' });
    this.deployModal = page.locator('.modal');
  }

  async goto() {
    await this.page.goto('/onboarding');
    await this.heading.waitFor();
  }

  async expectCardCount(count: number) {
    await expect(this.blueprintCards).toHaveCount(count);
  }

  async openDeployModal() {
    await this.deployButton.click();
    await this.deployModal.waitFor();
  }

  async fillDeployForm({ alias, department }: { alias?: string; department?: string }) {
    if (alias) {
      await this.page.locator('.field-input').fill(alias);
    }
    if (department) {
      await this.page.locator('.field-select').selectOption(department);
    }
  }

  async submitDeploy() {
    await this.page.getByRole('button', { name: '激活 Avatar' }).click();
    await this.deployModal.waitForHidden({ timeout: 3000 }).catch(() => {});
  }

  async getFirstCard() {
    return this.blueprintCards.first();
  }
}
```

- [ ] **Step 2: 确认目录存在**

```bash
mkdir -p frontend/tests/e2e/page-objects
```

---

## Task 5: 编写 E2E 测试用例

**文件:** `frontend/tests/e2e/onboarding.spec.ts`

- [ ] **Step 1: E2E-ON-03 — 加载 Blueprint 列表**

```typescript
import { test, expect } from '@playwright/test';
import { OnboardingPage } from './page-objects/onboarding.page';

test.describe('Onboarding E2E', () => {
  let page: OnboardingPage;

  test.beforeEach(async ({ page: p }) => {
    page = new OnboardingPage(p);
    await page.goto();
  });

  test('E2E-ON-03: 页面加载 Blueprint 列表', async () => {
    // 显示 4 张卡片
    await page.expectCardCount(4);

    // 第一张卡片显示角色和别名
    const firstCard = page.blueprintCards.first();
    await expect(firstCard.locator('.role-name')).toBeVisible();
    await expect(firstCard.locator('.role-alias')).toBeVisible();

    // 容量条存在
    await expect(firstCard.locator('.capacity-track')).toBeVisible();

    // 执行任务按钮存在
    await expect(firstCard.getByRole('button', { name: '执行任务' })).toBeVisible();
  });
});
```

- [ ] **Step 2: E2E-ON-01 — 部署新 Avatar**

```typescript
  test('E2E-ON-01: 部署新 Avatar', async () => {
    const initialCount = await page.blueprintCards.count();
    await page.openDeployModal();

    // 填写别名（选第一项即可，部门和分身用默认值）
    await page.fillDeployForm({ alias: '测试Avatar-静安' });

    // 提交
    await page.submitDeploy();

    // 列表多了一张
    await page.expectCardCount(initialCount + 1);

    // 新卡片出现，包含别名
    const newCard = page.blueprintCards.last();
    await expect(newCard.locator('.role-alias')).toContainText('测试Avatar');
  });
```

- [ ] **Step 3: E2E-ON-02 — 部署新版本**

```typescript
  test('E2E-ON-02: 部署新版本', async ({ page: p }) => {
    const firstCard = await page.getFirstCard();

    // 点击部署新版本
    await firstCard.getByRole('button', { name: '部署新版本' }).click();

    // 出现表单
    await expect(firstCard.locator('.deploy-form')).toBeVisible();

    // 填写版本号
    await firstCard.locator('.deploy-input').fill('v9.9.9');
    await firstCard.locator('.deploy-btn', { hasText: '2' }).click();

    // 确认部署
    await firstCard.getByRole('button', { name: '确认部署' }).click();

    // 关闭表单，新版本出现在列表
    await expect(firstCard.locator('.deploy-form')).toBeHidden();
    await expect(firstCard.locator('.v-tag', { hasText: 'v9.9.9' })).toBeVisible();
  });
```

- [ ] **Step 4: E2E-ON-04 — 任务执行**

```typescript
  test('E2E-ON-04: 任务执行结果展示（mock模式）', async ({ page: p }) => {
    // opsApi.execute 在 mock 模式下返回固定值
    const firstCard = await page.getFirstCard();

    // 打开执行面板
    await firstCard.getByRole('button', { name: '执行任务' }).click();
    await expect(firstCard.locator('.task-panel')).toBeVisible();

    // 输入任务并提交
    await firstCard.locator('.task-input').fill('hello');
    await firstCard.locator('.panel-actions .btn.primary').click();

    // 等待结果出现（mock 固定返回 tokenTotal: 100, durationMs: 2000）
    await expect(firstCard.locator('.task-result')).toBeVisible({ timeout: 5000 });
    await expect(firstCard.locator('.result-summary')).toBeVisible();
    await expect(firstCard.locator('.result-meta')).toBeVisible();
  });
```

- [ ] **Step 5: 运行测试验证全部通过**

```bash
cd frontend
npx playwright test --project=chromium
```
Expected: 4 PASSED

---

## Task 6: 本地验证全链路

- [ ] **Step 1: 启动 dev server 并手动走一遍**

```bash
cd frontend && npm run dev
# 浏览器打开 http://localhost:5173/onboarding
```

验证：
1. 页面加载 4 张 Blueprint 卡片
2. 点击"调流"按钮 → 只有该行出现滑块 → 点 ✓ 或 ✕ 正常
3. 点击"下线"按钮 → 显示确认 → 点确认后 traffic=0
4. 点击"+ 部署新 Avatar" → 填写别名 → 提交 → 列表新增
5. 点击"执行任务" → 输入 → 看到结果面板（mock 模式）

- [ ] **Step 2: commit**

```bash
git add -A
git commit -m "feat(frontend): add Playwright E2E tests for onboarding + fix index bug

- E2E-ON-03: 列表加载
- E2E-ON-01: 部署新 Avatar  
- E2E-ON-02: 部署新版本
- E2E-ON-04: 任务执行结果

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 验收清单

- [ ] `npm run build` → success
- [ ] Playwright 4 个测试全部 PASSED
- [ ] 调流 UI bug 修复（单独一行出现滑块）
- [ ] 下线 UI bug 修复（单独一行出现确认）
- [ ] commit 到 feat/onboarding-mvp
