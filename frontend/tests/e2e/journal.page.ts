import { type Page, type Locator, expect } from '@playwright/test';

export class JournalPage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async goto() {
    await this.page.goto('/journal');
    await this.page.getByRole('heading', { name: '工作日记' }).waitFor();
  }

  async expectCardCount(count: number) {
    await expect(this.page.locator('.exec-card')).toHaveCount(count);
  }

  getCard(index: number) {
    return this.page.locator('.exec-card').nth(index);
  }

  async clickCard(index: number) {
    await this.getCard(index).click();
  }

  async searchByKeyword(q: string) {
    await this.page.locator('.filter-input').fill(q);
    await this.page.getByRole('button', { name: '搜索' }).click();
  }

  async selectStatus(statusValue: string) {
    await this.page.locator('.filter-select').first().selectOption(statusValue);
  }

}
