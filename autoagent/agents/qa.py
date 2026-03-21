#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QA Agent — Quality Assurance Engineer

Runs all tests, Playwright E2E, validates everything. Finds coverage gaps and
fills them. Writes regression reports. Reports to shared/reports/qa.md.

Called by run.py — not run directly.
"""
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

AGENT_DIR  = Path(__file__).resolve().parent.parent
SHARED_DIR = AGENT_DIR / "shared"
ROOT       = AGENT_DIR.parent


def _call_claude(prompt: str, timeout: int = 1200) -> tuple[str, str]:
    npm_bin    = os.path.join(os.environ.get("APPDATA", ""), "npm")
    claude_cmd = os.path.join(npm_bin, "claude.cmd")
    if not os.path.exists(claude_cmd):
        return "", f"ERROR: claude.cmd not found at {claude_cmd}"
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(prompt)
            tmp = f.name
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_API_KEY_OVERRIDE", None)
        cmd    = f'type "{tmp}" | "{claude_cmd}" --print --dangerously-skip-permissions'
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace", cwd=str(ROOT),
            env=env
        )
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "", f"TIMEOUT after {timeout}s"
    except Exception as e:
        return "", f"ERROR: {e}"
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except Exception:
                pass


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def build_prompt(task_override: str = "") -> str:
    mission_brief = _read(SHARED_DIR / "mission_brief.md")
    project       = _read(AGENT_DIR / "PROJECT.md")
    knowledge     = _read(AGENT_DIR / "knowledge.md")[-2000:]
    north_star    = _read(SHARED_DIR / "north_star.md") or _read(AGENT_DIR / "NORTH_STAR.md")
    backlog       = _read(AGENT_DIR / "BACKLOG.md")
    health_log    = _read(AGENT_DIR / "health_log.json")

    # Parse health log for trends
    import json
    health_data   = json.loads(health_log) if health_log else []
    health_trend  = [(h.get("ts", ""), h.get("health_score", "?"), h.get("tests_failed", 0))
                     for h in health_data[-5:]]

    task_section = f"\n## YOUR ASSIGNED TASK\n{task_override}\n" if task_override else ""

    return f"""You are a SENIOR QA ENGINEER + PLAYWRIGHT SPECIALIST operating as part of a multi-agent autonomous system.

You have full access to Playwright, pytest, the file system, and all project tools.
You work without human supervision. Your job is to find and fix every quality gap.

PROJECT ROOT: {ROOT}

PROJECT CONTEXT:
{project or "(Fill in PROJECT.md)"}

NORTH STAR METRIC:
{north_star or "(Not set yet)"}

MISSION BRIEF (from Orchestrator):
{mission_brief or "(No mission brief — do a full QA audit)"}

KNOWLEDGE BASE:
{knowledge or "(empty)"}

BACKLOG:
{backlog or "(empty)"}

HEALTH LOG TREND (last 5 sessions):
{health_trend or "No data yet"}
{task_section}

---

## YOUR ROLE: Senior QA Engineer

You are a world-class QA engineer who:
- Thinks like a malicious user, not a happy user
- Tests edge cases, error conditions, and abuse cases
- Writes tests that actually find real bugs
- Improves test coverage systematically
- Never lets a known bug ship twice

---

## MANDATORY QA WORKFLOW

### STEP 1: Baseline Health Check
Run the full test suite. Record:
- Total tests: pass / fail / skip
- Any flaky tests (re-run 3 times to check)
- Test coverage percentage if available

### STEP 2: Coverage Gap Analysis
Find code that has NO test coverage:
- List all routes/endpoints — which have no test?
- List all utility functions — which have no test?
- List all React components — which have no E2E test?

### STEP 3: Bug Hunting
Think like an attacker and a confused user:
- What happens with empty inputs?
- What happens with very large inputs?
- What happens when the DB is down?
- What happens with special characters (SQL injection, XSS)?
- What happens when a user goes "back" mid-flow?
- What happens on a slow 3G connection?

### STEP 4: Write Missing Tests
Write tests for the 3 most critical gaps found in Step 2.
Priority order:
1. Tests for code changed in the last 3 sessions
2. Tests for user-facing critical flows (auth, payment, core feature)
3. Tests for edge cases that could cause data loss or security issues

### STEP 5: E2E Test Update
Update autoagent/e2e_check.py to cover:
- The main user flow from landing page to core feature
- Any new feature added in the last 2 sessions
- Error states (what happens when API is down?)

```python
# E2E test template
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:3000")
    page.wait_for_load_state("networkidle")

    # Assert key elements exist
    assert page.locator("[data-testid='main-heading']").is_visible()

    # Test the main user flow
    # ...

    page.screenshot(path="autoagent/e2e_screenshot.png")
    browser.close()
    print("E2E: PASS")
```

### STEP 6: Regression Report
Write a regression report to shared/reports/qa.md:
- Tests before: X pass, Y fail
- Tests after: X pass, Y fail
- New tests added: Z
- Bugs found: list them
- Bugs fixed: list them

### STEP 7: Self-Grow
- Save useful test patterns to autoagent/skills/
- Update knowledge.md with QA lessons
- Add found bugs to BACKLOG.md with [!] prefix

---

## QA STANDARDS
- Every test must be deterministic — no sleep(), use waitForSelector()
- Tests must work without a running server when possible
- E2E tests must save screenshots on failure
- Test names must describe what they test: test_user_can_login_with_valid_credentials()
- Never delete existing passing tests
- Fix flaky tests by root cause, not by retrying

---

END YOUR RESPONSE WITH THIS EXACT BLOCK:
QA_DONE: <one sentence: what was tested and fixed>
TESTS_BEFORE: <X pass, Y fail>
TESTS_AFTER: <X pass, Y fail>
NEW_TESTS_ADDED: <count>
BUGS_FOUND: <count>
BUGS_FIXED: <count>
COVERAGE_IMPROVEMENT: <estimate: e.g. "57% -> 63%">
"""


def run(task: str = "") -> dict:
    """Run the QA agent. Returns result dict."""
    print("  [QA] Starting quality assurance session...")
    prompt   = build_prompt(task_override=task)
    stdout, stderr = _call_claude(prompt, timeout=1200)

    if not stdout:
        print(f"  [QA] ERROR: {stderr[:200]}")
        return {"success": False, "error": stderr[:200]}

    import re
    done_m     = re.search(r"QA_DONE:\s*(.+)",              stdout)
    before_m   = re.search(r"TESTS_BEFORE:\s*(.+)",         stdout)
    after_m    = re.search(r"TESTS_AFTER:\s*(.+)",          stdout)
    new_m      = re.search(r"NEW_TESTS_ADDED:\s*(\d+)",     stdout)
    found_m    = re.search(r"BUGS_FOUND:\s*(\d+)",          stdout)
    fixed_m    = re.search(r"BUGS_FIXED:\s*(\d+)",          stdout)
    cov_m      = re.search(r"COVERAGE_IMPROVEMENT:\s*(.+)", stdout)

    summary      = done_m.group(1).strip()   if done_m   else "QA session completed"
    tests_before = before_m.group(1).strip() if before_m else "unknown"
    tests_after  = after_m.group(1).strip()  if after_m  else "unknown"
    new_tests    = int(new_m.group(1))        if new_m    else 0
    bugs_found   = int(found_m.group(1))      if found_m  else 0
    bugs_fixed   = int(fixed_m.group(1))      if fixed_m  else 0
    coverage     = cov_m.group(1).strip()     if cov_m    else "unknown"

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = (
        f"# QA Report — {ts}\n\n"
        f"**Summary:** {summary}\n"
        f"**Tests before:** {tests_before}\n"
        f"**Tests after:** {tests_after}\n"
        f"**New tests added:** {new_tests}\n"
        f"**Bugs found:** {bugs_found}\n"
        f"**Bugs fixed:** {bugs_fixed}\n"
        f"**Coverage:** {coverage}\n\n"
        f"## Full Output\n\n{stdout}\n"
    )
    (SHARED_DIR / "reports").mkdir(parents=True, exist_ok=True)
    (SHARED_DIR / "reports" / "qa.md").write_text(report, encoding="utf-8")

    print(f"  [QA] Done: {summary[:80]}")
    print(f"  [QA] Tests: {tests_before} -> {tests_after} | Bugs fixed: {bugs_fixed}")

    return {
        "success": True,
        "summary": summary,
        "tests_before": tests_before,
        "tests_after": tests_after,
        "new_tests": new_tests,
        "bugs_found": bugs_found,
        "bugs_fixed": bugs_fixed,
        "coverage": coverage,
        "full_output": stdout
    }
