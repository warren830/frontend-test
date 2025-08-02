
import { test } from '@playwright/test';
import { expect } from '@playwright/test';

test('test1_2025-06-23', async ({ page, context }) => {
  
    // Navigate to URL
    await page.goto('https://www.baidu.com');

    // Take screenshot
    await page.screenshot({ path: 'baidu_homepage.png' });

    // Fill input field
    await page.fill('#kw', '小米');

    // Click element
    await page.click('#su');

    // Take screenshot
    await page.screenshot({ path: 'search_results.png' });
});