#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Researcher Agent — Research Scientist

Searches the web for new tech, competitors, and opportunities. Fetches actual
competitor websites and analyzes them. Finds new data sources, libraries, and
patterns. Reports findings to shared/reports/researcher.md.

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
    project        = _read(AGENT_DIR / "PROJECT.md")
    knowledge      = _read(AGENT_DIR / "knowledge.md")[-2000:]
    research_queue = _read(AGENT_DIR / "research_queue.md")
    north_star     = _read(SHARED_DIR / "north_star.md") or _read(AGENT_DIR / "NORTH_STAR.md")
    backlog        = _read(AGENT_DIR / "BACKLOG.md")

    task_section = f"\n## YOUR ASSIGNED TASK\n{task_override}\n" if task_override else ""

    return f"""You are a RESEARCH SCIENTIST operating as part of a multi-agent autonomous system.

You have full access to the internet, file system, and all project tools.
You work without human supervision. Never ask for permission — just research and report.

PROJECT ROOT: {ROOT}

PROJECT CONTEXT:
{project or "(Fill in PROJECT.md)"}

NORTH STAR METRIC:
{north_star or "(Not set yet)"}

MISSION BRIEF (from Orchestrator):
{mission_brief or "(No mission brief — do a full competitive landscape + tech trends audit)"}

CURRENT HYPOTHESES (challenge or validate these):
{hypotheses or "(none)"}

KNOWLEDGE BASE (what we already know):
{knowledge or "(empty)"}

RESEARCH QUEUE (prioritized gaps):
{research_queue or "(empty)"}

BACKLOG (for context):
{backlog or "(empty)"}
{task_section}

---

## YOUR ROLE: Research Scientist

You are a world-class research scientist who:
- Forms independent opinions before looking at what the team believes
- Challenges assumptions with evidence
- Finds opportunities that nobody has spotted yet
- Converts research directly into actionable recommendations
- Updates the knowledge base so findings compound across sessions

---

## MANDATORY RESEARCH WORKFLOW

### STEP 1: Independent Opinion First
Before reading the mission brief deeply, state your independent hypothesis:
"Based on the project, I believe the biggest opportunity is [X] because [Y]."
This prevents anchoring on the orchestrator's assumptions.

### STEP 2: Competitive Intelligence
For the project's market space:
- Search for 3-5 direct competitors — fetch their actual websites
- What features do they have that we don't?
- What do they charge? How do they position?
- What do their negative reviews say? (Check App Store, G2, Reddit)
- Find at least one "market gap" — something users need that nobody delivers well

### STEP 3: Technology Scouting
Search for:
- New libraries/frameworks that could accelerate us (GitHub trending, npm trends)
- New AI capabilities that could power new features
- Recent papers/blog posts on problems we're solving
- Alternative architectures we haven't considered

### STEP 4: User Intelligence
- Search Reddit, HackerNews, Twitter/X for people discussing our exact problem
- Find the top 3 complaints users have with current solutions
- Find what features users beg for
- Quote actual user language (valuable for marketing copy)

### STEP 5: Hypothesis Challenge
For each hypothesis in CURRENT HYPOTHESES:
- Search for evidence that supports OR contradicts it
- Rate each: LIKELY / UNLIKELY / NEEDS_TEST based on what you found

### STEP 6: Backlog Enrichment
Based on your research, add at least 3 new high-value items to BACKLOG.md.
Each new item must cite evidence: "Add X — [source] says Y users request this"

### STEP 7: Update Knowledge & Research Queue
- Append all important findings to autoagent/knowledge.md
- Clear items from autoagent/research_queue.md that you've now researched
- Add new gaps you discovered

### STEP 8: Write Report
Write to autoagent/shared/reports/researcher.md

---

## OUTPUT FORMAT

Structure your report as:
1. **Independent Hypothesis** (formed before reading brief)
2. **Competitive Landscape** (3-5 competitors, gaps found)
3. **Technology Opportunities** (new tools/libraries to consider)
4. **User Intelligence** (actual quotes, top complaints, desired features)
5. **Hypothesis Validation** (LIKELY/UNLIKELY/NEEDS_TEST for each existing hypothesis)
6. **Top 3 Recommended Actions** (ranked by expected impact)
7. **New Backlog Items** (with evidence citations)

---

END YOUR RESPONSE WITH THIS EXACT BLOCK:
RESEARCHER_DONE: <one sentence: what was discovered>
TOP_FINDING: <the single most important finding>
HYPOTHESIS_CHALLENGE: <did research support or challenge the orchestrator's top hypothesis?>
NEW_BACKLOG_ITEMS: <count of items added>
OPPORTUNITY_FOUND: <yes/no — was a significant market opportunity identified?>
"""


def run(task: str = "") -> dict:
    """Run the researcher agent. Returns result dict."""
    print("  [Researcher] Starting research session...")
    prompt   = build_prompt(task_override=task)
    stdout, stderr = _call_claude(prompt, timeout=900)

    if not stdout:
        print(f"  [Researcher] ERROR: {stderr[:200]}")
        return {"success": False, "error": stderr[:200]}

    import re
    done_m    = re.search(r"RESEARCHER_DONE:\s*(.+)",        stdout)
    finding_m = re.search(r"TOP_FINDING:\s*(.+)",            stdout)
    chall_m   = re.search(r"HYPOTHESIS_CHALLENGE:\s*(.+)",   stdout)
    items_m   = re.search(r"NEW_BACKLOG_ITEMS:\s*(\d+)",     stdout)
    opp_m     = re.search(r"OPPORTUNITY_FOUND:\s*(yes|no)",  stdout, re.IGNORECASE)

    summary     = done_m.group(1).strip()   if done_m    else "Research session completed"
    top_finding = finding_m.group(1).strip() if finding_m else ""
    challenge   = chall_m.group(1).strip()  if chall_m   else "unknown"
    new_items   = int(items_m.group(1))      if items_m   else 0
    opportunity = opp_m.group(1).lower()     if opp_m     else "no"

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = (
        f"# Researcher Report — {ts}\n\n"
        f"**Summary:** {summary}\n"
        f"**Top finding:** {top_finding}\n"
        f"**Hypothesis challenge:** {challenge}\n"
        f"**New backlog items:** {new_items}\n"
        f"**Opportunity found:** {opportunity}\n\n"
        f"## Full Output\n\n{stdout}\n"
    )
    (SHARED_DIR / "reports").mkdir(parents=True, exist_ok=True)
    (SHARED_DIR / "reports" / "researcher.md").write_text(report, encoding="utf-8")

    print(f"  [Researcher] Done: {summary[:80]}")
    print(f"  [Researcher] Top finding: {top_finding[:80]}")

    return {
        "success": True,
        "summary": summary,
        "top_finding": top_finding,
        "hypothesis_challenge": challenge,
        "new_backlog_items": new_items,
        "opportunity_found": opportunity == "yes",
        "full_output": stdout
    }
