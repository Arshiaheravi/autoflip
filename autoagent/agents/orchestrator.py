#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orchestrator Agent — The CEO Brain

Runs first every session. Reads the North Star metric, measures it, diagnoses
the bottleneck, searches for external intelligence, generates hypotheses, and
assigns tasks to the right specialist agents. After all agents report back,
synthesizes results and updates strategy.

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
    """Call claude.cmd non-interactively, piping prompt via stdin."""
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


def _read_shared(filename: str) -> str:
    p = SHARED_DIR / filename
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _write_shared(filename: str, content: str):
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    (SHARED_DIR / filename).write_text(content, encoding="utf-8")


def _read_agent_file(filename: str) -> str:
    p = AGENT_DIR / filename
    return p.read_text(encoding="utf-8") if p.exists() else ""


def build_orchestrator_prompt(session_num: int, past_reports: str) -> str:
    north_star   = _read_shared("north_star.md") or _read_agent_file("NORTH_STAR.md")
    hypotheses   = _read_shared("hypotheses.md")
    decisions    = _read_shared("decisions.md")
    debates      = _read_shared("debates.md")
    activity_log = _read_agent_file("activity_log.md")[-3000:] if (AGENT_DIR / "activity_log.md").exists() else ""
    knowledge    = _read_agent_file("knowledge.md")[-3000:]
    backlog      = _read_agent_file("BACKLOG.md")
    project      = _read_agent_file("PROJECT.md")
    growth_raw   = _read_agent_file("growth_metrics.json")
    growth       = json.loads(growth_raw) if growth_raw else {}

    # Last 30-session pattern summary
    sessions_done = growth.get("total_sessions", 0)
    categories    = growth.get("categories", {})
    last_self_impr = (growth.get("self_improvements") or [{}])[-1].get("what", "none yet")
    critique_hist = growth.get("self_critique_history", [])[-5:]

    return f"""You are the ORCHESTRATOR — the CEO brain of a multi-agent autonomous system.

Your job this session (session #{session_num}):
1. Read the North Star metric and measure the CURRENT number (run relevant commands)
2. Diagnose: WHY is the number where it is? What is the single biggest bottleneck?
3. Search for external intelligence: Reddit, competitors, trends relevant to this project
4. Generate 3-5 hypotheses about what will move the metric most this session
5. Decide which specialist agents are needed: engineer, researcher, designer, strategist, qa
   - Only select agents that are genuinely useful this session (not always all 5)
   - Pick 2-4 agents max per session to stay focused
6. Write shared/mission_brief.md — a battle plan every agent will read
7. Write shared/hypotheses.md — the theories you're betting on this session
8. If you see any agent debates (disagreements) — rule on them with evidence in shared/debates.md

PROJECT CONTEXT:
{project or "(No PROJECT.md found — work generically)"}

NORTH STAR:
{north_star or "(NORTH_STAR.md not filled in — ask owner to fill it or infer from project context)"}

CURRENT HYPOTHESES:
{hypotheses or "(none yet)"}

MAJOR DECISIONS LOG:
{decisions or "(none yet)"}

ACTIVE DEBATES:
{debates or "(none yet)"}

RECENT ACTIVITY (last 3000 chars):
{activity_log or "(none)"}

KNOWLEDGE BASE:
{knowledge or "(empty)"}

BACKLOG:
{backlog or "(empty)"}

PAST AGENT REPORTS (this session's earlier agents):
{past_reports or "(this is the first agent — no reports yet)"}

ALL-TIME STATS:
Sessions: {sessions_done} | Categories: {json.dumps(categories)} | Last self-improvement: {last_self_impr}
Critique history (last 5): {json.dumps(critique_hist)}

---

## YOUR MANDATORY OUTPUTS

### Step 1: Measure the North Star
Run the measurement command(s) from NORTH_STAR.md. Record the exact current number.
If no measurement command exists yet, look at the project and define one yourself.

### Step 2: Diagnosis
What is the single biggest reason the metric is where it is?
Think like a doctor: name the root cause, not symptoms.

### Step 3: External Intelligence
Search for at least 2 of these:
- Competitors in this exact space (fetch their websites)
- Reddit threads from users with this problem
- Recent blog posts / GitHub repos solving similar problems
- Pricing/positioning trends in this market

### Step 4: 3-5 Hypotheses
Format each as:
"We believe [SPECIFIC ACTION] will move the metric by [ESTIMATE] because [EVIDENCE]."
Rank them by expected impact × confidence.

### Step 5: Agent Assignments
Decide which specialists to activate and what exact task each gets.
Write it as:
AGENTS: engineer, researcher   (or whatever subset is needed)
ENGINEER_TASK: [specific task]
RESEARCHER_TASK: [specific task]
(etc.)

### Step 6: Write shared/mission_brief.md
This file is read by ALL specialist agents. Write it now.
It must include:
- The current North Star number
- The top hypothesis you're betting on
- Each agent's specific assignment
- Any constraints or context they need
- What success looks like for this session

### Step 7: Write shared/hypotheses.md
Updated list of all hypotheses, ranked by priority. Mark ones from past sessions as CONFIRMED/REJECTED.

### Step 8: Pattern Recognition (every 10 sessions)
{('Read the activity log, find patterns across the last 30 sessions. Update shared/decisions.md with what works and what does not.' if sessions_done % 10 == 0 else '(skip — next pattern recognition at session ' + str((sessions_done // 10 + 1) * 10) + ')')}

---

END YOUR RESPONSE WITH THIS EXACT BLOCK:
ORCHESTRATOR_DONE: <one sentence summary of the mission this session>
METRIC_NOW: <current North Star number or "unknown">
TOP_HYPOTHESIS: <the single hypothesis you're most betting on>
AGENTS_SELECTED: <comma-separated list: engineer,researcher,designer,strategist,qa>
"""


def run(session_num: int, past_reports: str = "") -> dict:
    """Run the orchestrator agent. Returns a dict with results."""
    print("  [Orchestrator] Building mission brief...")
    prompt   = build_orchestrator_prompt(session_num, past_reports)
    stdout, stderr = _call_claude(prompt, timeout=900)

    if not stdout:
        print(f"  [Orchestrator] ERROR: {stderr[:300]}")
        return {
            "success": False,
            "error": stderr[:300],
            "agents_selected": ["engineer"],
            "metric_now": "unknown",
            "top_hypothesis": "unknown"
        }

    # Parse structured outputs
    import re
    done_m      = re.search(r"ORCHESTRATOR_DONE:\s*(.+)", stdout)
    metric_m    = re.search(r"METRIC_NOW:\s*(.+)", stdout)
    hyp_m       = re.search(r"TOP_HYPOTHESIS:\s*(.+)", stdout)
    agents_m    = re.search(r"AGENTS_SELECTED:\s*(.+)", stdout)

    summary      = done_m.group(1).strip()    if done_m   else "Orchestrator completed"
    metric_now   = metric_m.group(1).strip()  if metric_m else "unknown"
    top_hyp      = hyp_m.group(1).strip()     if hyp_m    else "unknown"
    agents_raw   = agents_m.group(1).strip()  if agents_m else "engineer"
    agents_list  = [a.strip().lower() for a in agents_raw.split(",") if a.strip()]

    # Validate agent names
    valid_agents = {"engineer", "researcher", "designer", "strategist", "qa"}
    agents_list  = [a for a in agents_list if a in valid_agents]
    if not agents_list:
        agents_list = ["engineer"]

    # Save orchestrator's report
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = (
        f"# Orchestrator Report — {ts}\n\n"
        f"**Summary:** {summary}\n"
        f"**Metric now:** {metric_now}\n"
        f"**Top hypothesis:** {top_hyp}\n"
        f"**Agents selected:** {', '.join(agents_list)}\n\n"
        f"## Full Output\n\n{stdout}\n"
    )
    _write_shared("reports/orchestrator.md", report)

    print(f"  [Orchestrator] Done. Metric: {metric_now}. Activating: {', '.join(agents_list)}")
    print(f"  [Orchestrator] Hypothesis: {top_hyp[:80]}")

    return {
        "success": True,
        "summary": summary,
        "metric_now": metric_now,
        "top_hypothesis": top_hyp,
        "agents_selected": agents_list,
        "full_output": stdout
    }
