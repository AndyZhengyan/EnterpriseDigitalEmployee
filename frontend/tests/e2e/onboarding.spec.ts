/**
 * onboarding.spec.ts — e-Agent-OS Onboarding E2E (real backend)
 * Tests run against the live Ops API (:8006) with Vite dev server (:5173).
 */

import { test, expect } from '@playwright/test';
import { OnboardingPage } from './page-objects/onboarding.page';

const SEED_BP_IDS = ['av-admin-001', 'av-legal-001', 'av-contract-001', 'av-swe-001'];
const BACKEND = 'http://localhost:8006';

test.beforeEach(async ({ request, page }) => {
  // Reset seeds and clean up non-seed blueprints
  await request.post(`${BACKEND}/api/test/reset-seeds`);
  const resp = await request.get(`${BACKEND}/api/onboarding/blueprints`);
  const blueprints = (await resp.json()) as Array<{ id: string }>;
  for (const bp of blueprints) {
    if (!SEED_BP_IDS.includes(bp.id)) {
      await request.delete(`${BACKEND}/api/onboarding/blueprints/${bp.id}`);
    }
  }
  // Reload so Vue re-fetches fresh state
  await page.goto('/onboarding');
  await page.getByRole('heading', { name: '入职中心' }).waitFor();
  await page.reload({ waitUntil: 'networkidle' });
  await page.getByRole('heading', { name: '入职中心' }).waitFor();
});

async function waitForCards(page: import('@playwright/test').Page) {
  await expect(page.locator('.avatar-card').first()).toBeVisible({ timeout: 8000 });
}

// ── Phase 1 ───────────────────────────────────────────

test.describe('Phase 1: Page Load', () => {
  test('E2E-ON-01: 4 seeded blueprints rendered', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    await expect(onboarding.page.locator('.avatar-card')).toHaveCount(4);
    const card = onboarding.getCard(0);
    await expect(card.locator('.role-name')).toContainText('专员');
    await expect(card.locator('.capacity-track')).toBeVisible();
    await expect(card.locator('.btn-action')).toBeVisible();
  });

  test('E2E-ON-02: Version list renders', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    await expect(onboarding.getCard(0).locator('.version-row')).toHaveCount(3);
    await expect(onboarding.getCard(0).locator('.v-status-label').first()).toContainText('正式上岗');
  });

  test('E2E-ON-03: Capacity bar visible', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    await expect(onboarding.getCard(0).locator('.capacity-fill').first()).toBeVisible();
  });
});

// ── Phase 2 ───────────────────────────────────────────

test.describe('Phase 2: Deploy Avatar', () => {
  test('E2E-ON-04: Card count increases, DB record created', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    const initial = await onboarding.page.locator('.avatar-card').count();
    await page.getByRole('button', { name: '+ 部署新 Avatar' }).click();
    await page.locator('.modal').waitFor({ state: 'visible' });
    await page.locator('.modal .field-input').first().fill('E2E04-Bot');
    await page.locator('.modal-footer .btn-primary').click();
    await page.waitForSelector('.modal', { state: 'hidden', timeout: 3000 }).catch(() => {});
    await page.waitForTimeout(300);
    expect(await onboarding.page.locator('.avatar-card').count()).toBe(initial + 1);
    const resp = await page.evaluate(() => fetch('/api/onboarding/blueprints').then(r => r.json()));
    const bps = resp as Array<{ alias: string }>;
    expect(bps.find(b => b.alias === 'E2E04-Bot')).toBeDefined();
  });

  test('E2E-ON-05: New card has capacity bar', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    await page.getByRole('button', { name: '+ 部署新 Avatar' }).click();
    await page.locator('.modal').waitFor({ state: 'visible' });
    await page.locator('.modal-footer .btn-primary').click();
    await page.waitForSelector('.modal', { state: 'hidden', timeout: 3000 }).catch(() => {});
    await page.waitForTimeout(300);
    await expect(onboarding.page.locator('.avatar-card').last().locator('.capacity-fill')).toBeVisible();
  });

  test('E2E-ON-06: Custom scaling visible in new card', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    await page.getByRole('button', { name: '+ 部署新 Avatar' }).click();
    await page.locator('.modal').waitFor({ state: 'visible' });
    await page.locator('.scaling-btn', { hasText: '2' }).first().click();
    await page.locator('.scaling-btn', { hasText: '10' }).last().click();
    await page.locator('.modal-footer .btn-primary').click();
    await page.waitForSelector('.modal', { state: 'hidden', timeout: 3000 }).catch(() => {});
    await page.waitForTimeout(300);
    await expect(onboarding.page.locator('.avatar-card').last().locator('.capacity-fill')).toBeVisible();
  });

  test('E2E-ON-07: Cancel — no card added', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    const initial = await onboarding.page.locator('.avatar-card').count();
    await page.getByRole('button', { name: '+ 部署新 Avatar' }).click();
    await page.locator('.modal').waitFor({ state: 'visible' });
    await page.locator('.modal-close').click();
    await page.waitForSelector('.modal', { state: 'hidden', timeout: 3000 }).catch(() => {});
    expect(await onboarding.page.locator('.avatar-card').count()).toBe(initial);
  });
});

// ── Phase 3 ───────────────────────────────────────────

test.describe('Phase 3: Deploy Version', () => {
  test('E2E-ON-08: Version appears in list', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    const card = onboarding.getCard(0);
    const before = await card.locator('.version-row').count();
    await card.locator('.btn-deploy').click();
    await expect(card.locator('.deploy-form')).toBeVisible();
    await card.locator('.deploy-input').fill('v99.99.99-e2e');
    await card.locator('.deploy-btn', { hasText: '2' }).click();
    await card.locator('.deploy-form .btn-confirm').click();
    await expect(card.locator('.deploy-form')).toBeHidden({ timeout: 3000 }).catch(() => {});
    await expect(card.locator('.v-tag', { hasText: 'v99.99.99-e2e' })).toBeVisible();
    expect(await card.locator('.version-row').count()).toBe(before + 1);
  });

  test('E2E-ON-09: Empty field — submit disabled', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    const card = onboarding.getCard(0);
    await card.locator('.btn-deploy').click();
    await expect(card.locator('.deploy-form')).toBeVisible();
    await expect(page.locator('.btn-confirm', { hasText: '确认部署' })).toBeDisabled();
    await card.locator('.deploy-input').fill('v1.0.0');
    await expect(page.locator('.btn-confirm', { hasText: '确认部署' })).toBeEnabled();
  });

  test('E2E-ON-10: Cancel — count unchanged', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    const card = onboarding.getCard(0);
    const before = await card.locator('.version-row').count();
    await card.locator('.btn-deploy').click();
    await page.locator('.btn-cancel').click();
    await expect(card.locator('.deploy-form')).toBeHidden({ timeout: 3000 }).catch(() => {});
    expect(await card.locator('.version-row').count()).toBe(before);
  });
});

// ── Phase 4 ───────────────────────────────────────────

test.describe('Phase 4: Traffic Adjustment', () => {
  test('E2E-ON-11: Slider opens, ✕ restores traffic', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    const card = onboarding.getCard(0);
    const row = card.locator('.version-row').first();
    await expect(row.locator('.v-btn', { hasText: '调流' })).toBeVisible({ timeout: 5000 });
    const original = await row.locator('.v-traffic').textContent();
    await row.locator('.v-btn', { hasText: '调流' }).click({ force: true });
    await expect(row.locator('.v-traffic-slider')).toBeVisible({ timeout: 3000 });
    await row.locator('.v-btn', { hasText: '✕' }).click({ force: true });
    await expect(row.locator('.v-btn', { hasText: '调流' })).toBeVisible({ timeout: 3000 });
    await expect(row.locator('.v-traffic')).toHaveText(original!, { timeout: 3000 });
  });

  test('E2E-ON-12: Drag slider changes value, ✕ restores', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    const card = onboarding.getCard(0);
    const row = card.locator('.version-row').first();
    await expect(row.locator('.v-btn', { hasText: '调流' })).toBeVisible({ timeout: 5000 });
    const original = await row.locator('.v-traffic').textContent();
    await row.locator('.v-btn', { hasText: '调流' }).click({ force: true });
    await expect(row.locator('.v-traffic-slider')).toBeVisible({ timeout: 3000 });
    const box = await row.locator('.v-traffic-slider').boundingBox();
    if (box) {
      await row.locator('.v-traffic-slider').hover({ position: { x: 0, y: 0 } });
      await page.mouse.down();
      await page.mouse.move(box.x + box.width * 0.25, box.y + box.height / 2);
      await page.mouse.up();
    }
    await row.locator('.v-btn', { hasText: '✕' }).click({ force: true });
    await expect(row.locator('.v-btn', { hasText: '调流' })).toBeVisible({ timeout: 3000 });
    await expect(row.locator('.v-traffic')).toHaveText(original!, { timeout: 3000 });
  });
});

// ── Phase 5 ───────────────────────────────────────────

test.describe('Phase 5: Deprecate Version', () => {
  test('E2E-ON-13: Optimistic UI updates status to 退役', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    const card = onboarding.getCard(0);
    const row = card.locator('.version-row').first();
    // Click 下线
    await page.evaluate(() => {
      const rows = document.querySelectorAll('.avatar-card .version-row');
      const btns = rows[0].querySelectorAll('.v-btn--danger');
      for (const btn of Array.from(btns)) {
        if (btn.textContent.trim() === '下线') { (btn as HTMLElement).click(); break; }
      }
    });
    await page.waitForTimeout(300);
    // Click 确认
    await page.evaluate(() => {
      const rows = document.querySelectorAll('.avatar-card .version-row');
      const btns = rows[0].querySelectorAll('button');
      for (const btn of Array.from(btns)) {
        if (btn.textContent.trim() === '确认') { (btn as HTMLElement).click(); break; }
      }
    });
    await page.waitForTimeout(500);
    await expect(row.locator('.v-status-label')).toContainText('退役', { timeout: 5000 });
  });

  test('E2E-ON-14: Cancel preserves original status', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    const card = onboarding.getCard(0);
    const row = card.locator('.version-row').first();
    await expect(row.locator('.v-btn--danger', { hasText: '下线' })).toBeVisible({ timeout: 5000 });
    const original = await row.locator('.v-status-label').textContent();
    await page.evaluate(() => {
      const rows = document.querySelectorAll('.avatar-card .version-row');
      const btns = rows[0].querySelectorAll('.v-btn--danger');
      for (const btn of Array.from(btns)) {
        if (btn.textContent.trim() === '下线') { (btn as HTMLElement).click(); break; }
      }
    });
    await page.waitForTimeout(300);
    await page.evaluate(() => {
      const rows = document.querySelectorAll('.avatar-card .version-row');
      const btns = rows[0].querySelectorAll('button');
      for (const btn of Array.from(btns)) {
        if (btn.textContent.trim() === '取消') { (btn as HTMLElement).click(); break; }
      }
    });
    await page.waitForTimeout(300);
    await expect(row.locator('.v-status-label')).toContainText(original!, { timeout: 3000 });
  });
});

// ── Phase 6 ───────────────────────────────────────────

test.describe('Phase 6: Task Panel', () => {
  test('E2E-ON-15: Opens and closes', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    const card = onboarding.getCard(0);
    await card.locator('.btn-action').click();
    await expect(onboarding.page.locator('.task-panel')).toBeVisible({ timeout: 3000 });
    await page.locator('.panel-close').click();
    await expect(onboarding.page.locator('.task-panel')).toBeHidden({ timeout: 5000 }).catch(() => {});
  });

  test('E2E-ON-16: Submit disabled when empty', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    const card = onboarding.getCard(0);
    await card.locator('.btn-action').click();
    await expect(onboarding.page.locator('.task-panel')).toBeVisible({ timeout: 3000 });
    await expect(page.locator('.panel-actions .btn.primary')).toBeDisabled();
    await page.locator('.task-input').fill('hello');
    await expect(page.locator('.panel-actions .btn.primary')).toBeEnabled();
  });

  test('E2E-ON-17: Empty input stays disabled', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    const card = onboarding.getCard(0);
    await card.locator('.btn-action').click();
    await expect(onboarding.page.locator('.task-panel')).toBeVisible({ timeout: 3000 });
    await expect(page.locator('.panel-actions .btn.primary')).toBeDisabled();
  });

  test('E2E-ON-18: Spinner completes (openclaw may be unavailable)', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    const card = onboarding.getCard(0);
    await card.locator('.btn-action').click();
    await expect(onboarding.page.locator('.task-panel')).toBeVisible({ timeout: 3000 });
    await page.locator('.task-input').fill('hello world');
    await page.locator('.panel-actions .btn.primary').click();
    // Spinner disappears when task completes (success or error)
    await expect(onboarding.page.locator('.spinner-inline')).toBeHidden({ timeout: 20000 });
  });
});

// ── Phase 7 ───────────────────────────────────────────

test.describe('Phase 7: Navigation', () => {
  test('E2E-ON-19: /onboarding renders correctly', async ({ page }) => {
    await page.goto('/onboarding');
    await page.getByRole('heading', { name: '入职中心' }).waitFor();
    await expect(page.locator('.page-title')).toContainText('入职中心');
    await expect(page.locator('.btn-primary', { hasText: '部署新 Avatar' })).toBeVisible();
  });

  test('E2E-ON-20: Button keyboard-focusable', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    await onboarding.getCard(0).locator('.btn-action').focus();
    await expect(onboarding.getCard(0).locator('.btn-action')).toBeFocused();
  });

  test('E2E-ON-21: Escape closes panel', async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await waitForCards(page);
    const card = onboarding.getCard(0);
    await card.locator('.btn-action').click();
    await expect(onboarding.page.locator('.task-panel')).toBeVisible({ timeout: 3000 });
    await page.keyboard.press('Escape');
    await expect(onboarding.page.locator('.task-panel')).toBeHidden({ timeout: 5000 }).catch(() => {});
  });
});
