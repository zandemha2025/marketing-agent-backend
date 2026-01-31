import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Seed localStorage with a fake org ID to skip onboarding
    await page.goto('/');
    await page.evaluate(() => localStorage.setItem('organizationId', 'test-org-123'));
    await page.reload();
  });

  test('dashboard loads with sidebar navigation', async ({ page }) => {
    await expect(page.locator('.dashboard-page')).toBeVisible();
    await expect(page.locator('.sidebar')).toBeVisible();
    await expect(page.locator('.main-content')).toBeVisible();
  });

  test('sidebar shows all nav items: Chat, Campaigns, Assets, Brand', async ({ page }) => {
    await expect(page.locator('.nav-item:has-text("Chat")')).toBeVisible();
    await expect(page.locator('.nav-item:has-text("Campaigns")')).toBeVisible();
    await expect(page.locator('.nav-item:has-text("Assets")')).toBeVisible();
    await expect(page.locator('.nav-item:has-text("Brand")')).toBeVisible();
  });

  test('can navigate between Chat, Campaigns, Assets, Brand views', async ({ page }) => {
    // Default is chat view
    await expect(page.locator('.chat-container')).toBeVisible();

    // Switch to Campaigns
    await page.locator('.nav-item:has-text("Campaigns")').click();
    await expect(page.locator('.campaigns-list-view, .campaign-detail-view')).toBeVisible();

    // Switch to Assets
    await page.locator('.nav-item:has-text("Assets")').click();
    await expect(page.locator('.assets-view')).toBeVisible();

    // Switch to Brand
    await page.locator('.nav-item:has-text("Brand")').click();
    await expect(page.locator('.brand-view')).toBeVisible();

    // Back to Chat
    await page.locator('.nav-item:has-text("Chat")').click();
    await expect(page.locator('.chat-container')).toBeVisible();
  });

  test('campaigns view shows empty state or campaign list', async ({ page }) => {
    await page.locator('.nav-item:has-text("Campaigns")').click();
    // Either shows campaigns grid or empty state
    const content = page.locator('.campaigns-grid, .empty-state');
    await expect(content.first()).toBeVisible();
  });

  test('chat input is visible and accepts text', async ({ page }) => {
    const chatInput = page.locator('.chat-input');
    await expect(chatInput).toBeVisible();
    await chatInput.fill('Hello, test message');
    await expect(chatInput).toHaveValue('Hello, test message');
  });

  test('chat send button exists', async ({ page }) => {
    await expect(page.locator('.chat-send')).toBeVisible();
  });

  test('Kata Lab button is visible in sidebar', async ({ page }) => {
    await expect(page.locator('.kata-launch-btn')).toBeVisible();
  });
});
