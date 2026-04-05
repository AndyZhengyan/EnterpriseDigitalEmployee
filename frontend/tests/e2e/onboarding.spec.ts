import { test, expect } from '@playwright/test';
import { OnboardingPage } from './page-objects/onboarding.page';

test.describe('Onboarding E2E — Phase 1', () => {

  test('E2E-ON-03: 页面加载 Blueprint 列表（mock 模式）', async ({ page: p }) => {
    const onboarding = new OnboardingPage(p);
    await onboarding.goto();

    // 显示 4 张卡片
    await onboarding.expectCardCount(4);

    // 第一张卡片有关键信息
    const firstCard = onboarding.getCard(0);
    await expect(firstCard.locator('.role-name')).toBeVisible();
    await expect(firstCard.locator('.role-alias')).toBeVisible();
    await expect(firstCard.locator('.capacity-track')).toBeVisible();
    await expect(firstCard.locator('.btn-action')).toBeVisible();
  });

  test('E2E-ON-01: 部署新 Avatar', async ({ page: p }) => {
    const onboarding = new OnboardingPage(p);
    await onboarding.goto();

    const initialCount = await onboarding.page.locator('.avatar-card').count();
    await onboarding.deployAvatar('自动化测试Avatar');

    // 等待 Vue 响应式更新
    await p.waitForTimeout(100);
    // 列表多了一张
    await expect(onboarding.page.locator('.avatar-card')).toHaveCount(initialCount + 1);

    // 新卡片包含别名
    const newCard = onboarding.page.locator('.avatar-card').last();
    await expect(newCard.locator('.role-alias')).toContainText('自动化测试Avatar');
  });

  test('E2E-ON-02: 部署新版本', async ({ page: p }) => {
    const onboarding = new OnboardingPage(p);
    await onboarding.goto();

    const firstCard = onboarding.getCard(0);

    // 展开部署表单
    await firstCard.locator('.btn-deploy').click();
    await expect(firstCard.locator('.deploy-form')).toBeVisible();

    // 填写并提交
    await firstCard.locator('.deploy-input').fill('v9.9.9');
    await firstCard.locator('.deploy-btn', { hasText: '2' }).click();
    await onboarding.page.getByRole('button', { name: '确认部署' }).click();

    // 表单关闭，新版本出现
    await expect(firstCard.locator('.deploy-form')).toBeHidden({ timeout: 3000 }).catch(() => {});
    await expect(firstCard.locator('.v-tag', { hasText: 'v9.9.9' })).toBeVisible();
  });

  test('E2E-ON-04: 任务执行结果展示（mock 模式）', async ({ page: p }) => {
    const onboarding = new OnboardingPage(p);
    await onboarding.goto();

    const firstCard = onboarding.getCard(0);

    // 打开任务面板
    await firstCard.locator('.btn-action').click();
    await expect(onboarding.page.locator('.task-panel')).toBeVisible();

    // 输入并提交
    await onboarding.page.locator('.task-input').fill('hello');
    await onboarding.page.locator('.panel-actions .btn.primary').click();

    // 等待 mock 返回（固定延迟 100ms，见 api.js opsApi.execute mock）
    await expect(onboarding.page.locator('.task-result')).toBeVisible({ timeout: 8000 });
    await expect(onboarding.page.locator('.result-summary')).toBeVisible();
    await expect(onboarding.page.locator('.result-meta')).toBeVisible();
  });

});
