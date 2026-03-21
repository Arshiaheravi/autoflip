#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meta-Agent — The Self-Improvement Brain

Runs independently from the main agent. Its ONLY job: make the agent system smarter.

Usage:
    py -X utf8 autoagent/meta/run.py            # run forever (every 3h)
    py -X utf8 autoagent/meta/run.py --once     # one session then exit
    py -X utf8 autoagent/meta/run.py --tasks 3  # exactly 3 sessions then exit

Every session:
  OBSERVE     → read all logs, find failures, measure current quality score
  RESEARCH    → web search for new AI agent patterns, techniques, architectures
  DIAGNOSE    → identify the single biggest weakness in the current agent system
  HYPOTHESIZE → form a ranked theory about what improvement will move the score most
  EXPERIMENT  → test the hypothesis (modify prompt, measure result)
  IMPLEMENT   → write the improvement to the actual agent files
  BENCHMARK   → score before/after, record result
  LOG         → update findings.md, experiments/, backlog.md
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─────────────────────────── Paths ────────────────────────────
META_DIR        = Path(__file__).resolve().parent          # autoagent/meta/
AGENT_DIR       = META_DIR.parent                          # autoagent/
ROOT            = AGENT_DIR.parent                         # project root

FINDINGS_FILE    = META_DIR / "findings.md"
BACKLOG_FILE     = META_DIR / "backlog.md"
EXPERIMENTS_DIR  = META_DIR / "experiments"
BENCHMARKS_DIR   = META_DIR / "benchmarks"
SESSION_LOG_FILE = META_DIR / "session_log.md"
RATE_LIMIT_FILE  = META_DIR / "rate_limit.json"
MISSION_FILE     = META_DIR / "MISSION.md"

EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)

# Claude CLI path (VS Code / npm global install)
CLAUDE_CMD = os.path.join(os.environ.get("APPDATA", ""), "npm", "claude.cmd")

# How long to sleep between meta-agent sessions (seconds)
SESSION_INTERVAL = 3 * 60 * 60   # 3 hours


# ─────────────────────────── Claude CLI call ──────────────────

def _call_claude(prompt: str, timeout: int = 900) -> tuple[str, str]:
    """
    Call claude.cmd via subprocess, piping the prompt through a temp file.
    Strips ANTHROPIC_API_KEY from env so the CLI uses its own auth (VS Code mode).
    Returns (stdout, stderr).
    """
    if not os.path.exists(CLAUDE_CMD):
        err = f"claude.cmd not found at {CLAUDE_CMD}. Install with: npm install -g @anthropic-ai/claude-code"
        print(f"[meta] ERROR: {err}", file=sys.stderr)
        return "", err

    # Write prompt to temp file to avoid shell quoting issues
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".txt", delete=False
    ) as tmp:
        tmp.write(prompt)
        tmp_path = tmp.name

    # Remove API key from env — let the CLI use its own stored credentials
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)

    # Windows: pipe through `type` so the file contents reach claude's stdin
    cmd = f'type "{tmp_path}" | "{CLAUDE_CMD}" --print --dangerously-skip-permissions'

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
        )
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "", f"Claude call timed out after {timeout}s"
    except Exception as exc:
        return "", f"Claude call failed: {exc}"
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ─────────────────────────── Log reading ──────────────────────

def _read_agent_logs() -> str:
    """
    Collect context from all agent memory files.
    Returns a single combined string ready to be injected into the meta-prompt.
    """
    parts = []

    # Activity log — last 5000 chars so we see recent failures, not ancient history
    activity_log = AGENT_DIR / "activity_log.md"
    if activity_log.exists():
        text = activity_log.read_text(encoding="utf-8", errors="replace")
        tail = text[-5000:] if len(text) > 5000 else text
        parts.append(f"=== activity_log.md (last 5000 chars) ===\n{tail}")
    else:
        parts.append("=== activity_log.md: NOT FOUND ===")

    # North star metric
    north_star = AGENT_DIR / "shared" / "north_star.md"
    if north_star.exists():
        parts.append(f"=== shared/north_star.md ===\n{north_star.read_text(encoding='utf-8', errors='replace')}")

    # Hypotheses
    hypotheses = AGENT_DIR / "shared" / "hypotheses.md"
    if hypotheses.exists():
        parts.append(f"=== shared/hypotheses.md ===\n{hypotheses.read_text(encoding='utf-8', errors='replace')}")

    # Growth metrics JSON
    growth_file = AGENT_DIR / "growth_metrics.json"
    if growth_file.exists():
        parts.append(f"=== growth_metrics.json ===\n{growth_file.read_text(encoding='utf-8', errors='replace')}")

    # All report files
    reports_dir = AGENT_DIR / "shared" / "reports"
    if reports_dir.exists():
        report_files = sorted(reports_dir.glob("*.md"))
        for rpt in report_files[-5:]:   # last 5 reports only — avoid token bloat
            parts.append(f"=== shared/reports/{rpt.name} ===\n{rpt.read_text(encoding='utf-8', errors='replace')}")

    return "\n\n".join(parts)


# ─────────────────────────── Session scoring ──────────────────

def _score_last_sessions() -> dict:
    """
    Parse activity_log.md to score recent sessions.
    Looks for keywords that indicate completion, retries, and push success.
    Returns {"score": float, "trend": str, "weakest_area": str, "session_count": int}.
    """
    activity_log = AGENT_DIR / "activity_log.md"
    if not activity_log.exists():
        return {
            "score": 0.0,
            "trend": "unknown",
            "weakest_area": "no activity log found",
            "session_count": 0,
        }

    text = activity_log.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    # Heuristic session boundaries — look for date/session headers
    session_blocks: list[list[str]] = []
    current_block: list[str] = []
    for line in lines:
        stripped = line.strip()
        # Common session header patterns
        if stripped.startswith("## Session") or stripped.startswith("## 20") or stripped.startswith("# Session"):
            if current_block:
                session_blocks.append(current_block)
            current_block = [line]
        else:
            current_block.append(line)
    if current_block:
        session_blocks.append(current_block)

    # Score the last 10 sessions
    scored_sessions = []
    for block in session_blocks[-10:]:
        block_text = "\n".join(block).lower()

        # Completion: did the session finish a task?
        # Supports both API-mode keywords and VS Code CLI activity log format
        # (which uses "**Outcome:**", "**What was done:**", "eliminates", "users can now", etc.)
        completed = any(
            kw in block_text
            for kw in [
                "task complete", "task_complete", "completed", "pushed", "git push", "done",
                "**outcome:**", "outcome:", "what was done", "users can now", "eliminates",
                "now persist", "now sync", "now shown", "now see", "now appear",
            ]
        )
        # Retries: did it hit phase 3.5 retries?
        retry_count = sum(
            1 for kw in ["retry", "qa attempt", "attempt 2", "attempt 3", "failed:"]
            if kw in block_text
        )
        # Push success: API mode logs "git push"; VS Code CLI mode doesn't push (no remote)
        # Give partial credit if session completed even without a push (VS Code mode)
        push_success = (
            "git push" in block_text
            or "pushed" in block_text
            or completed  # VS Code mode: no remote configured, completion is sufficient
        )

        # Build score: max 10
        score = 0.0
        score += 4.0 if completed else 0.0
        score += max(0.0, 3.0 - retry_count)   # 3 points minus 1 per retry
        score += 3.0 if push_success else 0.0

        scored_sessions.append(
            {"score": score, "completed": completed, "retries": retry_count, "pushed": push_success}
        )

    if not scored_sessions:
        return {
            "score": 0.0,
            "trend": "unknown",
            "weakest_area": "no parseable sessions in activity log",
            "session_count": 0,
        }

    avg_score = sum(s["score"] for s in scored_sessions) / len(scored_sessions)

    # Trend: compare first half vs second half
    mid = max(1, len(scored_sessions) // 2)
    first_half_avg = sum(s["score"] for s in scored_sessions[:mid]) / mid
    second_half_avg = sum(s["score"] for s in scored_sessions[mid:]) / max(1, len(scored_sessions) - mid)

    if second_half_avg > first_half_avg + 0.5:
        trend = "improving"
    elif second_half_avg < first_half_avg - 0.5:
        trend = "declining"
    else:
        trend = "flat"

    # Weakest area
    total_retries = sum(s["retries"] for s in scored_sessions)
    total_no_complete = sum(1 for s in scored_sessions if not s["completed"])
    total_no_push = sum(1 for s in scored_sessions if not s["pushed"])

    areas = {
        "retry rate (Phase 3.5 QA loops)": total_retries,
        "task completion rate": total_no_complete,
        "push/commit success": total_no_push,
    }
    weakest_area = max(areas, key=lambda k: areas[k])

    return {
        "score": round(avg_score, 2),
        "trend": trend,
        "weakest_area": weakest_area,
        "session_count": len(scored_sessions),
        "breakdown": scored_sessions,
    }


# ─────────────────────────── Source reading ───────────────────

def _read_agent_source() -> str:
    """
    Read the SYSTEM_PROMPT section of run.py and the full orchestrator.py.
    Returns combined source string.
    """
    parts = []

    run_py = AGENT_DIR / "run.py"
    if run_py.exists():
        text = run_py.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        # Extract lines 857-1100 (SYSTEM_PROMPT + session workflow)
        start = max(0, 856)
        end = min(len(lines), 1100)
        excerpt = "\n".join(lines[start:end])
        parts.append(
            f"=== autoagent/run.py lines {start+1}–{end} (SYSTEM_PROMPT + workflow) ===\n{excerpt}"
        )
    else:
        parts.append("=== autoagent/run.py: NOT FOUND ===")

    orchestrator = AGENT_DIR / "agents" / "orchestrator.py"
    if orchestrator.exists():
        parts.append(
            f"=== autoagent/agents/orchestrator.py ===\n"
            f"{orchestrator.read_text(encoding='utf-8', errors='replace')}"
        )
    else:
        parts.append("=== autoagent/agents/orchestrator.py: NOT FOUND ===")

    return "\n\n".join(parts)


# ─────────────────────────── Benchmark reading ────────────────

def _read_last_benchmarks(n: int = 10) -> str:
    """Read the last n benchmark entries across all benchmark files."""
    all_entries: list[tuple[str, str]] = []

    for bm_file in sorted(BENCHMARKS_DIR.glob("*.md")):
        if bm_file.name == "README.md":
            continue
        text = bm_file.read_text(encoding="utf-8", errors="replace")
        all_entries.append((bm_file.stem, text))

    if not all_entries:
        return "No benchmark history yet — this is session #1."

    # Return last n files' content
    recent = all_entries[-n:]
    return "\n\n".join(f"=== benchmark {date} ===\n{content}" for date, content in recent)


# ─────────────────────────── Meta-prompt builder ──────────────

def _build_meta_prompt(session_num: int) -> str:
    """
    Build the full meta-agent prompt.
    Includes mission, quality scores, benchmarks, agent logs, source, findings, backlog.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Load supporting content
    mission = MISSION_FILE.read_text(encoding="utf-8", errors="replace") if MISSION_FILE.exists() else "(MISSION.md not found)"
    quality = _score_last_sessions()
    benchmarks = _read_last_benchmarks(10)
    agent_logs = _read_agent_logs()
    agent_source = _read_agent_source()
    findings = FINDINGS_FILE.read_text(encoding="utf-8", errors="replace") if FINDINGS_FILE.exists() else "(findings.md not found)"
    backlog = BACKLOG_FILE.read_text(encoding="utf-8", errors="replace") if BACKLOG_FILE.exists() else "(backlog.md not found)"

    quality_summary = (
        f"Session count analysed: {quality['session_count']}\n"
        f"Average quality score: {quality['score']} / 10\n"
        f"Trend: {quality['trend']}\n"
        f"Weakest area: {quality['weakest_area']}"
    )

    prompt = f"""You are the META-AGENT — a superintelligent self-improvement system.
Your ONLY job: make the agent team smarter. You have full access to everything.

Today: {now_str}
Meta-Agent Session: #{session_num}

You are like a human brain studying itself — observing your own thought patterns,
finding weaknesses, researching better techniques, and rewiring your own neural pathways.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MISSION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{mission}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT SESSION QUALITY SCORES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{quality_summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BENCHMARK HISTORY (last 10 sessions)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{benchmarks}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AGENT LOGS (failures, retries, stuck points)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{agent_logs}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT SYSTEM_PROMPT + ORCHESTRATOR SOURCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{agent_source}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
META-AGENT FINDINGS (what we learned so far)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{findings}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
META-AGENT BACKLOG
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{backlog}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR MANDATORY WORKFLOW — FOLLOW IN ORDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OBSERVE phase:
  Read the logs above. Where did the agent fail? Retry? Get stuck? Produce weak output?
  List every failure mode you see with a severity rating (1=minor, 2=significant, 3=critical).

RESEARCH phase (MANDATORY — do at least 3 web searches every session):
  Use web_search for at least 3 of these each session:
  - "2026 AI agent self-improvement techniques"
  - "LLM agent failure modes and fixes"
  - "autonomous agent prompt engineering best practices"
  - "ReAct agent architecture improvements"
  - "chain of thought vs tree of thought 2026"
  - "multi-agent debate systems research"
  - "AI agent memory architectures"
  - "LLM agent tool use optimization"
  - "Reflexion autonomous agents self-reflection"
  - "AutoGen multi-agent framework 2026"
  Record every useful finding. Cite the source.

DIAGNOSE phase:
  Based on OBSERVE + RESEARCH, what is the SINGLE BIGGEST weakness right now?
  State it precisely. One sentence.

HYPOTHESIZE phase:
  Form exactly 3 ranked hypotheses (H1 = most impactful, H3 = least):
  Format:
    H1: [change] → expected improvement: [metric] by [amount]
    H2: [change] → expected improvement: [metric] by [amount]
    H3: [change] → expected improvement: [metric] by [amount]
  Pick H1. If you are less than 70% confident, pick H2.

EXPERIMENT phase:
  Design a measurable test for your chosen hypothesis.
  - What is the baseline? (record it as a number)
  - What is the change?
  - How will you measure improvement?
  Write your experiment plan to:
    autoagent/meta/experiments/{today}-[hypothesis-short-name].md

IMPLEMENT phase:
  Make the actual change. You have full access to:
  - autoagent/run.py     (edit SYSTEM_PROMPT, tools, workflow phases)
  - autoagent/agents/*.py  (edit any specialist agent)
  - autoagent/shared/*.md  (update shared memory and hypotheses)
  - autoagent/meta/*.md    (update your own files)
  Be bold. If the entire SYSTEM_PROMPT structure is wrong, rewrite it.
  If an agent is redundant, merge it. If a phase is missing, add it.
  Document every edit with a comment: # META: [reason] [date]

BENCHMARK phase:
  Write a quality score entry to: autoagent/meta/benchmarks/{today}.md
  Include:
  - Session #{session_num}
  - Baseline score: [number from quality analysis above]
  - Change implemented: [what you changed]
  - Predicted impact: [which metric, by how much]
  - Actual measurement method: [how to verify it worked]

LOG phase:
  Append your findings to autoagent/meta/findings.md under ## Discoveries.
  Format:
    ### {today} — Session #{session_num}
    **Finding:** [what you learned]
    **Evidence:** [what log lines / patterns led you here]
    **Change made:** [file:line — what was changed]
    **Confidence:** [high/medium/low]

  Update autoagent/meta/backlog.md:
  - Mark completed items [x]
  - Add new discoveries as new items
  - Re-prioritize based on quality score impact

COMMIT phase (MANDATORY — always commit agent improvements):
  git add autoagent/
  git commit -m "meta: [short description of what was improved and why]"
  Do NOT commit project code (frontend/, backend/, src/).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INVIOLABLE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- NEVER touch project code (frontend/, backend/, src/, any project files)
- ALWAYS measure before changing — record baseline before any edit
- ALWAYS commit agent improvements via git
- Think like a researcher: evidence first, intuition second
- Be bold: if the entire SYSTEM_PROMPT approach is wrong, rewrite it
- Document EVERY decision in meta/findings.md
- If you find a hypothesis that would take multiple sessions: add it to backlog.md
- The session quality score is the ONLY success metric that matters

Now execute all phases in order. Think deeply. Be specific. Make changes that will measurably
move the session quality score up. The agent is counting on you.
"""
    return prompt.strip()


# ─────────────────────────── Rate limit handling ──────────────

def _check_rate_limit() -> bool:
    """
    Returns True if we can proceed now.
    If rate limited, prints remaining wait time and sleeps.
    Returns False if the rate limit file is corrupted.
    """
    if not RATE_LIMIT_FILE.exists():
        return True

    try:
        data = json.loads(RATE_LIMIT_FILE.read_text(encoding="utf-8"))
        retry_after = data.get("retry_after_epoch", 0)
        now = time.time()

        if now >= retry_after:
            # Rate limit window has passed — delete the file and continue
            RATE_LIMIT_FILE.unlink(missing_ok=True)
            return True

        wait_secs = int(retry_after - now)
        wait_mins = wait_secs // 60
        wait_secs_rem = wait_secs % 60
        print(
            f"[meta] Rate limited. Waiting {wait_mins}m {wait_secs_rem}s "
            f"(until {datetime.fromtimestamp(retry_after).strftime('%H:%M:%S')})..."
        )

        # Sleep in 60-second chunks so we can print progress
        while time.time() < retry_after:
            remaining = int(retry_after - time.time())
            if remaining > 0:
                sleep_chunk = min(60, remaining)
                time.sleep(sleep_chunk)
                remaining = int(retry_after - time.time())
                if remaining > 0:
                    print(f"[meta] Still waiting... {remaining}s remaining")

        RATE_LIMIT_FILE.unlink(missing_ok=True)
        print("[meta] Rate limit window passed. Resuming.")
        return True

    except (json.JSONDecodeError, KeyError, TypeError):
        # Corrupted file — remove and continue
        RATE_LIMIT_FILE.unlink(missing_ok=True)
        return True


def _save_rate_limit(message: str) -> None:
    """
    Parse a rate limit message from Claude CLI output and save retry time.
    Looks for patterns like "retry after X seconds" or "retry-after: TIMESTAMP".
    """
    import re

    retry_epoch = None

    # Pattern: "retry after N seconds"
    m = re.search(r"retry after (\d+) second", message, re.IGNORECASE)
    if m:
        retry_epoch = time.time() + int(m.group(1)) + 5   # +5s buffer

    # Pattern: "retry-after: EPOCH_TIMESTAMP"
    if not retry_epoch:
        m = re.search(r"retry[-_]after[:\s]+(\d{10,})", message, re.IGNORECASE)
        if m:
            retry_epoch = float(m.group(1)) + 5

    # Pattern: "available in Xm Ys" or "available in X minutes"
    if not retry_epoch:
        m = re.search(r"available in (\d+)m\s*(\d+)?s?", message, re.IGNORECASE)
        if m:
            mins = int(m.group(1))
            secs = int(m.group(2)) if m.group(2) else 0
            retry_epoch = time.time() + mins * 60 + secs + 5

    if not retry_epoch:
        # Default fallback: 1 hour
        retry_epoch = time.time() + 3600
        print("[meta] Could not parse retry time from rate limit message. Defaulting to 1 hour.")

    data = {
        "retry_after_epoch": retry_epoch,
        "retry_at_human": datetime.fromtimestamp(retry_epoch).strftime("%Y-%m-%d %H:%M:%S"),
        "message_excerpt": message[:300],
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    RATE_LIMIT_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(
        f"[meta] Rate limit saved. Will retry at "
        f"{data['retry_at_human']}"
    )


# ─────────────────────────── Session writer ───────────────────

def _write_session_log(session_num: int, output: str, quality: dict) -> None:
    """Append session results to session_log.md."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = (
        f"\n\n---\n"
        f"## Session #{session_num} — {now_str}\n\n"
        f"**Quality Score:** {quality['score']} / 10  |  "
        f"**Trend:** {quality['trend']}  |  "
        f"**Weakest Area:** {quality['weakest_area']}\n\n"
        f"### Claude Output\n\n"
        f"{output}\n"
    )

    if SESSION_LOG_FILE.exists():
        existing = SESSION_LOG_FILE.read_text(encoding="utf-8", errors="replace")
        SESSION_LOG_FILE.write_text(existing + entry, encoding="utf-8")
    else:
        header = "# Meta-Agent Session Log\n\nAll meta-agent sessions recorded here.\n"
        SESSION_LOG_FILE.write_text(header + entry, encoding="utf-8")


def _write_benchmark(session_num: int, quality: dict, output: str) -> None:
    """Append a benchmark entry for today."""
    today = datetime.now().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%H:%M:%S")
    bm_file = BENCHMARKS_DIR / f"{today}.md"

    entry = (
        f"\n## Session #{session_num} — {now_str}\n\n"
        f"- Quality score: {quality['score']} / 10\n"
        f"- Trend: {quality['trend']}\n"
        f"- Sessions analysed: {quality['session_count']}\n"
        f"- Weakest area: {quality['weakest_area']}\n\n"
        f"### Meta Output Summary\n\n"
        f"{output[:1000]}{'...(truncated)' if len(output) > 1000 else ''}\n"
    )

    if bm_file.exists():
        existing = bm_file.read_text(encoding="utf-8", errors="replace")
        bm_file.write_text(existing + entry, encoding="utf-8")
    else:
        header = f"# Benchmarks — {today}\n\n"
        bm_file.write_text(header + entry, encoding="utf-8")


# ─────────────────────────── Session runner ───────────────────

def run_meta_session(session_num: int) -> None:
    """Run a single meta-agent session."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    separator = "═" * 60

    print(f"\n{separator}")
    print(f"  META-AGENT  |  Session #{session_num}  |  {now_str}")
    print(separator)

    # Step 1: Read logs
    print("[meta] Reading agent logs...")
    quality = _score_last_sessions()
    print(
        f"[meta] Quality score: {quality['score']}/10  |  "
        f"Trend: {quality['trend']}  |  "
        f"Weakest: {quality['weakest_area']}"
    )

    # Step 2: Build prompt
    print("[meta] Building meta-prompt...")
    prompt = _build_meta_prompt(session_num)
    prompt_tokens_est = len(prompt) // 4
    print(f"[meta] Prompt size ~{prompt_tokens_est:,} tokens. Calling Claude (timeout=1200s)...")

    # Step 3: Call Claude
    stdout, stderr = _call_claude(prompt, timeout=1200)

    # Step 4: Handle rate limiting
    if stderr and any(
        kw in stderr.lower()
        for kw in ["rate limit", "rate_limit", "too many requests", "429", "overloaded"]
    ):
        print(f"[meta] Rate limited by Claude API.")
        _save_rate_limit(stderr)
        return

    if not stdout and stderr:
        print(f"[meta] Claude returned no output. STDERR:\n{stderr[:500]}")
        return

    # Step 5: Print output
    print(f"\n{separator}")
    print("  META-AGENT OUTPUT")
    print(separator)
    print(stdout)

    # Step 6: Write session log + benchmark
    _write_session_log(session_num, stdout, quality)
    _write_benchmark(session_num, quality, stdout)
    print(f"\n[meta] Session #{session_num} complete. Logged to session_log.md and benchmarks/.")


# ─────────────────────────── Main ─────────────────────────────

def main() -> None:
    once        = "--once" in sys.argv
    tasks_limit = None

    if "--tasks" in sys.argv:
        idx = sys.argv.index("--tasks")
        try:
            tasks_limit = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            print("Usage: py autoagent/meta/run.py --tasks 3")
            sys.exit(1)
    if tasks_limit:
        once = False

    mode_label = (
        f"--tasks {tasks_limit}" if tasks_limit else
        "--once" if once else
        "continuous (every 3h)"
    )

    print("╔══════════════════════════════════════════════════════════╗")
    print("║   Meta-Agent [Self-Improvement Brain]  |  VS Code Mode   ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  Agent dir : {AGENT_DIR}")
    print(f"  Meta dir  : {META_DIR}")
    print(f"  Mode      : {mode_label}")
    print(f"  Claude    : {CLAUDE_CMD}")
    print()

    # Validate claude.cmd exists
    if not os.path.exists(CLAUDE_CMD):
        print(f"[meta] FATAL: claude.cmd not found at:\n  {CLAUDE_CMD}")
        print("[meta] Install with:  npm install -g @anthropic-ai/claude-code")
        sys.exit(1)

    session_num = 1

    # Load prior session count from session_log.md
    if SESSION_LOG_FILE.exists():
        import re
        text = SESSION_LOG_FILE.read_text(encoding="utf-8", errors="replace")
        matches = re.findall(r"## Session #(\d+)", text)
        if matches:
            session_num = int(matches[-1]) + 1

    try:
        if once:
            _check_rate_limit()
            run_meta_session(session_num)

        elif tasks_limit:
            completed = 0
            print(f"\n[meta] Running until {tasks_limit} session(s) complete...\n")
            while completed < tasks_limit:
                _check_rate_limit()
                run_meta_session(session_num)
                session_num += 1
                completed  += 1
                remaining   = tasks_limit - completed
                print(
                    f"\n[meta] [{completed}/{tasks_limit}] sessions done."
                    f"{f' {remaining} remaining.' if remaining else ' All done — exiting.'}",
                    flush=True
                )
                if completed < tasks_limit:
                    print(f"[meta] Sleeping {SESSION_INTERVAL // 3600}h before next session...")
                    time.sleep(SESSION_INTERVAL)

        else:
            while True:
                _check_rate_limit()
                run_meta_session(session_num)
                session_num += 1

                next_run = datetime.fromtimestamp(
                    time.time() + SESSION_INTERVAL
                ).strftime("%H:%M:%S")
                print(
                    f"\n[meta] Next meta-session in "
                    f"{SESSION_INTERVAL // 3600}h "
                    f"(around {next_run}). Sleeping..."
                )
                time.sleep(SESSION_INTERVAL)

    except KeyboardInterrupt:
        print("\n[meta] Interrupted. Meta-agent stopped gracefully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
