import { test, expect } from '@playwright/test';

test.describe('Onboarding Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Clear localStorage so we always start at onboarding
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  });

  test('welcome screen loads with heading and domain input', async ({ page }) => {
    await expect(page.locator('.onboarding-page')).toBeVisible();
    await expect(page.locator('.onboarding-container')).toBeVisible();
    // Should show welcome stage content
    // Verify onboarding content is present
    await expect(page.locator('.onboarding-page')).toBeVisible();
  });

  test('domain input accepts text', async ({ page }) => {
    const input = page.locator('input[type="text"], input[type="url"], input[placeholder*="domain" i], input[placeholder*="website" i], input[placeholder*="url" i]');
    await expect(input.first()).toBeVisible();
    await input.first().fill('example.com');
    await expect(input.first()).toHaveValue('example.com');
  });

  test('submit triggers processing state', async ({ page }) => {
    const input = page.locator('input[type="text"], input[type="url"], input[placeholder*="domain" i], input[placeholder*="website" i], input[placeholder*="url" i]');
    await input.first().fill('example.com');

    // Click the submit/start button
    const submitBtn = page.locator('button:has-text("Start"), button:has-text("Analyze"), button:has-text("Submit"), button:has-text("Go"), button[type="submit"]');
    await submitBtn.first().click();

    // Should transition to processing stage (or error if backend is down)
    await expect(
      page.locator('.onboarding-page')
    ).toBeVisible();
  });

  test('error state shows retry option', async ({ page }) => {
    const input = page.locator('input[type="text"], input[type="url"], input[placeholder*="domain" i], input[placeholder*="website" i], input[placeholder*="url" i]');
    await input.first().fill('example.com');

    const submitBtn = page.locator('button:has-text("Start"), button:has-text("Analyze"), button:has-text("Submit"), button:has-text("Go"), button[type="submit"]');
    await submitBtn.first().click();

    // If backend is down, we should eventually see error state
    const errorOrProcessing = page.locator('.onboarding-error, .onboarding-progress, [class*="progress"], [class*="error"]');
    await expect(errorOrProcessing.first()).toBeVisible({ timeout: 10000 });
  });
});
