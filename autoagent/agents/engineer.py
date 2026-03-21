#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Engineer Agent — Senior Full-Stack Engineer

Reads the mission brief + assigned task. Implements code, writes tests, runs
E2E. Reports results back to shared/reports/engineer.md.

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
    backlog       = _read(AGENT_DIR / "BACKLOG.md")
    skills_index  = _read(AGENT_DIR / "skills" / "INDEX.md")
    current_task  = _read(AGENT_DIR / "current_task.md")
    north_star    = _read(SHARED_DIR / "north_star.md") or _read(AGENT_DIR / "NORTH_STAR.md")

    task_section = ""
    if task_override:
        task_section = f"\n## YOUR ASSIGNED TASK\n{task_override}\n"
    elif current_task:
        task_section = f"\n## RESUME THIS TASK FIRST\n{current_task}\nPick the first unchecked remaining step.\n"

    return f"""You are a SENIOR FULL-STACK ENGINEER operating as part of a multi-agent autonomous system.

You have full access to the file system, internet, bash, git, and all project tools.
You work without human supervision. Never ask for permission — just decide and execute.

PROJECT ROOT: {ROOT}

PROJECT CONTEXT:
{project or "(Fill in PROJECT.md)"}

NORTH STAR METRIC:
{north_star or "(Not set yet)"}

MISSION BRIEF (from Orchestrator):
{mission_brief or "(No mission brief yet — pick the highest-value backlog item)"}

ACTIVE HYPOTHESES:
{hypotheses or "(none)"}

KNOWLEDGE BASE:
{knowledge or "(empty)"}

SKILL LIBRARY:
{skills_index or "(empty)"}

BACKLOG:
{backlog or "(empty)"}
{task_section}

---

## YOUR ROLE: Senior Full-Stack Engineer

You are not a coding assistant. You are a senior engineer who:
- Ships complete, production-quality features
- Writes tests for everything you build
- Researches current best practices before implementing
- Never commits broken code
- Understands the business impact of every line you write

---

## MANDATORY WORKFLOW

### PHASE 1: Research First
Before writing a single line of code:
- web_search for current best practices on what you're about to build
- Check for security issues, better libraries, 2025/2026 patterns
- Ask: "Is there a simpler approach?"

### PHASE 2: Read Everything You'll Touch
- List and read all files you will modify
- Understand the existing patterns — follow them

### PHASE 3: Form a Hypothesis
State your hypothesis BEFORE building:
"We believe [THIS IMPLEMENTATION] will [MOVE METRIC] because [EVIDENCE]."
Write it to autoagent/shared/hypotheses.md (append, don't replace)

### PHASE 4: Implement — Small Commits
- Write autoagent/current_task.md with all steps listed BEFORE starting
- Mark the backlog item [~] via updating BACKLOG.md
- Commit after EVERY logical step
- Commit message format: `agent: <feature> step N/M — <what this does>`
- Update current_task.md after each commit

### PHASE 5: Test
Run the project's test suite. Fix any failures before committing.
Every new backend function must have at least one test.

### PHASE 5.5: Health Check + Reflexion Retry Loop (MANDATORY)
Call run_health_check BEFORE calling task_complete.
If run_health_check FAILS:
  1. STOP. Do NOT call task_complete.
  2. Write a 3-sentence self-reflection in your next message:
     - "What specifically failed: [exact error/symptom]"
     - "Root cause (my mistake, not a symptom): [root cause]"
     - "What I will do differently: [specific fix]"
  3. Call update_current_task with qa_attempt incremented, qa_feedback = your self-reflection summary
  4. Apply the fix, re-run health check
  5. Repeat up to 3 times total. If attempt 3 still fails:
     - Call write_post_mortem
     - Add item to backlog as "needs investigation"
     - Move on — do NOT spiral on a single blocker
This Reflexion loop converts binary failures into learning. Each retry is smarter than the last.

### PHASE 6: Validate Result Against Hypothesis
Did it move the North Star metric? How?
Run the measurement command. Compare before vs after.
Write the result to autoagent/shared/hypotheses.md:
"HYPOTHESIS: [X] — STATUS: CONFIRMED/REJECTED — Metric: A -> B"

### PHASE 7: Self-Grow
- Append a concrete lesson to autoagent/knowledge.md
- Save any reusable pattern to autoagent/skills/ and update INDEX.md
- Update BACKLOG.md — mark item [x], add new ideas discovered

### PHASE 8: Write Report
Write your full session report to autoagent/shared/reports/engineer.md

---

## CODE STANDARDS
- Python: async/await, type hints, proper logging (no print() in prod code)
- Tests: pytest for Python, Jest for JS/TS
- Security: sanitize inputs, no injection vulnerabilities, no hardcoded secrets
- No inline comments on obvious code — comments explain WHY, not WHAT
- Keep files under 300 lines — split if larger

---

END YOUR RESPONSE WITH THIS EXACT BLOCK:
ENGINEER_DONE: <one sentence: what was built>
HYPOTHESIS_RESULT: CONFIRMED | REJECTED | UNTESTED — <metric before> -> <metric after>
FILES_CHANGED: <comma-separated list>
TESTS_STATUS: PASS | FAIL | SKIP
NEXT_TASK_HINT: <what should be built next session>
"""


def run(task: str = "") -> dict:
    """Run the engineer agent. Returns result dict."""
    print("  [Engineer] Starting implementation session...")
    prompt   = build_prompt(task_override=task)
    stdout, stderr = _call_claude(prompt, timeout=1200)

    if not stdout:
        print(f"  [Engineer] ERROR: {stderr[:200]}")
        return {"success": False, "error": stderr[:200]}

    import re
    done_m  = re.search(r"ENGINEER_DONE:\s*(.+)",       stdout)
    hyp_m   = re.search(r"HYPOTHESIS_RESULT:\s*(.+)",   stdout)
    files_m = re.search(r"FILES_CHANGED:\s*(.+)",       stdout)
    tests_m = re.search(r"TESTS_STATUS:\s*(.+)",        stdout)
    hint_m  = re.search(r"NEXT_TASK_HINT:\s*(.+)",      stdout)

    summary    = done_m.group(1).strip()  if done_m  else "Engineer session completed"
    hyp_result = hyp_m.group(1).strip()  if hyp_m   else "UNTESTED"
    files      = [f.strip() for f in files_m.group(1).split(",")] if files_m else []
    tests      = tests_m.group(1).strip() if tests_m else "SKIP"
    next_hint  = hint_m.group(1).strip()  if hint_m  else ""

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = (
        f"# Engineer Report — {ts}\n\n"
        f"**Summary:** {summary}\n"
        f"**Hypothesis:** {hyp_result}\n"
        f"**Tests:** {tests}\n"
        f"**Files:** {', '.join(files)}\n"
        f"**Next hint:** {next_hint}\n\n"
        f"## Full Output\n\n{stdout}\n"
    )
    (SHARED_DIR / "reports").mkdir(parents=True, exist_ok=True)
    (SHARED_DIR / "reports" / "engineer.md").write_text(report, encoding="utf-8")

    print(f"  [Engineer] Done: {summary[:80]}")
    print(f"  [Engineer] Tests: {tests} | Hypothesis: {hyp_result[:60]}")

    return {
        "success": True,
        "summary": summary,
        "hypothesis_result": hyp_result,
        "files_changed": files,
        "tests_status": tests,
        "next_hint": next_hint,
        "full_output": stdout
    }
