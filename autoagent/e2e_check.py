"""
AutoAgent E2E smoke test — run with: py autoagent/e2e_check.py

Uses Playwright (headless Chromium) to verify the app works like a real user.
Reads frontend_url from autoagent/config.json (default: http://localhost:3000).

The agent updates this file every session to cover newly added features.
"""
import json
import sys
import time
from pathlib import Path

# Load config to get frontend URL
AGENT_DIR    = Path(__file__).resolve().parent
CONFIG_FILE  = AGENT_DIR / "config.json"

_cfg = {}
if CONFIG_FILE.exists():
    try:
        _cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass

FRONTEND_URL = _cfg.get("frontend_url", "http://localhost:3000")
BACKEND_URL  = _cfg.get("backend_url",  "http://localhost:8000")


def run():
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    results = []

    def check(name: str, ok: bool, detail: str = ""):
        status = "PASS" if ok else "FAIL"
        msg    = f"  [{status}] {name}" + (f" — {detail}" if detail else "")
        results.append((ok, msg))
        print(msg)

    print(f"\nAutoAgent E2E — {FRONTEND_URL}\n" + "="*50)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page    = browser.new_page()

        # ── 1. App loads ────────────────────────────────────────────────────
        try:
            page.goto(FRONTEND_URL, timeout=15000)
            page.wait_for_load_state("networkidle", timeout=15000)
            check("App loads", True)
        except Exception as e:
            check("App loads", False, str(e))
            browser.close()
            return results

        # ── 2. Page has content ─────────────────────────────────────────────
        try:
            title = page.title()
            check("Page has title", bool(title), title)
        except Exception as e:
            check("Page has title", False, str(e))

        # ── 3. No console errors ────────────────────────────────────────────
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        time.sleep(1)
        check("No console errors", len(errors) == 0,
              f"{len(errors)} errors: {errors[:2]}" if errors else "")

        # ── 4. Screenshot ───────────────────────────────────────────────────
        try:
            screenshot_path = str(AGENT_DIR / "e2e_screenshot.png")
            page.screenshot(path=screenshot_path, full_page=False)
            check("Screenshot saved", True, screenshot_path)
        except Exception as e:
            check("Screenshot saved", False, str(e))

        # ── PROJECT-SPECIFIC CHECKS ─────────────────────────────────────────
        # The agent will add project-specific checks here each session.
        # Example patterns (uncomment and adapt as needed):
        #
        # # Check main listing/content area loads
        # try:
        #     page.wait_for_selector("[data-testid='main-content'], main, .app", timeout=5000)
        #     check("Main content visible", True)
        # except PWTimeout:
        #     check("Main content visible", False, "timeout")
        #
        # # Check search/filter works
        # try:
        #     search = page.locator("input[type='search'], [data-testid='search']").first
        #     search.fill("test")
        #     time.sleep(0.5)
        #     check("Search input works", True)
        # except Exception as e:
        #     check("Search input works", False, str(e))

        browser.close()

    # ── Summary ─────────────────────────────────────────────────────────────
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
