import { test, expect } from '@playwright/test';

test.describe('Static assets & PWA', () => {
  test('manifest returns valid JSON', async ({ request }) => {
    const response = await request.get('/manifest.json');
    expect(response.status()).toBe(200);
    const manifest = await response.json();
    expect(manifest.name).toBe('FPL Analytics');
    expect(manifest.display).toBe('standalone');
    expect(manifest.icons).toHaveLength(3);
  });

  test('favicon SVG loads', async ({ request }) => {
    const response = await request.get('/favicon.svg');
    expect(response.status()).toBe(200);
    const text = await response.text();
    expect(text).toContain('<svg');
  });

  test('favicon ICO loads', async ({ request }) => {
    const response = await request.get('/favicon.ico');
    expect(response.status()).toBe(200);
  });

  test('service worker JS loads with correct version', async ({ request }) => {
    const response = await request.get('/sw.js');
    expect(response.status()).toBe(200);
    const text = await response.text();
    expect(text).toContain('fpl-v2');
  });

  test('sw.js skips /api/ routes', async ({ request }) => {
    const text = await (await request.get('/sw.js')).text();
    expect(text).toContain("if (url.pathname.startsWith('/api/')) return");
  });
});

async function backendIsUp(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 2000);
    const res = await fetch('http://localhost:8000/health', { signal: controller.signal });
    clearTimeout(timer);
    return res.ok;
  } catch {
    return false;
  }
}

test.describe('Pages load (requires backend)', () => {
  test.beforeEach(async () => {
    test.skip(!(await backendIsUp()), 'Backend not running');
  });

  test('dashboard renders', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/FPL Analytics/);
    await expect(page.locator('text=Gameweek')).toBeVisible();
  });

  test('countdown is green', async ({ page }) => {
    await page.goto('/');
    const digit = page.locator('[style*="rgb(0, 255, 135)"]').first();
    await expect(digit).toBeVisible({ timeout: 5000 });
  });

  test('players page loads', async ({ page }) => {
    await page.goto('/players');
    await expect(page.locator('table')).toBeVisible({ timeout: 10000 });
  });

  test('navigate to players via nav', async ({ page }) => {
    await page.goto('/');
    await page.locator('a[href="/players"]').first().click();
    await expect(page).toHaveURL('/players');
  });
});

test.describe('Mobile layout', () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test.beforeEach(async () => {
    test.skip(!(await backendIsUp()), 'Backend not running');
  });

  test('bottom tab bar is visible', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('nav.fixed')).toBeVisible();
  });
});
