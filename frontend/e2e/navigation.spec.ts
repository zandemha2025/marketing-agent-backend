import { test, expect } from '@playwright/test';

test.describe('App Navigation', () => {
  test('app renders without crashing', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.app')).toBeVisible();
  });

  test('fresh load shows onboarding (no org in localStorage)', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await expect(page.locator('.onboarding-page')).toBeVisible();
  });

  test('with org ID, shows dashboard', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.setItem('organizationId', 'test-org-123'));
    await page.reload();
    await expect(page.locator('.dashboard-page')).toBeVisible();
  });

  test('can navigate from dashboard to Kata Lab and back', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.setItem('organizationId', 'test-org-123'));
    await page.reload();

    // Go to Kata Lab
    await page.locator('.kata-launch-btn').click();
    await expect(page.locator('.kata-lab-page')).toBeVisible();

    // Back to Dashboard
    await page.locator('.back-button').click();
    await expect(page.locator('.dashboard-page')).toBeVisible();
  });

  test('logout returns to onboarding', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.setItem('organizationId', 'test-org-123'));
    await page.reload();
    await expect(page.locator('.dashboard-page')).toBeVisible();

    // Click Switch Organization (logout)
    await page.locator('text=Switch Organization').click();
    await expect(page.locator('.onboarding-page')).toBeVisible();
  });
});
