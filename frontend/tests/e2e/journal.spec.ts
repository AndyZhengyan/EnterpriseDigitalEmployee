import { test, expect } from '@playwright/test';
import { JournalPage } from './journal.page';

test.describe('Journal E2E', () => {

  test('Journal page loads with layout', async ({ page: p }) => {
    const journal = new JournalPage(p);
    await journal.goto();

    // 标题
    await expect(p.getByRole('heading', { name: '工作日记' })).toBeVisible();

    // 左右分栏布局
    await expect(p.locator('.left-panel')).toBeVisible();
    await expect(p.locator('.right-panel')).toBeVisible();

    // 右面板默认显示空状态
    await expect(p.locator('.empty-text')).toContainText('选择一条记录查看详情');
  });

  test('Journal filter bar has all controls', async ({ page: p }) => {
    const journal = new JournalPage(p);
    await journal.goto();

    // 3 个下拉框：状态、角色、部门
    const selects = p.locator('.filter-select');
    await expect(selects).toHaveCount(3);

    // 搜索框
    await expect(p.locator('.filter-input')).toBeVisible();

    // 搜索按钮
    await expect(p.getByRole('button', { name: '搜索' })).toBeVisible();
  });

  test('Journal shows execution cards', async ({ page: p }) => {
    const journal = new JournalPage(p);
    await journal.goto();

    // 等待卡片加载（mock 模式，6 条记录）
    await p.waitForTimeout(200);
    const count = await p.locator('.exec-card').count();
    expect(count).toBeGreaterThan(0);

    // 卡片包含关键信息
    const firstCard = journal.getCard(0);
    await expect(firstCard.locator('.card-alias')).toBeVisible();
    await expect(firstCard.locator('.card-role')).toBeVisible();
    await expect(firstCard.locator('.card-summary')).toBeVisible();
    await expect(firstCard.locator('.card-footer')).toBeVisible();
  });

  test('Journal clicking card shows detail', async ({ page: p }) => {
    const journal = new JournalPage(p);
    await journal.goto();

    // 点击第一张卡片
    await journal.clickCard(0);

    // 右侧详情面板显示内容（不再是空状态）
    await expect(p.locator('.detail-header')).toBeVisible();
    await expect(p.locator('.detail-title')).toBeVisible();
    await expect(p.locator('.detail-grid')).toBeVisible();

    // 状态徽章
    await expect(p.locator('.status-badge')).toBeVisible();
  });

  test('Journal search filters results', async ({ page: p }) => {
    const journal = new JournalPage(p);
    await journal.goto();

    await p.waitForTimeout(200);
    const initialCount = await p.locator('.exec-card').count();
    expect(initialCount).toBeGreaterThan(0);

    // 搜索关键词：只匹配 "码哥" 相关的记录（exec-001, exec-005）
    await journal.searchByKeyword('码哥');
    await p.waitForTimeout(200);

    const filteredCount = await p.locator('.exec-card').count();
    expect(filteredCount).toBeLessThan(initialCount);

    // 每张卡片的别名都包含"码哥"
    const cards = p.locator('.exec-card');
    const count = await cards.count();
    for (let i = 0; i < count; i++) {
      await expect(cards.nth(i).locator('.card-alias')).toContainText('码哥');
    }
  });

  test('Journal status filter works', async ({ page: p }) => {
    const journal = new JournalPage(p);
    await journal.goto();

    await p.waitForTimeout(200);
    const initialCount = await p.locator('.exec-card').count();
    expect(initialCount).toBeGreaterThan(0);

    // 筛选"成功"状态
    await journal.selectStatus('ok');
    await p.waitForTimeout(200);

    const okCount = await p.locator('.exec-card').count();
    expect(okCount).toBeLessThanOrEqual(initialCount);

    // 所有卡片的 status 图标都是 ok
    const cards = p.locator('.exec-card');
    const count = await cards.count();
    for (let i = 0; i < count; i++) {
      await expect(cards.nth(i).locator('.card-status.ok')).toBeVisible();
    }
  });

});
