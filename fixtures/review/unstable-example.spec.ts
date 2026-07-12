import { expect, test } from '@playwright/test';

test('shows the saved resource', async ({ page }) => {
  await page.goto('<BASE_URL>');
  await page.waitForTimeout(2000);

  const rows = page.locator('<SELECTOR>');
  if ((await rows.count()) > 0) {
    await rows.first().click();
  }

  expect(await page.locator('<SELECTOR>').textContent()).toBeTruthy();
});
