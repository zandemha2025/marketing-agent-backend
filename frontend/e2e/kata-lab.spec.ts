import { test, expect } from '@playwright/test';

test.describe('Kata Lab', () => {
  test.beforeEach(async ({ page }) => {
    // Seed localStorage and navigate to Kata Lab via dashboard
    await page.goto('/');
    await page.evaluate(() => localStorage.setItem('organizationId', 'test-org-123'));
    await page.reload();
    // Click Kata Lab button in sidebar
    await page.locator('.kata-launch-btn').click();
    await expect(page.locator('.kata-lab-page')).toBeVisible();
  });

  test('Kata Lab page loads with header', async ({ page }) => {
    await expect(page.locator('.kata-header')).toBeVisible();
    await expect(page.locator('text=Kata Lab')).toBeVisible();
  });

  test('mode selector shows 3 modes', async ({ page }) => {
    const modeButtons = page.locator('.mode-button');
    await expect(modeButtons).toHaveCount(3);
    await expect(page.locator('.mode-name:has-text("Synthetic Influencer")')).toBeVisible();
    await expect(page.locator('text=Video Compositor')).toBeVisible();
    await expect(page.locator('text=Script Builder')).toBeVisible();
  });

  test('can switch between modes', async ({ page }) => {
    // Default is influencer mode — it should be active
    await expect(page.locator('.mode-button.active:has-text("Synthetic Influencer")')).toBeVisible();

    // Switch to Video Compositor
    await page.locator('.mode-button:has-text("Video Compositor")').click();
    await expect(page.locator('.mode-button.active:has-text("Video Compositor")')).toBeVisible();

    // Switch to Script Builder
    await page.locator('.mode-button:has-text("Script Builder")').click();
    await expect(page.locator('.mode-button.active:has-text("Script Builder")')).toBeVisible();
  });

  test('back button returns to dashboard', async ({ page }) => {
    await page.locator('.back-button').click();
    await expect(page.locator('.dashboard-page')).toBeVisible();
  });
});
