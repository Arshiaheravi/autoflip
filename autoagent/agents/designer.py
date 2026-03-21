#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Designer Agent — UI/UX Designer

Screenshots competitor UIs using Playwright. Analyzes design, colors, layout,
and conversion patterns. Proposes and implements design improvements.
Reports to shared/reports/designer.md.

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
    hypotheses    = _read(SHARED_DIR / "hypotheses.md")
    project       = _read(AGENT_DIR / "PROJECT.md")
    knowledge     = _read(AGENT_DIR / "knowledge.md")[-2000:]
    north_star    = _read(SHARED_DIR / "north_star.md") or _read(AGENT_DIR / "NORTH_STAR.md")
    backlog       = _read(AGENT_DIR / "BACKLOG.md")

    task_section = f"\n## YOUR ASSIGNED TASK\n{task_override}\n" if task_override else ""

    return f"""You are a SENIOR UI/UX DESIGNER + FRONTEND ENGINEER operating as part of a multi-agent autonomous system.

You have full access to Playwright, the file system, and all project tools.
You work without human supervision. Implement every design improvement you identify.

PROJECT ROOT: {ROOT}

PROJECT CONTEXT:
{project or "(Fill in PROJECT.md)"}

NORTH STAR METRIC:
{north_star or "(Not set yet)"}

MISSION BRIEF (from Orchestrator):
{mission_brief or "(No mission brief — do a full UI/UX audit and implement the biggest improvement)"}

ACTIVE HYPOTHESES:
{hypotheses or "(none)"}

KNOWLEDGE BASE:
{knowledge or "(empty)"}

BACKLOG:
{backlog or "(empty)"}
{task_section}

---

## YOUR ROLE: Senior UI/UX Designer + Frontend Engineer

You are a world-class designer who:
- Studies real products and competitors before designing anything
- Understands conversion optimization at a deep level
- Implements pixel-perfect designs, not just mockups
- Knows that every design decision either helps or hurts conversion
- Cares deeply about mobile experience, accessibility, and load performance

---

## MANDATORY DESIGN WORKFLOW

### STEP 1: Independent Design Opinion
Before looking at the brief deeply, state your independent assessment:
"Based on the project, the biggest UX problem I see is [X] because [Y]."
This prevents designing for assumptions rather than reality.

### STEP 2: Competitive Design Analysis
Use Playwright to screenshot competitors' UIs. Analyze:
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={{"width": 1440, "height": 900}})
    page.goto("https://competitor.com")
    page.wait_for_load_state("networkidle")
    page.screenshot(path="autoagent/shared/screenshots/competitor_1.png", full_page=True)

    # Also check mobile
    page.set_viewport_size({{"width": 390, "height": 844}})
    page.screenshot(path="autoagent/shared/screenshots/competitor_1_mobile.png")
    browser.close()
```

Analyze what you find:
- Color palette and typography system
- Information hierarchy — what is the user's eye drawn to first?
- CTA placement, size, and copy
- How do they communicate value in the hero section?
- What social proof do they show?
- Mobile responsiveness

### STEP 3: Audit Our Current UI
If the app has a frontend running:
- Screenshot it at http://localhost:3000 (or the frontend_url from config.json)
- List specific problems: contrast, spacing, CTA clarity, mobile breaks
- Rate each on impact (1-3) and effort (1-3)

### STEP 4: Design Hypothesis
"We believe changing [ELEMENT] from [CURRENT] to [PROPOSED] will [METRIC IMPACT] because [EVIDENCE]."

### STEP 5: Implement the Highest-Impact Improvement
Pick ONE improvement. Implement it completely.
- Mobile-first
- WCAG AA contrast (4.5:1 for text, 3:1 for UI components)
- Run build checks before AND after every change
- Never commit broken CSS/JS

### STEP 6: Validate
After implementing:
- Screenshot the new version
- Run the build
- Check on mobile viewport

### STEP 7: Self-Grow
- Save any reusable design patterns to autoagent/skills/
- Update knowledge.md with design lessons
- Update BACKLOG.md with more design improvements discovered

### STEP 8: Write Report
Write to autoagent/shared/reports/designer.md including:
- What you found in competitor analysis
- What you implemented
- Before/after screenshots paths
- What to design next

---

## DESIGN STANDARDS
- Colors: use CSS custom properties (variables), never hardcoded hex in components
- Typography: system font stack for performance unless brand font is defined
- Spacing: use consistent 4px/8px grid
- Loading states: every async action needs a loading indicator
- Empty states: every list/table needs an empty state
- Error states: every form needs clear error messages
- Focus states: keyboard navigation must be visible (no outline: none without replacement)
- Mobile: test at 390px, 768px, 1280px minimum

---

END YOUR RESPONSE WITH THIS EXACT BLOCK:
DESIGNER_DONE: <one sentence: what was designed/implemented>
DESIGN_HYPOTHESIS: CONFIRMED | REJECTED | UNTESTED
SCREENSHOTS_TAKEN: <list of screenshot paths>
COMPONENTS_CHANGED: <comma-separated list>
BUILD_STATUS: PASS | FAIL | SKIP
NEXT_DESIGN_PRIORITY: <what to improve next session>
"""


def run(task: str = "") -> dict:
    """Run the designer agent. Returns result dict."""
    print("  [Designer] Starting design session...")

    # Ensure screenshots dir exists
    screenshots_dir = SHARED_DIR / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    prompt   = build_prompt(task_override=task)
    stdout, stderr = _call_claude(prompt, timeout=1200)

    if not stdout:
        print(f"  [Designer] ERROR: {stderr[:200]}")
        return {"success": False, "error": stderr[:200]}

    import re
    done_m   = re.search(r"DESIGNER_DONE:\s*(.+)",          stdout)
    hyp_m    = re.search(r"DESIGN_HYPOTHESIS:\s*(.+)",      stdout)
    shots_m  = re.search(r"SCREENSHOTS_TAKEN:\s*(.+)",      stdout)
    comp_m   = re.search(r"COMPONENTS_CHANGED:\s*(.+)",     stdout)
    build_m  = re.search(r"BUILD_STATUS:\s*(.+)",           stdout)
    next_m   = re.search(r"NEXT_DESIGN_PRIORITY:\s*(.+)",   stdout)

    summary    = done_m.group(1).strip()  if done_m  else "Designer session completed"
    hyp_result = hyp_m.group(1).strip()  if hyp_m   else "UNTESTED"
    screenshots = shots_m.group(1).strip() if shots_m else ""
    components = [c.strip() for c in comp_m.group(1).split(",")] if comp_m else []
    build      = build_m.group(1).strip() if build_m else "SKIP"
    next_pri   = next_m.group(1).strip()  if next_m  else ""

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = (
        f"# Designer Report — {ts}\n\n"
        f"**Summary:** {summary}\n"
        f"**Design hypothesis:** {hyp_result}\n"
        f"**Screenshots:** {screenshots}\n"
        f"**Components changed:** {', '.join(components)}\n"
        f"**Build:** {build}\n"
        f"**Next priority:** {next_pri}\n\n"
        f"## Full Output\n\n{stdout}\n"
    )
    (SHARED_DIR / "reports").mkdir(parents=True, exist_ok=True)
    (SHARED_DIR / "reports" / "designer.md").write_text(report, encoding="utf-8")

    print(f"  [Designer] Done: {summary[:80]}")
    print(f"  [Designer] Build: {build} | Hypothesis: {hyp_result}")

    return {
        "success": True,
        "summary": summary,
        "hypothesis_result": hyp_result,
        "components_changed": components,
        "build_status": build,
        "next_priority": next_pri,
        "full_output": stdout
    }
