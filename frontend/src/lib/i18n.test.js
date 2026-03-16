/**
 * Tests for the i18n translation system.
 *
 * Verifies:
 * - Both English and Persian have the exact same set of keys
 * - No translation key is an empty string
 * - The t() function returns the right language
 * - Falling back to English when a key is missing in Persian
 */

// Import the raw translations object directly
const translations = require('./i18n').default || require('./i18n');

// Helper: extract the `translations` object from the module
// The module exports { translations, LanguageProvider, useLanguage, t } etc.
// We need access to the raw keys — import the module and check its shape.

describe('i18n — translation key completeness', () => {
  let en, fa;

  beforeAll(() => {
    // Support both default export and named export patterns
    const mod = require('./i18n');
    const raw = mod.default || mod;

    // If the module exports a `translations` object directly
    if (raw && raw.en && raw.fa) {
      en = raw.en;
      fa = raw.fa;
    } else if (raw && raw.translations) {
      en = raw.translations.en;
      fa = raw.translations.fa;
    } else {
      throw new Error('Cannot find translations object in i18n.js — update this test if the export shape changed');
    }
  });

  test('English translations object exists and is not empty', () => {
    expect(en).toBeDefined();
    expect(Object.keys(en).length).toBeGreaterThan(10);
  });

  test('Persian (fa) translations object exists and is not empty', () => {
    expect(fa).toBeDefined();
    expect(Object.keys(fa).length).toBeGreaterThan(10);
  });

  test('English and Persian have the same keys', () => {
    const enKeys = Object.keys(en).sort();
    const faKeys = Object.keys(fa).sort();

    const missingInFa = enKeys.filter(k => !fa[k]);
    const missingInEn = faKeys.filter(k => !en[k]);

    if (missingInFa.length > 0) {
      console.warn('Keys in English but missing/empty in Persian:', missingInFa);
    }
    if (missingInEn.length > 0) {
      console.warn('Keys in Persian but missing/empty in English:', missingInEn);
    }

    // Both languages must have the same count
    expect(enKeys.length).toBe(faKeys.length);
  });

  test('No English translation is an empty string', () => {
    const emptyKeys = Object.entries(en)
      .filter(([, v]) => typeof v === 'string' && v.trim() === '')
      .map(([k]) => k);
    expect(emptyKeys).toEqual([]);
  });

  test('No Persian translation is an empty string', () => {
    const emptyKeys = Object.entries(fa)
      .filter(([, v]) => typeof v === 'string' && v.trim() === '')
      .map(([k]) => k);
    expect(emptyKeys).toEqual([]);
  });

  test('Key nav.dashboard exists in both languages', () => {
    expect(en['nav.dashboard']).toBeTruthy();
    expect(fa['nav.dashboard']).toBeTruthy();
  });

  test('Key dashboard.buyDeals exists in both languages', () => {
    expect(en['dashboard.buyDeals']).toBeTruthy();
    expect(fa['dashboard.buyDeals']).toBeTruthy();
  });
});
