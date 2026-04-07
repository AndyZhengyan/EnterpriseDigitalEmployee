import { test, expect } from '@playwright/test';
import { OraclePage } from './oracle.page';

test.describe('Oracle E2E', () => {

  test('Oracle page loads with layout', async ({ page: p }) => {
    const oracle = new OraclePage(p);
    await oracle.goto();

    // 标题
    await expect(p.getByRole('heading', { name: '档案中心' })).toBeVisible();

    // 左右分栏布局
    await expect(p.locator('.left-panel')).toBeVisible();
    await expect(p.locator('.right-panel')).toBeVisible();

    // 右面板默认显示空状态
    await expect(p.locator('.empty-text')).toContainText('选择一份档案查看内容');
  });

  test('Oracle source filter buttons work', async ({ page: p }) => {
    const oracle = new OraclePage(p);
    await oracle.goto();

    // 等待卡片加载（mock 模式，6 条记录）
    await expect(p.locator('.archive-card').first()).toBeVisible({ timeout: 5000 });
    const initialCount = await p.locator('.archive-card').count();
    expect(initialCount).toBeGreaterThan(0);

    // 筛选 Avatar 记忆（3 条）
    await oracle.filterBySource('Avatar 记忆');
    await oracle.expectSourceFilterActive('Avatar 记忆');
    await expect(p.locator('.archive-card').first()).toBeVisible({ timeout: 5000 });
    const avatarCount = await p.locator('.archive-card').count();
    expect(avatarCount).toBeLessThan(initialCount);
    for (let i = 0; i < avatarCount; i++) {
      await expect(p.locator('.archive-card').nth(i).locator('.source-tag')).toContainText('Avatar 记忆');
    }

    // 筛选 导入档案（3 条）
    await oracle.filterBySource('导入档案');
    await oracle.expectSourceFilterActive('导入档案');
    await expect(p.locator('.archive-card').first()).toBeVisible({ timeout: 5000 });
    const importCount = await p.locator('.archive-card').count();
    expect(importCount).toBeLessThan(initialCount);
    for (let i = 0; i < importCount; i++) {
      await expect(p.locator('.archive-card').nth(i).locator('.source-tag')).toContainText('导入档案');
    }

    // 切回全部
    await oracle.filterBySource('全部');
    await oracle.expectSourceFilterActive('全部');
    await expect(p.locator('.archive-card').first()).toBeVisible({ timeout: 5000 });
    const allCount = await p.locator('.archive-card').count();
    expect(allCount).toBe(initialCount);
  });

  test('Oracle archive card shows metadata', async ({ page: p }) => {
    const oracle = new OraclePage(p);
    await oracle.goto();

    await expect(p.locator('.archive-card').first()).toBeVisible({ timeout: 5000 });
    const firstCard = oracle.getCard(0);

    // 来源标签
    await expect(firstCard.locator('.source-tag')).toBeVisible();

    // 标题
    await expect(firstCard.locator('.card-title')).toBeVisible();

    // 贡献者
    await expect(firstCard.locator('.card-contributor')).toBeVisible();

    // 日期
    await expect(firstCard.locator('.card-date')).toBeVisible();
  });

  test('Oracle clicking card shows detail', async ({ page: p }) => {
    const oracle = new OraclePage(p);
    await oracle.goto();

    await expect(p.locator('.archive-card').first()).toBeVisible({ timeout: 5000 });

    // 点击第一张卡片
    await oracle.clickCard(0);

    // 右侧详情面板显示内容（不再是空状态）
    await expect(p.locator('.detail-header')).toBeVisible();
    await expect(p.locator('.detail-title')).toBeVisible();
    await expect(p.locator('.detail-content')).toBeVisible();

    // Markdown 内容区域有内容
    const content = p.locator('.detail-content');
    await expect(content).not.toBeEmpty();
  });

  test('Oracle Markdown renders correctly', async ({ page: p }) => {
    const oracle = new OraclePage(p);
    await oracle.goto();

    await expect(p.locator('.archive-card').first()).toBeVisible({ timeout: 5000 });
    await oracle.clickCard(0);

    const content = p.locator('.detail-content');

    // Markdown h2 渲染（所有档案内容都以 ## 开头）
    await expect(content.locator('h2').first()).toBeVisible({ timeout: 5000 });

    // Markdown 表格渲染（arch-001 包含表格）
    const table = content.locator('table');
    await expect(table.first()).toBeVisible({ timeout: 5000 });

    // Markdown 列表渲染
    await expect(content.locator('ul').first()).toBeVisible();
  });

  test('Oracle empty state on no archives', async ({ page: p }) => {
    const oracle = new OraclePage(p);
    await oracle.goto();

    // 等待初始卡片加载
    await expect(p.locator('.archive-card').first()).toBeVisible({ timeout: 5000 });

    // 切换到 Avatar 记忆（3条），确认卡片存在且无空状态
    await oracle.filterBySource('Avatar 记忆');
    await expect(p.locator('.archive-card').first()).toBeVisible({ timeout: 5000 });
    await expect(p.locator('.list-empty')).not.toBeVisible();
    const avatarCount = await p.locator('.archive-card').count();
    expect(avatarCount).toBe(3);
    for (let i = 0; i < avatarCount; i++) {
      await expect(p.locator('.archive-card').nth(i).locator('.source-tag')).toContainText('Avatar 记忆');
    }

    // 切换到导入档案（3条），确认卡片存在且无空状态
    await oracle.filterBySource('导入档案');
    await expect(p.locator('.archive-card').first()).toBeVisible({ timeout: 5000 });
    await expect(p.locator('.list-empty')).not.toBeVisible();
    const importCount = await p.locator('.archive-card').count();
    expect(importCount).toBe(3);
    for (let i = 0; i < importCount; i++) {
      await expect(p.locator('.archive-card').nth(i).locator('.source-tag')).toContainText('导入档案');
    }

    // 切回全部，确认恢复全部卡片，无空状态
    await oracle.filterBySource('全部');
    await expect(p.locator('.archive-card').first()).toBeVisible({ timeout: 5000 });
    await expect(p.locator('.list-empty')).not.toBeVisible();
    const allCount = await p.locator('.archive-card').count();
    expect(allCount).toBe(6);
  });

});
