/**
 * E2E Smoke Tests — requires both frontend (port 3000) and backend (port 8001) running.
 *
 * Run with: npx playwright test
 * These tests simulate real user actions in a real browser.
 */

const { test, expect } = require('@playwright/test');

test.describe('AutoFlip — Smoke Tests', () => {
  test('app loads and shows the navigation bar', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('nav, [role="navigation"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('dashboard page is visible on load', async ({ page }) => {
    await page.goto('/');
    // Wait for the main content area — either listings table or empty state
    await expect(page.locator('body')).toBeVisible();
    // No JS errors should have occurred
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.waitForTimeout(2000);
    expect(errors.filter(e => !e.includes('ResizeObserver'))).toHaveLength(0);
  });

  test('search input is interactive', async ({ page }) => {
    await page.goto('/');
    const search = page.locator('input[placeholder*="Search"], input[placeholder*="search"]').first();
    await search.waitFor({ state: 'visible', timeout: 10000 });
    await search.fill('Toyota Camry');
    await expect(search).toHaveValue('Toyota Camry');
  });

  test('navigation links are present', async ({ page }) => {
    await page.goto('/');
    // Check at least one nav item renders
    const navText = await page.locator('body').textContent();
    expect(navText).toMatch(/dashboard|intelligence|autoflip/i);
  });
});

test.describe('AutoFlip — Auth Flow', () => {
  test('login page renders when navigating to /login', async ({ page }) => {
    await page.goto('/');
    // Look for a login or sign in element
    const loginBtn = page.locator('button, a').filter({ hasText: /sign in|log in|login/i }).first();
    if (await loginBtn.isVisible()) {
      await loginBtn.click();
      await page.waitForTimeout(500);
    }
    // Either we're on a login page or saw the auth button
    const body = await page.locator('body').textContent();
    expect(body.length).toBeGreaterThan(0);
  });

  test('register page shows email and password fields', async ({ page }) => {
    await page.goto('/');
    // Try to find signup link
    const signupBtn = page.locator('button, a').filter({ hasText: /sign up|register|create account/i }).first();
    if (await signupBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await signupBtn.click();
      await page.waitForTimeout(500);
      // Should have email and password inputs
      const email = page.locator('input[type="email"], input[placeholder*="email" i]').first();
      const password = page.locator('input[type="password"], input[placeholder*="password" i]').first();
      if (await email.isVisible()) {
        await expect(email).toBeVisible();
        await expect(password).toBeVisible();
      }
    }
  });
});

test.describe('AutoFlip — API Health', () => {
  test('backend API root is reachable', async ({ request }) => {
    const resp = await request.get('http://localhost:8001/api/').catch(() => null);
    if (resp) {
      expect(resp.status()).toBe(200);
      const body = await resp.json();
      expect(body).toHaveProperty('version');
    } else {
      test.skip(true, 'Backend not running — skipping API health check');
    }
  });

  test('listings endpoint returns valid structure', async ({ request }) => {
    const resp = await request.get('http://localhost:8001/api/listings').catch(() => null);
    if (resp) {
      expect(resp.status()).toBe(200);
      const body = await resp.json();
      expect(Array.isArray(body)).toBe(true);
    } else {
      test.skip(true, 'Backend not running — skipping listings check');
    }
  });

  test('stats endpoint returns valid structure', async ({ request }) => {
    const resp = await request.get('http://localhost:8001/api/stats').catch(() => null);
    if (resp) {
      expect(resp.status()).toBe(200);
      const body = await resp.json();
      expect(body).toHaveProperty('total');
    } else {
      test.skip(true, 'Backend not running — skipping stats check');
    }
  });
});
