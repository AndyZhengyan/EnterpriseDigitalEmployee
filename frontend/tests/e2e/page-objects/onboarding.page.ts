import { type Page, type Locator, expect } from '@playwright/test';

export class OnboardingPage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async goto() {
    await this.page.goto('/onboarding');
    await this.page.getByRole('heading', { name: '入职中心' }).waitFor();
  }

  async expectCardCount(count: number) {
    await expect(this.page.locator('.avatar-card')).toHaveCount(count);
  }

  getCard(index: number) {
    return this.page.locator('.avatar-card').nth(index);
  }

  async openDeployModal() {
    await this.page.getByRole('button', { name: '+ 部署新 Avatar' }).click();
    await this.page.locator('.modal').waitFor({ state: 'visible' });
  }

  async submitDeploy() {
    await this.page.locator('.modal-footer .btn-primary').click();
    // wait for modal to close
    await this.page.locator('.modal').waitFor({ state: 'hidden', timeout: 3000 }).catch(() => {});
  }

  async deployAvatar(alias: string, department?: string) {
    await this.openDeployModal();
    if (alias) {
      await this.page.locator('.field-input').fill(alias);
    }
    if (department) {
      await this.page.locator('.field-select').selectOption(department);
    }
    await this.submitDeploy();
  }

  async openTaskPanel(card: Locator) {
    await card.locator('.btn-action').click();
    await this.page.locator('.task-panel').waitFor({ state: 'visible' });
  }

  async submitTask(message: string) {
    await this.page.locator('.task-input').fill(message);
    await this.page.locator('.panel-actions .btn.primary').click();
    await this.page.locator('.task-result').waitFor({ state: 'visible', timeout: 8000 });
  }

  async openDeployVersionForm(card: Locator) {
    await card.locator('.btn-deploy').click();
    await card.locator('.deploy-form').waitFor({ state: 'visible' });
  }

  async submitDeployVersion(version: string, replicas: number = 1) {
    await this.page.locator('.deploy-input').fill(version);
    await this.page.locator('.deploy-btn', { hasText: String(replicas) }).click();
    await this.page.getByRole('button', { name: '确认部署' }).click();
    await this.page.locator('.deploy-form').waitFor({ state: 'hidden', timeout: 3000 }).catch(() => {});
  }
}
