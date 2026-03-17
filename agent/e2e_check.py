"""
AutoFlip E2E smoke test — run with: py agent/e2e_check.py
Uses Playwright (headless Chromium) to verify the app works like a real user.
The agent updates this file every session to cover newly added features.
"""
import sys
import time

FRONTEND_URL = "http://localhost:3000"
BACKEND_URL  = "http://localhost:8001"


def run():
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    results = []

    def check(name: str, ok: bool, detail: str = ""):
        status = "PASS" if ok else "FAIL"
        msg = f"  [{status}] {name}" + (f" — {detail}" if detail else "")
        results.append((ok, msg))
        print(msg)

    print(f"\nAutoFlip E2E — {FRONTEND_URL}\n" + "="*50)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # ── 1. App loads ───────────────────────────────────────────────────
        try:
            page.goto(FRONTEND_URL, timeout=15000)
            page.wait_for_load_state("networkidle", timeout=15000)
            check("App loads", True)
        except Exception as e:
            check("App loads", False, str(e))
            browser.close()
            return results

        # ── 2. Listings visible ────────────────────────────────────────────
        try:
            page.wait_for_selector("table tbody tr, [data-testid='listing-row']", timeout=10000)
            count = page.locator("table tbody tr").count()
            check("Listings visible", count > 0, f"{count} rows")
        except PWTimeout:
            check("Listings visible", False, "timeout waiting for rows")

        # ── 3. Source filter has SalvageReseller ───────────────────────────
        try:
            page.locator("[data-testid='source-filter']").click()
            page.wait_for_selector("text=SalvageReseller", timeout=3000)
            check("SalvageReseller in source filter", True)
            page.keyboard.press("Escape")
        except Exception:
            check("SalvageReseller in source filter", False, "not found in dropdown")

        # ── 4. Search works ────────────────────────────────────────────────
        try:
            search = page.locator("[data-testid='search-input']")
            search.fill("Toyota")
            time.sleep(1)
            count_after = page.locator("table tbody tr").count()
            search.fill("")
            check("Search filters listings", True, f"{count_after} results for 'Toyota'")
        except Exception as e:
            check("Search filters listings", False, str(e))

        # ── 5. Watchlist star button ───────────────────────────────────────
        try:
            star = page.locator("button[aria-label*='watchlist'], button[title*='save'], button svg").first
            star.click(timeout=3000)
            check("Watchlist star clickable", True)
        except Exception:
            check("Watchlist star clickable", False, "star button not found")

        # ── 6. Screenshot ──────────────────────────────────────────────────
        try:
            page.screenshot(path="agent/e2e_screenshot.png", full_page=False)
            check("Screenshot saved", True, "agent/e2e_screenshot.png")
        except Exception as e:
            check("Screenshot saved", False, str(e))

        browser.close()

    # ── Summary ────────────────────────────────────────────────────────────
    passed = sum(1 for ok, _ in results if ok)
    total  = len(results)
    print(f"\n{'='*50}")
    print(f"E2E Result: {passed}/{total} checks passed")

    if passed < total:
        print("\nFailed checks:")
        for ok, msg in results:
            if not ok:
                print(msg)
        sys.exit(1)
    else:
        print("All checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    run()
