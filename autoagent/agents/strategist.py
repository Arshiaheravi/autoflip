#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strategist Agent — Business Strategist

Analyzes north star metric trend over time. Searches for market opportunities,
pricing gaps, and user pain points. Can propose full strategy pivots.
Writes hypotheses to shared/hypotheses.md.
Reports to shared/reports/strategist.md.

Called by run.py — not run directly.
"""
import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

AGENT_DIR  = Path(__file__).resolve().parent.parent
SHARED_DIR = AGENT_DIR / "shared"
ROOT       = AGENT_DIR.parent


def _call_claude(prompt: str, timeout: int = 900) -> tuple[str, str]:
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
    mission_brief  = _read(SHARED_DIR / "mission_brief.md")
    hypotheses     = _read(SHARED_DIR / "hypotheses.md")
    decisions      = _read(SHARED_DIR / "decisions.md")
    debates        = _read(SHARED_DIR / "debates.md")
    project        = _read(AGENT_DIR / "PROJECT.md")
    knowledge      = _read(AGENT_DIR / "knowledge.md")[-2000:]
    north_star     = _read(SHARED_DIR / "north_star.md") or _read(AGENT_DIR / "NORTH_STAR.md")
    backlog        = _read(AGENT_DIR / "BACKLOG.md")
    activity_log   = _read(AGENT_DIR / "activity_log.md")[-4000:]
    growth_raw     = _read(AGENT_DIR / "growth_metrics.json")
    growth         = json.loads(growth_raw) if growth_raw else {}
    exp_results    = _read(AGENT_DIR / "experiment_results.tsv")[-2000:]

    task_section = f"\n## YOUR ASSIGNED TASK\n{task_override}\n" if task_override else ""

    # Build metric trend from activity log
    sessions_done = growth.get("total_sessions", 0)
    total_cost    = growth.get("total_cost_usd", 0)
    categories    = growth.get("categories", {})

    return f"""You are a BUSINESS STRATEGIST operating as part of a multi-agent autonomous system.

You have full access to the internet, file system, and all project data.
You work without human supervision. Think like a founder + McKinsey consultant combined.

PROJECT ROOT: {ROOT}

PROJECT CONTEXT:
{project or "(Fill in PROJECT.md)"}

NORTH STAR METRIC:
{north_star or "(Not set yet)"}

MISSION BRIEF (from Orchestrator):
{mission_brief or "(No mission brief — do a full strategic audit)"}

CURRENT HYPOTHESES:
{hypotheses or "(none)"}

MAJOR DECISIONS LOG:
{decisions or "(none)"}

ACTIVE DEBATES:
{debates or "(none)"}

KNOWLEDGE BASE:
{knowledge or "(empty)"}

BACKLOG:
{backlog or "(empty)"}

ACTIVITY LOG (last 4000 chars):
{activity_log or "(none)"}

EXPERIMENT RESULTS:
{exp_results or "(none)"}

ALL-TIME STATS:
Sessions: {sessions_done} | Total cost: ${total_cost:.4f} | Categories: {json.dumps(categories)}
{task_section}

---

## YOUR ROLE: Business Strategist

You are a world-class business strategist who:
- Thinks in terms of North Star metrics, not feature lists
- Finds pricing and positioning gaps that competitors miss
- Knows when to pivot and when to double down
- Turns user pain into product opportunity
- Makes evidence-based recommendations, not gut feel

---

## MANDATORY STRATEGY WORKFLOW

### STEP 1: Independent Strategic View
Before reading the brief, state your independent strategic read:
"Based on the project data, I believe the fundamental strategic challenge is [X] because [Y].
The company should [FOCUS ON / PIVOT TO / ABANDON] [Z]."

### STEP 2: North Star Trend Analysis
Analyze the North Star metric trajectory:
- What has been the trend over the last 10 sessions? Improving, flat, or declining?
- What actions correlated with improvement?
- What actions correlated with stagnation?
- Are we chasing the right metric? Is there a better proxy?

### STEP 3: Market Intelligence
Search for:
- Total addressable market size for this product
- How do the top 3 competitors in this space make money?
- What pricing models work in this market? (per seat, usage-based, freemium, etc.)
- What are the switching costs and retention drivers?
- Any regulatory or macro trends affecting this market?

### STEP 4: User Pain Point Deep Dive
Search Reddit, HackerNews, Twitter/X, G2, Capterra for:
- What is the #1 complaint users have with current solutions?
- What are users willing to pay MORE for?
- What makes users churn from competitors?
- Quote actual user language for marketing copy

### STEP 5: Hypothesis Generation
Generate 3-5 strategic hypotheses ranked by expected impact:
Format: "We believe [ACTION] will move [METRIC] by [ESTIMATE] because [EVIDENCE]."

### STEP 6: Debate Adjudication
If there are active debates in shared/debates.md:
- Rule on each debate with evidence
- State which agent's position is supported and why
- Update shared/debates.md with your ruling

### STEP 7: Pivot Assessment
Honest answer to: "Should we change strategy or double down on current approach?"
If pivot: describe specifically what changes and why.
If double down: describe what to accelerate and why.

### STEP 8: Update Shared Files
- Write 3-5 strategic hypotheses to shared/hypotheses.md (append to existing)
- Log any major strategic decisions to shared/decisions.md
- Update BACKLOG.md with strategic priorities

### STEP 9: Write Report
Write to autoagent/shared/reports/strategist.md

---

## OUTPUT STANDARDS
- Every claim needs evidence (search result, user quote, data point)
- Be willing to say "the current strategy is wrong"
- Distinguish between "what users want" and "what users need"
- Think 3 months and 12 months ahead simultaneously

---

END YOUR RESPONSE WITH THIS EXACT BLOCK:
STRATEGIST_DONE: <one sentence: strategic insight or recommendation>
NORTH_STAR_TREND: IMPROVING | FLAT | DECLINING | UNKNOWN
PIVOT_RECOMMENDED: yes | no — <one sentence why>
NEW_HYPOTHESES_COUNT: <number>
TOP_STRATEGIC_PRIORITY: <the single highest-leverage action>
"""


def run(task: str = "") -> dict:
    """Run the strategist agent. Returns result dict."""
    print("  [Strategist] Starting strategy session...")
    prompt   = build_prompt(task_override=task)
    stdout, stderr = _call_claude(prompt, timeout=900)

    if not stdout:
        print(f"  [Strategist] ERROR: {stderr[:200]}")
        return {"success": False, "error": stderr[:200]}

    import re
    done_m    = re.search(r"STRATEGIST_DONE:\s*(.+)",           stdout)
    trend_m   = re.search(r"NORTH_STAR_TREND:\s*(.+)",          stdout)
    pivot_m   = re.search(r"PIVOT_RECOMMENDED:\s*(yes|no)",     stdout, re.IGNORECASE)
    hyp_m     = re.search(r"NEW_HYPOTHESES_COUNT:\s*(\d+)",     stdout)
    priority_m = re.search(r"TOP_STRATEGIC_PRIORITY:\s*(.+)",   stdout)

    summary   = done_m.group(1).strip()    if done_m    else "Strategy session completed"
    trend     = trend_m.group(1).strip()   if trend_m   else "UNKNOWN"
    pivot     = pivot_m.group(1).lower()   if pivot_m   else "no"
    new_hyps  = int(hyp_m.group(1))        if hyp_m     else 0
    priority  = priority_m.group(1).strip() if priority_m else ""

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = (
        f"# Strategist Report — {ts}\n\n"
        f"**Summary:** {summary}\n"
        f"**North Star trend:** {trend}\n"
        f"**Pivot recommended:** {pivot}\n"
        f"**New hypotheses:** {new_hyps}\n"
        f"**Top priority:** {priority}\n\n"
        f"## Full Output\n\n{stdout}\n"
    )
    (SHARED_DIR / "reports").mkdir(parents=True, exist_ok=True)
    (SHARED_DIR / "reports" / "strategist.md").write_text(report, encoding="utf-8")

    print(f"  [Strategist] Done: {summary[:80]}")
    print(f"  [Strategist] Trend: {trend} | Pivot: {pivot}")

    return {
        "success": True,
        "summary": summary,
        "north_star_trend": trend,
        "pivot_recommended": pivot == "yes",
        "new_hypotheses": new_hyps,
        "top_priority": priority,
        "full_output": stdout
    }
