#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoFlip Autonomous Agent -- Senior Dev + Marketing Team

A fully autonomous AI that acts as the entire product development and marketing
team for AutoFlip. Runs 24/7, improves the app and itself every session,
writes daily reports, tracks spending, and requests API keys when needed.

Usage:
    py -X utf8 agent/run.py             # run forever (every N hours)
    py -X utf8 agent/run.py --once      # run one session then exit
    py -X utf8 agent/run.py --status    # print today's spend + recent activity
"""
import io
import json
import os
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import anthropic
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# ─────────────────────────── Paths ────────────────────────────
ROOT      = Path(__file__).resolve().parent.parent   # autoflip/
AGENT_DIR = Path(__file__).resolve().parent          # autoflip/agent/
REPORTS_DIR = AGENT_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

CONFIG_FILE       = AGENT_DIR / "config.json"
BUDGET_FILE       = AGENT_DIR / "daily_budget.json"
GROWTH_FILE       = AGENT_DIR / "growth_metrics.json"
LOG_FILE          = AGENT_DIR / "activity_log.md"
BACKLOG_FILE      = AGENT_DIR / "BACKLOG.md"
API_REQUESTS_FILE = AGENT_DIR / "api_requests.md"
KNOWLEDGE_FILE    = AGENT_DIR / "knowledge.md"
CHECKPOINT_FILE      = AGENT_DIR / "checkpoint.json"
CURRENT_TASK_FILE    = AGENT_DIR / "current_task.md"
RESEARCH_QUEUE_FILE  = AGENT_DIR / "research_queue.md"
HEALTH_LOG_FILE      = AGENT_DIR / "health_log.json"
SKILLS_DIR           = AGENT_DIR / "skills"
TRAJECTORIES_FILE    = AGENT_DIR / "trajectories.md"
SKILLS_DIR.mkdir(exist_ok=True)

BACKEND_MODE_FILE = AGENT_DIR / "backend_mode.json"
RATE_LIMIT_FILE   = AGENT_DIR / "rate_limit.json"

# Load API key from backend/.env
load_dotenv(ROOT / "backend" / ".env")

# ─────────────────────────── Config ───────────────────────────
def load_config() -> dict:
    defaults = {
        "model": "claude-sonnet-4-6",
        "daily_limit_usd": 15.0,
        "interval_hours": 4,
        "session_max_turns": 50,
        "input_cost_per_token": 3e-6,
        "output_cost_per_token": 15e-6
    }
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            defaults.update(saved)
        except Exception:
            pass
    return defaults

cfg = load_config()
client = None  # initialized only in API mode — never touched in VS Code mode

# ──────────────────────────────────────────────────────────────
# TOOLS
# ──────────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "list_directory",
        "description": "List files/folders at a path in the AutoFlip project. Use '.' for root.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"]
        }
    },
    {
        "name": "read_file",
        "description": "Read a file. Returns up to 15000 chars. Works for any project file including agent/run.py itself.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": (
            "Write content to a file (creates or overwrites). "
            "You can edit ANY file including agent/run.py to improve yourself."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "run_command",
        "description": (
            "Run a shell command in the project root. Returns stdout+stderr. "
            "Use for: git commands, syntax checks (`py -c \"from app.main import app\"`), "
            "pip installs, npm installs, etc. Avoid long-running servers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout": {"type": "integer", "default": 30}
            },
            "required": ["command"]
        }
    },
    {
        "name": "web_search",
        "description": "Search the web for technical docs, best practices, Canadian auction sites, market data.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }
    },
    {
        "name": "fetch_url",
        "description": "Fetch and extract readable text from a URL (docs, GitHub, npm, PyPI, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "max_chars": {"type": "integer", "default": 6000}
            },
            "required": ["url"]
        }
    },
    {
        "name": "request_api_key",
        "description": (
            "Log that a feature needs an API key from the owner. "
            "IMPORTANT: You must ALWAYS implement the full feature FIRST using os.getenv('KEY_NAME'), "
            "with graceful fallback when the key is missing (log a warning, skip silently). "
            "The feature must be 100% ready — it activates automatically the moment the owner adds the key to backend/.env. "
            "Call this tool AFTER implementing the feature, not before. The owner only needs to paste the key — nothing else."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "e.g. 'Stripe', 'SendGrid'"},
                "env_var_name": {"type": "string", "description": "e.g. 'STRIPE_SECRET_KEY'"},
                "what_it_unlocks": {"type": "string", "description": "Exactly what feature activates when the key is added"},
                "how_to_get_key": {"type": "string", "description": "Simple instructions: where to sign up and find the key"},
                "urgency": {"type": "string", "enum": ["low", "medium", "high"]}
            },
            "required": ["service", "env_var_name", "what_it_unlocks", "how_to_get_key", "urgency"]
        }
    },
    {
        "name": "optimize_costs",
        "description": (
            "Update agent config to use a different model or settings for cost efficiency. "
            "Use claude-haiku-4-5-20251001 for simple sessions (research, small edits, marketing copy). "
            "Use claude-sonnet-4-6 for complex coding sessions. "
            "This takes effect next session."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "enum": ["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-6"],
                    "description": "Model to use next session"
                },
                "reason": {"type": "string", "description": "Why you're switching"}
            },
            "required": ["model", "reason"]
        }
    },
    {
        "name": "run_experiment",
        "description": (
            "Test a hypothesis with automatic accept/reject (autoresearch pattern by Karpathy). "
            "BEFORE modifying any file: call with action='baseline' to record current metric. "
            "AFTER modifying: call with action='evaluate' — if metric improves, changes are kept and committed; "
            "if metric regresses, changes are automatically git-reverted. "
            "Use this for: deal scoring tweaks, scraper improvements, calculation changes, agent/run.py self-modifications. "
            "This is how the agent makes safe, verified improvements instead of hopeful guesses."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hypothesis": {"type": "string", "description": "What you're testing: 'Adding mileage penalty should improve deal score accuracy'"},
                "metric_command": {"type": "string", "description": "Shell command outputting a numeric metric, e.g. 'py -m pytest backend/tests/ -q --tb=no 2>&1 | grep -E \"passed|failed\"'"},
                "action": {"type": "string", "enum": ["baseline", "evaluate"], "description": "baseline=record current state, evaluate=compare against baseline and decide"},
                "higher_is_better": {"type": "boolean", "default": True, "description": "True if higher metric = better (tests passed). False if lower = better (error rate, cost)."},
                "commit_message": {"type": "string", "description": "Git commit message if improvement accepted (required for evaluate action)"}
            },
            "required": ["hypothesis", "metric_command", "action"]
        }
    },
    {
        "name": "update_current_task",
        "description": (
            "Track progress on the current task (agents-orchestrator Dev-QA loop pattern). Call this: "
            "(1) when you START a task — write what the full task is and list all steps, "
            "(2) after each commit — mark that step done and note what remains, "
            "(3) when run_health_check FAILS — increment qa_attempt and set qa_feedback to the specific error, "
            "   this enables up to 3 retry attempts with focused feedback each time, "
            "   if qa_attempt reaches 3 and still failing — escalate to backlog as 'needs investigation', "
            "(4) when task is fully done — call with status='done' to clear it. "
            "This file is the first thing read next session so the agent resumes exactly here."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task_name": {"type": "string", "description": "Short name of the task e.g. 'Auth system — JWT login'"},
                "status": {"type": "string", "enum": ["in_progress", "done"], "description": "done clears the file"},
                "completed_steps": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Steps already committed e.g. ['backend JWT auth route', 'user model']"
                },
                "remaining_steps": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Steps not yet done e.g. ['login page UI', 'protected route wrapper']"
                },
                "last_commit": {"type": "string", "description": "The last git commit message made for this task"},
                "qa_attempt": {"type": "integer", "default": 1, "description": "Which QA attempt this is (1-3). Increment when run_health_check fails."},
                "qa_feedback": {"type": "string", "description": "Specific failure from run_health_check — exact error, test name, what needs fixing"}
            },
            "required": ["task_name", "status", "remaining_steps"]
        }
    },
    {
        "name": "update_backlog",
        "description": (
            "Mark a backlog item as done, add new items, or reprioritize. "
            "Read the current BACKLOG.md first, then call this with the full updated content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Full new content for BACKLOG.md"}
            },
            "required": ["content"]
        }
    },
    {
        "name": "save_skill",
        "description": (
            "Save a reusable code pattern to the persistent skill library (Voyager pattern). "
            "Call this whenever you write something reusable: a scraper helper, an API pattern, "
            "a MongoDB query, a React hook, a validation utility, a retry wrapper. "
            "Skills are stored as Python files in agent/skills/ and shown in future sessions. "
            "An agent with a growing skill library compounds capability — each skill stands on prior skills."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Short snake_case name, e.g. 'mongodb_upsert_pattern'"},
                "description": {"type": "string", "description": "One line: what this does and when to use it"},
                "code": {"type": "string", "description": "The reusable Python (or JS) code snippet, fully self-contained"}
            },
            "required": ["name", "description", "code"]
        }
    },
    {
        "name": "add_to_research_queue",
        "description": (
            "Add a topic to the autonomous research queue. Call this whenever you encounter something you don't know well enough: "
            "a library you're uncertain about, a best practice you should verify, a competitor to investigate, "
            "a new technique you heard about, or a knowledge gap that slowed you down. "
            "These get researched during the next self-growth session. NEVER skip learning opportunities."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "What to research, e.g. 'Stripe webhooks idempotency best practices'"},
                "why": {"type": "string", "description": "Why this matters — what problem it solves or what it would improve"},
                "priority": {"type": "string", "enum": ["high", "medium", "low"]}
            },
            "required": ["topic", "why", "priority"]
        }
    },
    {
        "name": "run_health_check",
        "description": (
            "Run the full project health check: backend imports, test suite, git status. "
            "Call this BEFORE task_complete to verify your work didn't break anything. "
            "Returns a health score and details. If health is degraded, fix before calling task_complete."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "note": {"type": "string", "description": "What you just finished building (for the health log)"}
            },
            "required": ["note"]
        }
    },
    {
        "name": "write_post_mortem",
        "description": (
            "Write a structured post-mortem when something failed, took much longer than expected, or had a surprising root cause. "
            "This is how the agent learns from mistakes and avoids repeating them. "
            "Call this ANY time: a test fails unexpectedly, a scraper breaks, a bug takes >3 turns to fix, or an approach was completely wrong."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "what_failed": {"type": "string", "description": "Concise description of what went wrong"},
                "root_cause": {"type": "string", "description": "The actual underlying cause, not just the symptom"},
                "fix_applied": {"type": "string", "description": "What you did to fix it"},
                "prevention": {"type": "string", "description": "How to avoid this next time — a rule or check to add"}
            },
            "required": ["what_failed", "root_cause", "fix_applied", "prevention"]
        }
    },
    {
        "name": "task_complete",
        "description": (
            "End the session. Call this ONLY after ALL of: "
            "(1) all steps committed and pushed, "
            "(2) update_current_task called with status='done' (clears the tracker), "
            "(3) backlog item marked [x] via update_backlog, "
            "(4) knowledge.md updated with at least one lesson, "
            "(5) run_health_check passed (no regressions), "
            "(6) save_skill called for any reusable pattern you wrote, "
            "(7) agent/run.py improved if you spotted anything. "
            "If the task is NOT fully done yet — do NOT call this. "
            "Instead commit what you have, update current_task with remaining steps, and let the next session continue."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task_name": {
                    "type": "string",
                    "description": "Short name matching the backlog item, e.g. 'Stripe Checkout integration'"
                },
                "summary": {
                    "type": "string",
                    "description": "What was built/fixed this session."
                },
                "files_changed": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "category": {
                    "type": "string",
                    "enum": ["feature", "bug_fix", "performance", "ui_ux", "marketing",
                             "new_source", "calculation", "subscription", "alert",
                             "self_improvement", "infrastructure"]
                },
                "impact": {
                    "type": "string",
                    "description": "Why this matters to users or the business."
                },
                "self_improvement": {
                    "type": "string",
                    "description": "What you improved about yourself this session (agent/run.py, knowledge.md, tools, prompt). Be specific."
                },
                "self_critique": {
                    "type": "object",
                    "description": "Honest 1-3 score on each dimension. 1=poor, 2=ok, 3=excellent.",
                    "properties": {
                        "research_depth": {"type": "integer", "minimum": 1, "maximum": 3, "description": "Did you search before building?"},
                        "code_quality": {"type": "integer", "minimum": 1, "maximum": 3, "description": "Clean, tested, secure code?"},
                        "self_growth": {"type": "integer", "minimum": 1, "maximum": 3, "description": "Did you improve knowledge.md + agent?"},
                        "task_completion": {"type": "integer", "minimum": 1, "maximum": 3, "description": "Did you finish what you started?"}
                    }
                },
                "next_session_hint": {
                    "type": "string",
                    "description": "One sentence: what the next session should prioritize and why."
                }
            },
            "required": ["summary", "category", "impact", "self_improvement", "next_session_hint"]
        }
    }
]


def execute_tool(name: str, inputs: dict) -> str:
    try:
        if name == "list_directory":
            path = ROOT / inputs["path"]
            if not path.exists():
                return f"Path not found: {inputs['path']}"
            items = []
            for item in sorted(path.iterdir()):
                if item.name in ("node_modules", "__pycache__", ".git", ".venv", "venv"):
                    continue
                prefix = "[DIR]" if item.is_dir() else "[FILE]"
                items.append(f"{prefix} {item.name}")
            return "\n".join(items) if items else "(empty)"

        elif name == "read_file":
            path = ROOT / inputs["path"]
            if not path.exists():
                return f"File not found: {inputs['path']}"
            content = path.read_text(encoding="utf-8", errors="replace")
            if len(content) > 15000:
                content = content[:15000] + "\n\n...(truncated to 15000 chars)"
            return content

        elif name == "write_file":
            path = ROOT / inputs["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(inputs["content"], encoding="utf-8")
            return f"Written {len(inputs['content'])} chars to {inputs['path']}"

        elif name == "run_command":
            cmd = inputs["command"]
            timeout = int(inputs.get("timeout", 30))
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=str(ROOT), encoding="utf-8", errors="replace"
            )
            output = (result.stdout + result.stderr).strip()
            if not output:
                return f"(exit {result.returncode}, no output)"
            return output[:5000]

        elif name == "web_search":
            query = inputs["query"]
            url = f"https://html.duckduckgo.com/html/?q={httpx.utils.quote(query)}"
            resp = httpx.get(url, timeout=15, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for block in soup.select(".result__body")[:6]:
                title = block.select_one(".result__title")
                snippet = block.select_one(".result__snippet")
                link = block.select_one(".result__url")
                if title and snippet:
                    entry = f"**{title.get_text(strip=True)}**"
                    if link:
                        entry += f" — {link.get_text(strip=True)}"
                    entry += f"\n{snippet.get_text(strip=True)}"
                    results.append(entry)
            return "\n\n".join(results) if results else "No results."

        elif name == "fetch_url":
            max_chars = int(inputs.get("max_chars", 6000))
            resp = httpx.get(inputs["url"], timeout=20, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            lines = [l for l in soup.get_text(separator="\n", strip=True).splitlines() if l.strip()]
            return "\n".join(lines)[:max_chars]

        elif name == "request_api_key":
            service  = inputs["service"]
            env_var  = inputs["env_var_name"]
            unlocks  = inputs.get("what_it_unlocks", "")
            how_to   = inputs.get("how_to_get_key", "")
            urgency  = inputs.get("urgency", "medium")
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry = (
                f"\n---\n"
                f"## [ ] {service} — {urgency.upper()} priority — {ts}\n\n"
                f"**Add this to `backend/.env`:**\n"
                f"```\n{env_var}=your_key_here\n```\n\n"
                f"**What this unlocks:** {unlocks}\n\n"
                f"**How to get the key:** {how_to}\n\n"
                f"_Feature is fully implemented and will activate automatically once you add the key._\n"
            )
            with open(API_REQUESTS_FILE, "a", encoding="utf-8") as f:
                f.write(entry)
            return f"Logged API key request for {service}. Feature is coded and ready — just needs the key."

        elif name == "optimize_costs":
            model  = inputs["model"]
            reason = inputs.get("reason", "")
            cfg_data = load_config()
            # Update pricing based on model
            pricing_map = {
                "claude-haiku-4-5-20251001":  {"input_cost_per_token": 0.8e-6,  "output_cost_per_token": 4e-6},
                "claude-sonnet-4-6":           {"input_cost_per_token": 3e-6,    "output_cost_per_token": 15e-6},
                "claude-opus-4-6":             {"input_cost_per_token": 15e-6,   "output_cost_per_token": 75e-6},
            }
            cfg_data["model"] = model
            cfg_data.update(pricing_map.get(model, {}))
            CONFIG_FILE.write_text(json.dumps(cfg_data, indent=2), encoding="utf-8")
            return f"Model switched to {model}. Reason: {reason}. Takes effect next session."

        elif name == "update_current_task":
            if inputs.get("status") == "done":
                if CURRENT_TASK_FILE.exists():
                    CURRENT_TASK_FILE.unlink()
                return "Current task cleared — task complete."
            task_name   = inputs["task_name"]
            completed   = inputs.get("completed_steps", [])
            remaining   = inputs["remaining_steps"]
            last_commit = inputs.get("last_commit", "")
            qa_attempt  = inputs.get("qa_attempt", 1)
            qa_feedback = inputs.get("qa_feedback", "")
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            retry_block = ""
            if qa_attempt > 1:
                retry_block = (
                    f"\n\n## QA Retry Status (agents-orchestrator pattern)\n"
                    f"**Attempt {qa_attempt}/3**\n"
                    f"Previous QA feedback: {qa_feedback}\n"
                    f"{'⚠️  FINAL ATTEMPT — if this fails, escalate to backlog and move on.' if qa_attempt >= 3 else ''}\n"
                )
            content = (
                f"# Current Task — {task_name}\n"
                f"_Last updated: {ts}_\n\n"
                f"## Completed Steps (already committed)\n"
                + ("\n".join(f"- [x] {s}" for s in completed) if completed else "- (none yet)\n")
                + f"\n\n## Remaining Steps (do these next)\n"
                + "\n".join(f"- [ ] {s}" for s in remaining)
                + (f"\n\n## Last Commit\n`{last_commit}`\n" if last_commit else "")
                + retry_block
            )
            CURRENT_TASK_FILE.write_text(content, encoding="utf-8")
            return f"Task tracker updated. {len(completed)} done, {len(remaining)} remaining. QA attempt: {qa_attempt}/3."

        elif name == "update_backlog":
            BACKLOG_FILE.write_text(inputs["content"], encoding="utf-8")
            return "Backlog updated."

        elif name == "run_experiment":
            import re as _re
            hypothesis     = inputs["hypothesis"]
            metric_cmd     = inputs["metric_command"]
            action         = inputs["action"]
            higher_better  = inputs.get("higher_is_better", True)
            commit_msg     = inputs.get("commit_message", "")
            exp_file       = AGENT_DIR / "experiment_baseline.json"

            def extract_number(text: str) -> float | None:
                nums = _re.findall(r"[-+]?\d+\.?\d*", text)
                return float(nums[0]) if nums else None

            # Run the metric command
            r = subprocess.run(metric_cmd, shell=True, capture_output=True, text=True,
                               timeout=120, cwd=str(ROOT), encoding="utf-8", errors="replace")
            raw = (r.stdout + r.stderr).strip()
            metric = extract_number(raw)

            if action == "baseline":
                data = {"hypothesis": hypothesis, "metric_cmd": metric_cmd,
                        "baseline": metric, "raw": raw[:500],
                        "higher_is_better": higher_better,
                        "git_ref": subprocess.run(
                            "git rev-parse HEAD", shell=True, capture_output=True,
                            text=True, cwd=str(ROOT)
                        ).stdout.strip()}
                exp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
                return (f"Baseline recorded: metric={metric}\nRaw output: {raw[:300]}\n"
                        f"Now make your changes, then call run_experiment with action='evaluate'.")

            elif action == "evaluate":
                if not exp_file.exists():
                    return "ERROR: No baseline recorded. Call with action='baseline' first."
                baseline_data = json.loads(exp_file.read_text(encoding="utf-8"))
                baseline      = baseline_data.get("baseline")
                git_ref       = baseline_data.get("git_ref", "")

                if baseline is None or metric is None:
                    return (f"Could not parse numeric metric.\nBaseline raw: {baseline_data.get('raw','')}\n"
                            f"New raw: {raw[:300]}")

                improved = (metric > baseline) if higher_better else (metric < baseline)
                delta = metric - baseline

                # Get current commit hash for results log
                commit_hash = subprocess.run(
                    "git rev-parse --short HEAD", shell=True, capture_output=True,
                    text=True, cwd=str(ROOT)
                ).stdout.strip()

                # Log to experiment results TSV (autoresearch pattern)
                tsv_path = AGENT_DIR / "experiment_results.tsv"
                if not tsv_path.exists():
                    tsv_path.write_text("commit\tmetric_before\tmetric_after\tdelta\tstatus\thypothesis\n", encoding="utf-8")

                if improved:
                    # Keep changes — commit them
                    if commit_msg:
                        execute_tool("run_command", {
                            "command": f'git add -A && git commit -m "{commit_msg} [exp: {baseline:.3f}→{metric:.3f}]"',
                            "timeout": 30
                        })
                        commit_hash = subprocess.run(
                            "git rev-parse --short HEAD", shell=True, capture_output=True,
                            text=True, cwd=str(ROOT)
                        ).stdout.strip()
                    status = "keep"
                    with open(tsv_path, "a", encoding="utf-8") as tsv_f:
                        tsv_f.write(f"{commit_hash}\t{baseline:.4f}\t{metric:.4f}\t{delta:+.4f}\t{status}\t{hypothesis[:80]}\n")
                    exp_file.unlink(missing_ok=True)
                    return (f"EXPERIMENT ACCEPTED. Metric: {baseline:.4f} → {metric:.4f} ({delta:+.4f})\n"
                            f"Changes committed. Hypothesis confirmed: {hypothesis}")
                else:
                    # Revert — git checkout back to baseline ref
                    execute_tool("run_command", {
                        "command": f"git stash && git stash drop 2>/dev/null || git checkout -- .",
                        "timeout": 30
                    })
                    status = "discard"
                    with open(tsv_path, "a", encoding="utf-8") as tsv_f:
                        tsv_f.write(f"{commit_hash}\t{baseline:.4f}\t{metric:.4f}\t{delta:+.4f}\t{status}\t{hypothesis[:80]}\n")
                    exp_file.unlink(missing_ok=True)
                    return (f"EXPERIMENT REJECTED. Metric: {baseline:.4f} → {metric:.4f} ({delta:+.4f})\n"
                            f"Changes reverted to baseline. Try a different approach.\n"
                            f"Review agent/experiment_results.tsv to avoid repeating failed hypotheses.")

        elif name == "save_skill":
            skill_name = inputs["name"].replace(" ", "_").lower()
            description = inputs["description"]
            code = inputs["code"]
            skill_path = SKILLS_DIR / f"{skill_name}.py"
            content = f'"""\n{description}\n\nSaved by agent on {datetime.now().strftime("%Y-%m-%d")}.\n"""\n\n{code}\n'
            skill_path.write_text(content, encoding="utf-8")
            # Update skills index
            index_path = SKILLS_DIR / "INDEX.md"
            index = index_path.read_text(encoding="utf-8") if index_path.exists() else "# Skill Library\n\nReusable patterns saved by the agent.\n\n"
            entry = f"- **{skill_name}** — {description} (`agent/skills/{skill_name}.py`)\n"
            if skill_name not in index:
                index += entry
                index_path.write_text(index, encoding="utf-8")
            return f"Skill '{skill_name}' saved to agent/skills/{skill_name}.py"

        elif name == "add_to_research_queue":
            topic    = inputs["topic"]
            why      = inputs["why"]
            priority = inputs.get("priority", "medium")
            ts = datetime.now().strftime("%Y-%m-%d")
            entry = f"\n- [{priority.upper()}] **{topic}** — Added {ts}\n  _Why: {why}_\n"
            if not RESEARCH_QUEUE_FILE.exists():
                RESEARCH_QUEUE_FILE.write_text(
                    "# Research Queue\n\nItems to research in the next self-growth session.\n"
                    "Delete an item after researching it and updating knowledge.md.\n",
                    encoding="utf-8"
                )
            with open(RESEARCH_QUEUE_FILE, "a", encoding="utf-8") as f:
                f.write(entry)
            return f"Added to research queue: '{topic}' [{priority}]"

        elif name == "run_health_check":
            note = inputs.get("note", "end of session")
            results = {}

            # Backend import check
            r = subprocess.run(
                'py -c "import sys; sys.path.insert(0,\'backend\'); from app.main import app; print(\'OK\')"',
                shell=True, capture_output=True, text=True, timeout=30, cwd=str(ROOT),
                encoding="utf-8", errors="replace"
            )
            results["backend_import"] = "OK" if "OK" in r.stdout else f"FAIL: {(r.stdout+r.stderr)[:200]}"

            # Test suite
            r2 = subprocess.run(
                "py -m pytest backend/tests/ -q --tb=no 2>&1 | tail -3",
                shell=True, capture_output=True, text=True, timeout=60, cwd=str(ROOT),
                encoding="utf-8", errors="replace"
            )
            test_out = (r2.stdout + r2.stderr).strip()
            results["tests"] = test_out[:300]

            # Parse pass/fail counts
            import re
            m = re.search(r"(\d+) passed", test_out)
            passed = int(m.group(1)) if m else 0
            m2 = re.search(r"(\d+) failed", test_out)
            failed = int(m2.group(1)) if m2 else 0
            health_score = 3 if (results["backend_import"] == "OK" and failed == 0) else \
                           2 if results["backend_import"] == "OK" else 1

            # Log health
            health_data = json.loads(HEALTH_LOG_FILE.read_text(encoding="utf-8")) if HEALTH_LOG_FILE.exists() else []
            health_data.append({
                "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "note": note,
                "backend_import": results["backend_import"],
                "tests_passed": passed,
                "tests_failed": failed,
                "health_score": health_score
            })
            health_data = health_data[-20:]  # keep last 20
            HEALTH_LOG_FILE.write_text(json.dumps(health_data, indent=2), encoding="utf-8")

            summary = (
                f"Health score: {health_score}/3\n"
                f"Backend import: {results['backend_import']}\n"
                f"Tests: {passed} passed, {failed} failed\n"
                f"{test_out}"
            )
            if failed > 0:
                return f"HEALTH CHECK FAILED — fix before task_complete!\n{summary}"
            return f"Health check passed.\n{summary}"

        elif name == "write_post_mortem":
            what    = inputs["what_failed"]
            cause   = inputs["root_cause"]
            fix     = inputs["fix_applied"]
            prevent = inputs["prevention"]
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry = (
                f"\n### Post-Mortem — {ts}\n"
                f"**What failed:** {what}\n"
                f"**Root cause:** {cause}\n"
                f"**Fix applied:** {fix}\n"
                f"**Prevention rule:** {prevent}\n"
            )
            # Append to knowledge.md under a Post-Mortems section
            knowledge = KNOWLEDGE_FILE.read_text(encoding="utf-8") if KNOWLEDGE_FILE.exists() else ""
            if "## Post-Mortems" not in knowledge:
                knowledge += "\n\n## Post-Mortems\n"
            knowledge += entry
            KNOWLEDGE_FILE.write_text(knowledge, encoding="utf-8")
            return f"Post-mortem written to knowledge.md: {what}"

        elif name == "task_complete":
            return "__TASK_COMPLETE__"

        return f"Unknown tool: {name}"

    except subprocess.TimeoutExpired:
        return f"Timed out after {inputs.get('timeout', 30)}s"
    except Exception as e:
        return f"Tool error [{name}]: {type(e).__name__}: {e}"


# ──────────────────────────────────────────────────────────────
# BUDGET
# ──────────────────────────────────────────────────────────────

def load_budget() -> dict:
    if BUDGET_FILE.exists():
        return json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
    return {}

def get_today_spend() -> float:
    return load_budget().get(str(date.today()), {}).get("spend", 0.0)

def record_spend(input_tokens: int, output_tokens: int) -> float:
    cost = (input_tokens  * cfg["input_cost_per_token"] +
            output_tokens * cfg["output_cost_per_token"])
    budget = load_budget()
    today = str(date.today())
    if today not in budget:
        budget[today] = {"spend": 0.0, "runs": 0}
    budget[today]["spend"] = round(budget[today]["spend"] + cost, 6)
    budget[today]["runs"] += 1
    BUDGET_FILE.write_text(json.dumps(budget, indent=2), encoding="utf-8")
    return cost


def seconds_until_midnight() -> int:
    """Seconds until local midnight (start of next day)."""
    now = datetime.now()
    midnight = datetime(now.year, now.month, now.day)
    from datetime import timedelta
    midnight += timedelta(days=1)
    return max(int((midnight - now).total_seconds()), 60)


def save_checkpoint(task_description: str, progress: str):
    """Save mid-task state so next session continues from here."""
    data = {
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "task": task_description,
        "progress": progress
    }
    CHECKPOINT_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def clear_checkpoint():
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()


def load_checkpoint() -> dict | None:
    if CHECKPOINT_FILE.exists():
        try:
            return json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


# ──────────────────────────────────────────────────────────────
# DAILY REPORT
# ──────────────────────────────────────────────────────────────

def get_report_file() -> Path:
    return REPORTS_DIR / f"{date.today()}.md"

def append_to_report(section: str):
    report = get_report_file()
    if not report.exists():
        report.write_text(
            f"# AutoFlip Agent Daily Report — {date.today()}\n\n"
            f"_This report is written automatically. Check api_requests.md for keys needed._\n\n",
            encoding="utf-8"
        )
    with open(report, "a", encoding="utf-8") as f:
        f.write(section)

def finalize_report():
    """Append spend summary to today's report."""
    spend = get_today_spend()
    remaining = cfg["daily_limit_usd"] - spend
    section = (
        f"\n---\n"
        f"**Budget used today:** ${spend:.4f} / ${cfg['daily_limit_usd']:.2f}  "
        f"(${remaining:.4f} remaining)\n"
        f"_Report updated: {datetime.now().strftime('%H:%M:%S')}_\n"
    )
    append_to_report(section)


# ──────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a **fully autonomous, self-growing intelligence** — not just a coding assistant, but a complete organism that learns, adapts, and improves in every dimension without human interaction.

You simultaneously hold all roles:
- **Senior Full-Stack Engineer** — clean async Python, React 19, FastAPI, MongoDB, security-first, test-driven
- **Senior UI/UX Designer** — beautiful interfaces, Tailwind + shadcn/ui, mobile-first, accessibility, conversion-optimized
- **Senior Growth Marketer** — SaaS copywriting, landing page optimization, SEO, retention, pricing psychology
- **Financial Optimizer** — minimize API costs, maximize output per dollar, find smarter/cheaper approaches
- **Research Scientist** — absorbs new knowledge from Anthropic docs, GitHub, tech blogs, applies it immediately
- **Systems Architect** — improves your own architecture, decision-making, tools, and prompts every session
- **DevOps Engineer** — git discipline, clean commits, dependency management
- **Product Manager** — prioritizes by revenue impact and user value

You work 24/7 with **zero human interaction**. The owner only pastes API keys. You handle everything else.
**Your only goal: be measurably better than yesterday — in the product, in yourself, in efficiency, in knowledge.**

---

## DIMENSIONS OF GROWTH (all equally important)

### 1. Product Growth
Build features, fix bugs, improve UI/UX, add auction sources, improve calculations.

### 2. Agent Self-Growth
Improve agent/run.py — better tools, smarter prompts, better context loading, new capabilities.
Every 3rd session minimum: read agent/run.py fully and find something to improve.

### 3. Financial Intelligence
**Every session, think about cost efficiency:**
- Am I using the right model? Use `claude-haiku-4-5-20251001` for simple tasks (10x cheaper: $0.80/MTok vs $3/MTok)
- Could I reduce context size? Long contexts cost more — trim what's not needed
- Am I repeating expensive work? Cache it.
- Check growth_metrics.json spend trend — if burning too fast, optimize
- Update config.json model if a cheaper model can do the job equally well
- Search "Anthropic API cost optimization 2026" periodically for new techniques

### 4. Knowledge Absorption
**Regularly search for and absorb:**
- Anthropic release notes: new models, new features, prompt caching, tool improvements
- Claude documentation updates: fetch https://docs.anthropic.com/en/docs/about-claude/models
- GitHub trending repos in Python/React/FastAPI/AI agents
- Claude skill MDs and CLAUDE.md patterns from other projects on GitHub
- New scraping techniques, new Canadian auction sites
- SaaS growth tactics, car flipper communities, Ontario auto market news
- When you find something useful → update knowledge.md immediately

**Knowledge freshness rule:** If knowledge.md hasn't mentioned a topic in 7+ days, it's stale.
Key domains to refresh regularly: Anthropic API/models, React patterns, MongoDB/Motor, FastAPI security, SaaS pricing.
Use `add_to_research_queue` to queue stale domains for the next self-growth session.

**Research queue discipline (Voyager pattern):**
When you notice a gap → don't just work around it → add it to the research queue via `add_to_research_queue`.
The research queue is your long-term skill accumulation engine. An agent that never queues research never grows.

### 5. Marketing Intelligence
Research competitors, find new channels, improve copy, study what converts.

---

---

## The Product
AutoFlip is an Ontario SaaS for car flippers:
- Monitors auction sites (Cathcart Auto, Pic N Save) every 10 minutes
- Scrapes vehicles that DON'T require a dealership license
- AI damage detection (Claude vision), blended market value (60% AutoTrader comps + 40% formula), Ontario fees (HST 13%, OMVIC $22, MTO $32, safety cert $100)
- Deal scoring 0-100, ranks by profit potential
- **Business model:** $4.99/month or $39.99/year — target: Ontario car flippers

---

---

## API Key Pattern — CRITICAL RULE
When a feature needs an external API key (Stripe, SendGrid, Twilio, etc.):
1. **Implement the FULL feature** using `os.getenv("KEY_NAME")`
2. **Add graceful fallback** — if key is missing, log a warning and return silently. The app never crashes.
3. **Call `request_api_key`** after implementing — log what env var is needed and where to get it
4. **Keep working** — move to the next task. Never block on a missing key.

Example pattern:
```python
api_key = os.getenv("SENDGRID_API_KEY")
if not api_key:
    logger.warning("SENDGRID_API_KEY not set — email alerts disabled")
    return
# ... full feature code using api_key
```
The feature is **100% coded and tested**. It activates the instant the owner adds the key to `backend/.env`. That's the only thing the owner ever needs to do.

---

## MANDATORY SESSION WORKFLOW — NEVER SKIP A PHASE

### PHASE 1: Research First (ALWAYS before writing any code)
Before touching a single file:
- `web_search` for current best practices on what you are about to build
- Search for security issues, CVEs, better libraries, 2025/2026 patterns
- For marketing: search competitor landing pages, SaaS conversion best practices, Ontario car flipper communities
- For scrapers: fetch the actual auction site to understand its current HTML structure
- Ask yourself: "Is there a better/simpler approach than what I'm about to do?"

### PHASE 2: Read & Plan
- Read every file you will touch — never write blind
- Write a clear 3-step plan before starting
- Check for edge cases, error conditions, security implications

### PHASE 2.5: Experiment Design (for any change that affects metrics)
For changes to calculations, scrapers, or agent/run.py — use the experiment loop (Karpathy autoresearch pattern):
```
1. run_experiment(action="baseline", metric_command="py -m pytest backend/tests/ -q --tb=no")
2. Make your changes
3. run_experiment(action="evaluate", ...) → auto-keeps if better, auto-reverts if worse
```
This makes every modification safe. Never commit a regression.

### PHASE 3: Implement — commit small, track everything
- **Before writing a single line**: call `update_current_task` with the full task name + all steps listed
- **Mark the backlog item `[~]`** via `update_backlog` so next session knows it's in progress
- **Commit after EVERY logical step** — never hold more than one step in uncommitted state
- Each commit message: `agent: <feature> step N/M — <what this step does>`
- After each commit: call `update_current_task` again to mark that step done and show remaining
- This way: if budget runs out after any commit, next session reads current_task.md and picks up the next step
- Write clean, async, secure code. Follow existing patterns (async/await, logger not print, type hints)
- Every new backend function → add a test in backend/tests/

### PHASE 3.5: Dev-QA Retry Loop (agents-orchestrator pattern — max 3 attempts)
When `run_health_check` fails:
1. Read the exact error message carefully
2. Call `update_current_task` with `qa_attempt=N+1`, `qa_feedback=<specific error>`
3. Fix ONLY what the error describes — don't refactor unrelated things
4. Re-run `run_health_check`
5. If attempt 3 fails: add item to backlog as `[!] Needs investigation — {what failed}`, commit what works, move on
This prevents infinite loops. 3 attempts max, then escalate.

### PHASE 4: VALIDATE — NON-NEGOTIABLE (no commit without this)
Run ALL of these after any backend change:
```
py -c "import sys; sys.path.insert(0,'backend'); from app.main import app; print('backend imports OK')"
py -m pytest backend/tests/ -x -q --tb=short
```
For any individual changed Python file:
```
py -m py_compile backend/app/routes/scrape.py
```
**If any check fails → fix it. Never commit broken code. Ever.**

For frontend changes, run BOTH checks before committing:
1. Build check (catches JSX syntax errors):
```
cd frontend && PATH="/c/Program Files/nodejs:$PATH" "C:\\Program Files\\nodejs\\npm.cmd" run build 2>&1 | tail -10
```
2. Unit tests (run from /tmp shadow copy — OneDrive blocks scoped npm packages):
```
cp -r frontend/src /tmp/autoflip-fe/src && NODE_ENV=test PATH="/c/Program Files/nodejs:$PATH" "C:\\Program Files\\nodejs\\npm.cmd" --prefix /tmp/autoflip-fe test -- --watchAll=false --forceExit 2>&1 | tail -10
```
**If EITHER check fails → fix it before committing. Never commit broken code. Ever.**
Common JSX pitfalls: unescaped apostrophes in single-quoted strings (`We're` → `"We're"`), unescaped `<`/`>` in JSX text, missing closing tags.

### PHASE 5: Commit & Push
Only after ALL checks pass:
```
git add -A
git commit -m "agent: <what changed> — <why it matters>"
git push origin main
```
Commit messages must explain the WHY, not just the what.

### PHASE 6: Self-Reflect & Grow — MANDATORY, EVERY SESSION, NO EXCEPTIONS
This phase is not optional. It is the engine of compounding growth. (Based on Reflexion, Voyager, and AutoGPT patterns.)

**Step A — Knowledge capture** (ALWAYS — no exceptions):
Append at least one concrete, specific lesson to `agent/knowledge.md`:
- "BeautifulSoup fails on this site — uses JS rendering, need regex fallback"
- "Stripe webhook requires raw body bytes, not parsed JSON"
- "IAA Canada needs a session cookie from homepage before search works"
If something took more than 3 turns to fix → write a `write_post_mortem`. This is how the agent gets smarter.

**Step A2 — Skill library** (Voyager pattern — whenever you write something reusable):
If you wrote a helper function, a scraper pattern, an API integration pattern, a MongoDB query pattern,
or a React hook — call `save_skill`. The skill library compounds: future sessions don't rewrite from scratch.
Check the Skill Library section in context first — it may already have what you need.

**Step B — Research queue** (whenever you noticed a gap):
Did anything make you think "I should know more about this"? Call `add_to_research_queue`.
Examples: a library you used without fully understanding, a competitor you heard of, a technique that might help.

**Step C — Agent self-modification** (at least every 3rd session):
Ask yourself: "What would make me meaningfully smarter or faster next session?"
- A missing tool? Add it to TOOLS + execute_tool.
- A weak context section? Improve build_context().
- A prompt gap? Sharpen SYSTEM_PROMPT.
- A repeated mistake? Add a guard or warning.
The agent next session should be measurably better than you right now.

**Step D — Run health check** (ALWAYS before task_complete):
Call `run_health_check`. If score < 3, fix regressions before finishing.

**Step E — Fill in task_complete** with:
- `self_improvement`: exactly what you changed about the agent (or "none" if truly nothing)
- `self_critique`: honest 1-3 scores on research_depth, code_quality, self_growth, task_completion
- `next_session_hint`: what the next session should prioritize and why

**Step F — Update BACKLOG.md**:
Mark item done `[x]`. Add any new ideas. Re-prioritize based on business impact.

**Self-critique scoring guide:**
- research_depth: 3=searched before every change | 2=some research | 1=coded without researching
- code_quality: 3=all tests pass, clean async, no security issues | 2=tests pass, minor issues | 1=tests failing or messy
- self_growth: 3=concrete lesson + post-mortem if needed + agent improved | 2=lesson written | 1=nothing written
- task_completion: 3=task fully done and pushed | 2=partial but committed | 1=nothing committed

---

## Code Quality Standards (non-negotiable)
- **Security**: sanitize all scraped inputs, never trust external data, no injection vulnerabilities
- **Error handling**: all scrapers must handle network failures, timeouts, and HTML structure changes gracefully — wrap in try/except, log errors, continue
- **Async**: all I/O must be async. Never use `time.sleep()` in async code — use `asyncio.sleep()`
- **Logging**: use `logger = logging.getLogger(__name__)` not `print()` in backend code
- **Tests**: pytest for backend. Every new scraper/service function → at least one test
- **No hardcoded values**: use constants or config for URLs, timeouts, thresholds
- **Up to date**: always search for the current recommended approach before implementing

---

## UI/UX Standards
As senior UI/UX designer you must:
- **Research first**: search "shadcn ui best practices 2026", "Tailwind dashboard design patterns", "React UX conversion"
- **Mobile-first**: every component must work on 375px screens before desktop
- **Loading states**: every async action has a skeleton or spinner — never blank screens
- **Empty states**: every list has a meaningful empty state with a clear CTA ("No listings yet — trigger a scan")
- **Error states**: network failures show friendly messages, never raw errors
- **Micro-interactions**: hover states, transition animations (150ms), focus rings for accessibility
- **Color & contrast**: WCAG AA minimum — readable text, clear hierarchy
- **Data density**: tables are scannable — most important info (profit, score) most prominent
- **Typography**: consistent scale, bold for key numbers (profit amounts), muted for secondary info

## Marketing Standards
As senior growth marketer you must:
- **Research first**: search "SaaS car dealer tool marketing", "Ontario car flipper forums", "auction car resale Canada 2026"
- **Specific value language**: "Find profitable flip deals 10 minutes before anyone else" — never vague ("Our app is great")
- **Target exact pain points**: "Stop spending 2 hours checking auction sites every morning. AutoFlip does it while you sleep."
- **Pricing psychology**: $4.99/month framed as "less than one coffee" — $39.99/year framed as "2 months free"
- **Social proof hooks**: "Join X car flippers already using AutoFlip" (use real number from DB user count)
- **Urgency + scarcity**: "New deals appear every 10 minutes — subscribers see them first"
- **Risk reduction**: "Cancel anytime. No contracts."
- **Landing page hierarchy**: Hero (pain + solution + CTA) → How it works (3 steps) → Sample deals (proof) → Pricing → FAQ → Footer CTA

---

## Stack Reference
- Backend: Python 3.14, FastAPI, Motor (async MongoDB), httpx, BeautifulSoup4, Anthropic claude-opus-4-6
- Frontend: React 19, Tailwind CSS, shadcn/ui, craco, path alias `@/` = `frontend/src/`
- DB: MongoDB localhost:27017, database `autoflip`
- Python: `py` | Node: `C:\\Program Files\\nodejs\\npm.cmd` | Git: push to `origin main`
- Backend entry: `cd backend && py -m uvicorn app.main:app --port 8001 --reload`

---

## Simplicity Criterion (from Karpathy autoresearch)
When evaluating whether to keep a change — weigh complexity cost against improvement magnitude:
- Small improvement + ugly complexity = not worth it. Revert.
- Small improvement + code deletion = definitely keep.
- Equal performance + simpler code = keep. Simplification is a win.
- Big improvement + any complexity = keep with good documentation.
Apply this when using `run_experiment`: an experiment that adds 20 lines of hacky code for 0.1% improvement is a discard.

## Autonomous Operation (never ask for permission)
You run indefinitely. You do not stop to ask if you should continue.
If you run out of obvious ideas, think harder: re-read knowledge.md, review experiment_results.tsv for patterns,
try combining prior near-misses, read the failing tests for clues. The loop runs until budget is exhausted.
The owner may be asleep. Work as if they are.

Be decisive. Research first. Build completely. Test rigorously. Commit only clean code. Grow every session."""


# ──────────────────────────────────────────────────────────────
# SESSION CONTEXT
# ──────────────────────────────────────────────────────────────

def build_context() -> str:
    parts = []

    # Active task tracker — resume this before anything else
    if CURRENT_TASK_FILE.exists():
        parts.append(
            f"## RESUME THIS TASK FIRST — DO NOT START ANYTHING NEW\n"
            f"{CURRENT_TASK_FILE.read_text(encoding='utf-8')}\n\n"
            f"Pick the first unchecked remaining step and implement it. "
            f"Commit it. Update current_task via update_current_task tool. "
            f"Only start a new task when all remaining steps are done."
        )

    # Checkpoint from hard mid-session interrupt (budget hit)
    cp = load_checkpoint()
    if cp and not CURRENT_TASK_FILE.exists():
        parts.append(
            f"## CHECKPOINT — budget ran out mid-session on {cp['saved_at']}\n"
            f"Was working on: {cp['task']}\n"
            f"Progress: {cp['progress']}"
        )

    # Backlog (priorities)
    if BACKLOG_FILE.exists():
        parts.append(f"## BACKLOG (your priorities)\n{BACKLOG_FILE.read_text(encoding='utf-8')}")

    # Accumulated knowledge from past sessions
    if KNOWLEDGE_FILE.exists():
        parts.append(f"## Knowledge Base (lessons learned from past sessions)\n{KNOWLEDGE_FILE.read_text(encoding='utf-8')}")

    # Recent activity log (last 3000 chars)
    if LOG_FILE.exists():
        content = LOG_FILE.read_text(encoding="utf-8")
        parts.append(f"## Recent Activity (what was done — don't repeat)\n{content[-3000:]}")

    # Current test status
    test_result = execute_tool("run_command", {
        "command": "py -m pytest backend/tests/ -q --tb=no 2>&1 | tail -5",
        "timeout": 30
    })
    parts.append(f"## Current Test Status\n{test_result}")

    # API keys available
    env_path = ROOT / "backend" / ".env"
    if env_path.exists():
        env_keys = [
            line.split("=")[0].strip()
            for line in env_path.read_text(encoding="utf-8").splitlines()
            if "=" in line and not line.startswith("#")
        ]
        parts.append("## Available API Keys (in backend/.env)\n" + "\n".join(f"- {k}" for k in env_keys))

    # Pending API key requests
    if API_REQUESTS_FILE.exists():
        content = API_REQUESTS_FILE.read_text(encoding="utf-8")
        if "PENDING" in content:
            parts.append(f"## Pending API Key Requests (owner has not yet provided)\n{content}")

    # Budget + financial efficiency
    spend = get_today_spend()
    remaining = cfg["daily_limit_usd"] - spend
    m = json.loads(GROWTH_FILE.read_text(encoding="utf-8")) if GROWTH_FILE.exists() else {}
    total_sessions = m.get("total_sessions", 1)
    avg_cost = m.get("total_cost_usd", 0) / max(total_sessions, 1)
    current_model = load_config().get("model", "claude-sonnet-4-6")
    parts.append(
        f"## Budget & Financial Intelligence\n"
        f"Today: ${spend:.4f} spent / ${remaining:.4f} remaining (limit ${cfg['daily_limit_usd']:.2f})\n"
        f"Avg cost/session: ${avg_cost:.4f} | Current model: {current_model}\n"
        f"Models available: haiku ($0.80/MTok in, $4/MTok out) | sonnet ($3/$15) | opus ($15/$75)\n"
        f"Consider switching to haiku for simpler sessions to stretch the daily budget further."
    )

    # Last session's recommended next priority + all-time growth stats
    if GROWTH_FILE.exists():
        m = json.loads(GROWTH_FILE.read_text(encoding="utf-8"))
        hints = m.get("next_session_hints", [])
        total = m.get("total_sessions", 0)
        cats  = m.get("categories", {})
        last_self = (m.get("self_improvements") or [{}])[-1].get("what", "none yet")
        growth_summary = (
            f"Total sessions: {total} | Categories: {cats}\n"
            f"Last self-improvement: {last_self}\n"
        )
        if hints:
            growth_summary += f"PRIORITY FROM LAST SESSION: {hints[0]['hint']}"
        parts.append(f"## Growth Metrics & Next Priority\n{growth_summary}")

    # Experiment results log — what has been tried, what worked
    exp_tsv = AGENT_DIR / "experiment_results.tsv"
    if exp_tsv.exists():
        lines = exp_tsv.read_text(encoding="utf-8").strip().splitlines()
        if len(lines) > 1:
            recent = "\n".join(lines[-10:])  # last 10 experiments
            parts.append(f"## Experiment History (last 10 — don't repeat failed hypotheses)\n{recent}")

    # Skill library index — reusable patterns the agent has built up
    skills_index = SKILLS_DIR / "INDEX.md"
    if skills_index.exists():
        idx = skills_index.read_text(encoding="utf-8").strip()
        if len(idx) > 100:
            parts.append(f"## Skill Library (reusable patterns — use these before writing from scratch)\n{idx}")

    # Recent successful trajectories — what approaches worked before (Reflexion exemplar pattern)
    if TRAJECTORIES_FILE.exists():
        traj = TRAJECTORIES_FILE.read_text(encoding="utf-8")
        if len(traj) > 100:
            parts.append(f"## Recent Successful Approaches (learn from these — don't reinvent)\n{traj[-2500:]}")

    # Research queue — topics to learn
    if RESEARCH_QUEUE_FILE.exists():
        rq = RESEARCH_QUEUE_FILE.read_text(encoding="utf-8").strip()
        if rq and len(rq) > 60:
            parts.append(f"## Research Queue (knowledge gaps — tackle during self-growth sessions)\n{rq[-2000:]}")

    # Self-critique trend — what dimensions are weak?
    if GROWTH_FILE.exists():
        m2 = json.loads(GROWTH_FILE.read_text(encoding="utf-8"))
        history = m2.get("self_critique_history", [])
        if history:
            last3 = history[-3:]
            dims = ["research_depth", "code_quality", "self_growth", "task_completion"]
            averages = {}
            for d in dims:
                vals = [h[d] for h in last3 if d in h]
                averages[d] = round(sum(vals)/len(vals), 1) if vals else "?"
            weak = [d for d, v in averages.items() if isinstance(v, float) and v < 2.5]
            critique_summary = "Last 3 sessions avg: " + " | ".join(f"{d}={v}" for d, v in averages.items())
            if weak:
                critique_summary += f"\n⚠️  WEAK AREAS (avg < 2.5): {', '.join(weak)} — focus on improving these this session"
            parts.append(f"## Self-Critique Trend\n{critique_summary}")

    # Project health trend
    if HEALTH_LOG_FILE.exists():
        health_data = json.loads(HEALTH_LOG_FILE.read_text(encoding="utf-8"))
        if health_data:
            last = health_data[-1]
            trend = [h["health_score"] for h in health_data[-5:]]
            parts.append(
                f"## Project Health\n"
                f"Last check ({last['ts']}): score {last['health_score']}/3, "
                f"{last['tests_passed']} passed, {last['tests_failed']} failed\n"
                f"Trend (last 5): {trend}"
            )

    # Recent git commits
    git_log = execute_tool("run_command", {"command": "git log --oneline -12"})
    parts.append(f"## Recent Git Commits\n{git_log}")

    return "\n\n---\n\n".join(parts)


# ──────────────────────────────────────────────────────────────
# MAIN SESSION
# ──────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────
# BACKEND MODE SELECTION
# ──────────────────────────────────────────────────────────────

def choose_backend_mode() -> str:
    """Always ask user to choose backend mode on every run."""
    print("\n" + "="*55)
    print("Choose backend for agent sessions:")
    print()
    print("  1) vscode  — Claude Code (VS Code subscription)")
    print("              No API cost. Auto-waits on rate limit.")
    print()
    print("  2) api     — Anthropic API (pay-per-token)")
    print("              $15/day budget. Faster, no rate waits.")
    print("="*55)

    while True:
        try:
            choice = input("Enter 1 or 2 [default: 1]: ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "1"
        if choice in ("", "1", "vscode"):
            mode = "vscode"
            break
        elif choice in ("2", "api"):
            mode = "api"
            break
        print("Enter 1 or 2")

    BACKEND_MODE_FILE.write_text(json.dumps({"mode": mode}, indent=2), encoding="utf-8")
    print(f"Mode '{mode}' saved. Delete agent/backend_mode.json to re-select.\n")
    return mode


def _check_vscode_rate_limit() -> bool:
    """Returns True (and prints wait time) if still rate limited."""
    if not RATE_LIMIT_FILE.exists():
        return False
    try:
        data = json.loads(RATE_LIMIT_FILE.read_text(encoding="utf-8"))
        retry_after = datetime.fromisoformat(data["retry_after"])
        now = datetime.now()
        if now < retry_after:
            wait_secs = int((retry_after - now).total_seconds())
            mins = wait_secs // 60
            print(f"VS Code Claude rate limited. Retry at {retry_after.strftime('%H:%M:%S')} "
                  f"({mins}m {wait_secs % 60}s remaining)")
            print(f"Message: {data.get('message', '')[:150]}")
            return True
        RATE_LIMIT_FILE.unlink(missing_ok=True)
        return False
    except Exception:
        RATE_LIMIT_FILE.unlink(missing_ok=True)
        return False


def _save_vscode_rate_limit(message: str):
    """Parse rate limit message and save retry time."""
    import re as _re
    now = datetime.now()
    retry_dt = None
    for pat in [
        r'reset at (\d{1,2}:\d{2}\s*(?:AM|PM))',
        r'retry after (\d{1,2}:\d{2}\s*(?:AM|PM))',
        r'available at (\d{1,2}:\d{2}\s*(?:AM|PM))',
        r'at (\d{1,2}:\d{2}\s*(?:AM|PM))',
    ]:
        m = _re.search(pat, message, _re.IGNORECASE)
        if m:
            try:
                t = datetime.strptime(m.group(1).strip(), "%I:%M %p")
                t = t.replace(year=now.year, month=now.month, day=now.day)
                from datetime import timedelta
                if t <= now:
                    t += timedelta(days=1)
                retry_dt = t
                break
            except ValueError:
                pass

    if retry_dt is None:
        from datetime import timedelta
        retry_dt = now + timedelta(hours=1)
        print("Could not parse retry time — defaulting to 1 hour.")

    RATE_LIMIT_FILE.write_text(json.dumps({
        "retry_after": retry_dt.isoformat(),
        "message": message[:500]
    }, indent=2), encoding="utf-8")
    print(f"Rate limit saved. Agent will auto-resume at {retry_dt.strftime('%H:%M:%S')}.")


def _call_vscode_claude(full_prompt: str, timeout: int = 300) -> tuple:
    """Call claude.cmd non-interactively, piping prompt via stdin. Returns (stdout, stderr)."""
    import tempfile
    npm_bin = os.path.join(os.environ.get("APPDATA", ""), "npm")
    claude_cmd = os.path.join(npm_bin, "claude.cmd")
    if not os.path.exists(claude_cmd):
        return "", f"ERROR: claude.cmd not found at {claude_cmd}. Run: npm i -g @anthropic-ai/claude-code"
    tmp = None
    try:
        # Write prompt to temp file — avoids Windows 8191-char arg limit
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write(full_prompt)
            tmp = f.name
        # Pipe file content to claude via cmd's type command
        # Strip ANTHROPIC_API_KEY so claude CLI uses the subscription (not API credits)
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_API_KEY_OVERRIDE", None)
        cmd = f'type "{tmp}" | "{claude_cmd}" --print --dangerously-skip-permissions'
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace", cwd=str(ROOT),
            env=env
        )
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "", f"TIMEOUT: claude CLI did not respond in {timeout}s"
    except Exception as e:
        return "", f"ERROR: {e}"
    finally:
        if tmp:
            try: os.unlink(tmp)
            except Exception: pass


def _get_session_directive(session_num: int) -> str:
    """Returns the directive for this session number (shared by API + VS Code modes)."""
    if session_num % 5 == 0:
        critique_diag = ""
        if GROWTH_FILE.exists():
            gm = json.loads(GROWTH_FILE.read_text(encoding="utf-8"))
            history = gm.get("self_critique_history", [])
            if history:
                last5 = history[-5:]
                dims = ["research_depth", "code_quality", "self_growth", "task_completion"]
                weakest = min(dims, key=lambda d: sum(h.get(d, 2) for h in last5) / max(len(last5), 1))
                critique_diag = f" Your weakest dimension over last 5 sessions: '{weakest}' — make this the focus."
        return (
            f"This is session #{session_num} — a SELF-GROWTH session.{critique_diag}\n\n"
            "Work through ALL of these in order:\n"
            "1. **Research queue**: Read agent/research_queue.md — tackle HIGH priority items first. "
            "For each: web_search → fetch top results → update knowledge.md → delete item from queue.\n"
            "2. **Anthropic updates**: Fetch https://docs.anthropic.com/en/docs/about-claude/models — "
            "check for new models, features, pricing. Update config.json + knowledge.md.\n"
            "3. **Financial audit**: Review growth_metrics.json spend. "
            "If avg session cost > $3, find cost reduction (caching, model switch, context trimming).\n"
            "4. **GitHub intelligence**: Search 'FastAPI best practices 2026', 'React 19 patterns', "
            "'autonomous agent self-improvement' — absorb 3+ concrete techniques into knowledge.md.\n"
            "5. **Agent architecture**: Read agent/run.py fully. Find one thing to improve. Implement it.\n"
            "6. **Competitor intelligence**: Search 'car auction SaaS Canada 2026', 'vehicle flipping app' — "
            "find gaps, update BACKLOG with marketing ideas.\n\n"
            "The product gets better when the agent gets smarter. Every hour on self-growth is worth 3 hours on features."
        )

    specialist_cycle = ["revenue", "scraper", "calculations", "ui", "revenue"]
    specialist = specialist_cycle[session_num % len(specialist_cycle)]
    specialist_directives = {
        "revenue": (
            "**REVENUE SPECIALIST SESSION**\n"
            "Identity: You are a Senior Monetization Engineer + Growth Marketer hybrid.\n"
            "Mission: Turn AutoFlip into a revenue-generating machine. Every decision goes through: 'does this get more people to pay?'\n"
            "Critical rules: Never break the free tier. Test payment flows in sandbox before any live config.\n"
            "Priority: Stripe Checkout integration (top backlog). If done, pick next revenue item.\n"
            "Deliverables: Working payment flow with sandbox test, webhook handler, user.plan update, confirmation UI.\n"
            "Success metrics: User can click 'Go Pro' → complete Stripe checkout → account upgrades → no manual steps.\n"
            "Tools: Use `run_experiment` for any pricing/conversion change. Use `save_skill` for Stripe patterns."
        ),
        "scraper": (
            "**DATA SPECIALIST SESSION**\n"
            "Identity: You are a Senior Web Scraping Engineer + Data Pipeline Architect.\n"
            "Mission: Maximize the volume and quality of salvage vehicle data. More sources = more deals = more value.\n"
            "Critical rules: Research ToS before scraping. Handle rate limits with exponential backoff. Never crash on HTML changes.\n"
            "Priority: IAA Canada (https://www.iaai.com/vehiclesearch?lang=en_CA) or Copart Canada — research first.\n"
            "Deliverables: New scraper module in backend/app/scrapers/, integrated into runner.py, at least 1 pytest test.\n"
            "Success metrics: New source returns 10+ listings with price, title, URL. All existing tests still pass.\n"
            "Tools: Use `run_experiment` baseline=listing count. Use `fetch_url` to inspect site HTML before coding."
        ),
        "calculations": (
            "**DEAL INTELLIGENCE SPECIALIST SESSION**\n"
            "Identity: You are a Senior Quantitative Analyst + Algorithm Engineer.\n"
            "Mission: Make the deal scores so accurate that subscribers trust them completely.\n"
            "Critical rules: ALWAYS use `run_experiment` — baseline test count, modify, evaluate, auto-revert if regression.\n"
            "Priority: Mileage penalty in scoring, colour premium (black/white sell faster), or time-on-market decay.\n"
            "Deliverables: Modified calculations.py, updated tests, experiment_results.tsv entry showing improvement.\n"
            "Success metrics: More tests passing, deal scores better reflect real-world flip outcomes (check past deals).\n"
            "Simplicity rule: A 1% scoring improvement that adds 20 lines of hacky code = discard. Simplification = always keep."
        ),
        "ui": (
            "**UX SPECIALIST SESSION**\n"
            "Identity: You are a Senior Frontend Engineer + Conversion Rate Optimizer.\n"
            "Mission: Make the app so good-looking and easy to use that users upgrade just to keep using it.\n"
            "Critical rules: Mobile-first (375px). Run `npm run build` before AND after every change. WCAG AA contrast.\n"
            "Priority: Watchlist/saved listings, better mobile layout, price drop badge, or side-by-side comparison.\n"
            "Deliverables: Working React component, Tailwind styling, empty/loading/error states, no build errors.\n"
            "Success metrics: Feature works on 375px mobile, all existing frontend tests pass, build succeeds.\n"
            "Tools: Use `save_skill` for any reusable React/Tailwind patterns."
        ),
    }
    base = specialist_directives.get(specialist, specialist_directives["revenue"])
    return (
        f"{base}\n\n"
        "Pick ONE small, completable task (max 3-5 files). "
        "Implement completely, validate, commit, push, call task_complete. "
        "If a current_task.md exists — resume it first, specialist mode applies to next task after."
    )


# ──────────────────────────────────────────────────────────────
# VS CODE SESSION (no API cost, rate-limit aware)
# ──────────────────────────────────────────────────────────────

def run_vscode_session():
    """Run a session using Claude Code CLI.

    claude -p runs Claude Code's own agentic loop using its built-in tools
    (Bash, Read, Write, Edit, WebSearch, WebFetch). We give it the full task
    context and let it work autonomously — no custom tool loop needed.
    """
    if _check_vscode_rate_limit():
        return

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"AutoFlip Agent [VS Code Mode]  |  {ts}")
    print('='*60)

    context = build_context()
    metrics = json.loads(GROWTH_FILE.read_text(encoding="utf-8")) if GROWTH_FILE.exists() else {}
    session_num = metrics.get("total_sessions", 0) + 1
    session_directive = _get_session_directive(session_num)

    # Strip API budget section from context — irrelevant in VS Code mode
    import re as _re
    context_clean = _re.sub(
        r'## Budget & Financial Intelligence.*?(?=\n## |\Z)', '',
        context, flags=_re.DOTALL
    ).strip()

    # Build task prompt — Claude Code uses its own tools (Bash/Read/Write/WebSearch)
    task_prompt = f"""You are working autonomously on the AutoFlip project.
Project root: {ROOT}

NOTE: You are running via VS Code subscription — there are NO API credits or budget limits to worry about. Ignore any dollar amounts or budget references in the context below.

{SYSTEM_PROMPT}

=== SESSION CONTEXT ===
{context_clean}

=== YOUR MISSION THIS SESSION ===
{session_directive}

=== EXECUTION RULES ===
- Python: py (not python3) | Node: C:\\Program Files\\nodejs\\npm.cmd
- Backend import check: py -c "import sys; sys.path.insert(0,'backend'); from app.main import app; print('OK')"
- Run tests: py -m pytest backend/tests/ -x -q --tb=short
- Frontend build: PATH="/c/Program Files/nodejs:$PATH" "C:\\Program Files\\nodejs\\npm.cmd" --prefix frontend run build 2>&1 | tail -10
- Commit: git add -A && git commit -m "agent: <what> — <why>" && git push origin main
- After every backend change: run import check + tests before committing. Never commit broken code.

=== TOOL EQUIVALENTS (use these instead of Python tool calls) ===

**update_current_task** — track progress so next session resumes here:
Write agent/current_task.md with:
  # Current Task — <name>
  ## Completed Steps
  - [x] step done
  ## Remaining Steps
  - [ ] next step
  ## Last Commit
  `commit message`

**run_experiment** — safe accept/reject gate (Karpathy autoresearch pattern):
  1. Run: py -m pytest backend/tests/ -q --tb=no 2>&1 | tail -3  → record baseline number
  2. Make your changes
  3. Run tests again → compare
  4. If improved: git add -A && git commit -m "exp: <hypothesis> [baseline→new]"
  5. If worse: git stash && git stash drop  (revert all changes)
  6. Append result to agent/experiment_results.tsv: commit\\tmetric_before\\tmetric_after\\tdelta\\tkeep/discard\\thypothesis

**run_health_check** — always run before finishing:
  py -c "import sys; sys.path.insert(0,'backend'); from app.main import app; print('OK')"
  py -m pytest backend/tests/ -q --tb=no 2>&1 | tail -5
  If any test fails → fix it before writing DONE block.

**save_skill** — save reusable patterns to skill library:
  Write agent/skills/<snake_case_name>.py with the pattern as a docstring + code.
  Append to agent/skills/INDEX.md: - **name** — description (agent/skills/name.py)

**write_post_mortem** — learn from failures (call when something took >3 turns to fix):
  Append to agent/knowledge.md:
  ### Post-Mortem — <date>
  **What failed:** ...
  **Root cause:** ...
  **Fix applied:** ...
  **Prevention rule:** ...

**add_to_research_queue** — queue knowledge gaps:
  Append to agent/research_queue.md:
  - [PRIORITY] **topic** — Added <date>
    _Why: reason_

**request_api_key** — log needed API keys:
  Append to agent/api_requests.md with service, env var name, what it unlocks, urgency.

=== MANDATORY SESSION WORKFLOW (follow ALL phases — same as API mode) ===

PHASE 1 — Research first: web_search before writing any code. Find current best practices.
PHASE 2 — Read & plan: read every file you will touch. Write a 3-step plan.
PHASE 2.5 — Experiment design: for calculation/scraper/agent changes, use run_experiment gate.
PHASE 3 — Implement: call update_current_task first. Commit after each logical step.
PHASE 3.5 — Dev-QA retry: if health_check fails, fix it. Max 3 attempts. Escalate to backlog if still failing.
PHASE 4 — Validate: run import check + tests + frontend build before every commit.
PHASE 5 — Commit & push: git add -A && git commit && git push.
PHASE 6 — Self-reflect & grow (MANDATORY, NO EXCEPTIONS):
  A. Append a concrete lesson to agent/knowledge.md
  B. call save_skill for any reusable pattern you wrote
  C. call add_to_research_queue for any knowledge gap you noticed
  D. Run health check — fix any regressions before finishing
  E. Update agent/BACKLOG.md — mark item [x] done, add new ideas
  F. Update or delete agent/current_task.md

=== END YOUR RESPONSE WITH THIS EXACT BLOCK ===
DONE: <one sentence: what was accomplished>
IMPACT: <why this matters to users or revenue>
FILES: <comma-separated files changed>
"""

    print(f"  Calling claude CLI — running autonomously (may take 5-20 min)...")
    stdout, stderr = _call_vscode_claude(task_prompt, timeout=1200)
    combined = stdout + "\n" + stderr
    combined_lower = combined.lower()

    ts_short = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Detect rate limit
    rate_limit_keywords = ["rate limit", "usage limit", "limit reached", "try again", "reset at", "quota exceeded"]
    if any(kw in combined_lower for kw in rate_limit_keywords):
        _save_vscode_rate_limit(combined)
        # Show retry time — outer loop handles sleeping
        retry_dt = None
        if RATE_LIMIT_FILE.exists():
            try:
                retry_dt = datetime.fromisoformat(
                    json.loads(RATE_LIMIT_FILE.read_text(encoding="utf-8"))["retry_after"]
                )
            except Exception:
                pass
        print(f"\n{'='*60}")
        print(f"  RATE LIMIT HIT — Claude Pro quota exhausted.")
        if retry_dt:
            wait_secs = max(int((retry_dt - datetime.now()).total_seconds()), 0)
            mins = wait_secs // 60
            print(f"  Retry at: {retry_dt.strftime('%H:%M:%S')}  ({mins}m {wait_secs % 60}s from now)")
        else:
            print(f"  Retry time unknown — will wait 1 hour.")
        print(f"{'='*60}")
        return

    if not stdout:
        msg = f"Claude CLI returned no output. stderr: {stderr[:300]}"
        print(f"  {msg}")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n---\n## {ts_short} — ERROR [vscode]\n{msg}\n")
        finalize_report()
        return

    # Parse summary block from end of output
    import re as _re
    summary_m = _re.search(r'DONE:\s*(.+)',   stdout)
    impact_m  = _re.search(r'IMPACT:\s*(.+)', stdout)
    files_m   = _re.search(r'FILES:\s*(.+)',  stdout)

    summary = summary_m.group(1).strip() if summary_m else f"VS Code session {ts_short}"
    impact  = impact_m.group(1).strip()  if impact_m  else ""
    files   = [f.strip() for f in files_m.group(1).split(",")] if files_m else []

    print(f"\nDone: {summary}")

    # Activity log
    log_entry = f"\n---\n## {ts_short} — FEATURE [vscode]\n**{summary}**\n"
    if impact: log_entry += f"Impact: {impact}\n"
    if files:  log_entry += f"Files: {', '.join(files)}\n"
    log_entry += f"Output tail:\n{stdout[-800:]}\nCost: $0.00 (VS Code mode)\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)

    append_to_report(
        f"\n## {ts_short} — FEATURE [vscode]\n**{summary}**\n"
        + (f"> {impact}\n" if impact else "")
        + (f"Files: `{'`, `'.join(files)}`\n" if files else "")
        + "Cost: $0.00 (VS Code mode)\n"
    )

    # Growth metrics
    m_data = json.loads(GROWTH_FILE.read_text(encoding="utf-8")) if GROWTH_FILE.exists() else {
        "total_sessions": 0, "total_cost_usd": 0.0,
        "categories": {}, "self_improvements": [], "next_session_hints": []
    }
    m_data["total_sessions"] += 1
    m_data["categories"]["feature"] = m_data["categories"].get("feature", 0) + 1
    GROWTH_FILE.write_text(json.dumps(m_data, indent=2), encoding="utf-8")

    clear_checkpoint()
    finalize_report()
    sync_state(f"after vscode session {ts_short}")


def sync_state(label: str = "state"):
    """Push all agent state files to GitHub so any machine can resume."""
    execute_tool("run_command", {
        "command": (
            "git add agent/activity_log.md agent/knowledge.md agent/BACKLOG.md "
            "agent/growth_metrics.json agent/daily_budget.json agent/checkpoint.json "
            "agent/current_task.md agent/api_requests.md agent/reports/ 2>nul & "
            f"git diff --cached --quiet || git commit -m \"agent: sync state — {label}\" && "
            "git push origin main"
        ),
        "timeout": 30
    })


def run_session():
    global client
    if client is None:
        client = anthropic.Anthropic()  # only created when API mode is actually used
    cfg_live = load_config()  # reload in case agent updated config
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Pull latest state from GitHub before starting (supports multi-machine)
    execute_tool("run_command", {"command": "git pull origin main --rebase 2>&1 | tail -3", "timeout": 30})

    spend = get_today_spend()
    limit = cfg_live["daily_limit_usd"]

    print(f"\n{'='*60}")
    print(f"AutoFlip Agent  |  {ts}")
    print(f"Budget: ${spend:.4f} spent  |  ${limit - spend:.4f} remaining")
    print('='*60)

    if spend >= limit:
        print("Daily budget exhausted. Will resume tomorrow.")
        append_to_report(f"\n_Budget exhausted at {datetime.now().strftime('%H:%M')}. Resuming tomorrow._\n")
        sync_state("budget exhausted")
        return

    context = build_context()
    metrics = json.loads(GROWTH_FILE.read_text(encoding="utf-8")) if GROWTH_FILE.exists() else {}
    session_num = metrics.get("total_sessions", 0) + 1
    session_directive = _get_session_directive(session_num)
    messages = [{
        "role": "user",
        "content": f"{context}\n\n---\n\n{session_directive}"
    }]

    total_in = 0
    total_out = 0
    task_result = None
    model = cfg_live["model"]
    max_turns = cfg_live["session_max_turns"]

    for turn in range(max_turns):
        # Retry on rate limit
        for attempt in range(6):
            try:
                response = client.messages.create(
                    model=model,
                    max_tokens=8096,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=messages
                )
                break
            except anthropic.RateLimitError:
                wait = 60 * (attempt + 1)
                print(f"  Rate limit — waiting {wait}s (attempt {attempt+1}/6)...")
                time.sleep(wait)
        else:
            print("Rate limit retries exhausted.")
            break

        total_in  += response.usage.input_tokens
        total_out += response.usage.output_tokens

        # Mid-session budget check
        session_cost = total_in * cfg_live["input_cost_per_token"] + total_out * cfg_live["output_cost_per_token"]

        # Circuit breaker (Autonomous Optimization Architect pattern):
        # If burn rate after turn 15 projects > 70% of daily budget, inject model-switch advisory
        if turn == 15 and model != "claude-haiku-4-5-20251001":
            projected_total = session_cost * (max_turns / 15)
            budget_fraction = projected_total / limit
            if budget_fraction > 0.7:
                print(f"  Circuit breaker: projected ${projected_total:.2f} > 70% of ${limit:.2f} budget")
                # Inject cost advisory into next tool results
                circuit_msg = (
                    f"CIRCUIT BREAKER ALERT: At turn 15 you've spent ${session_cost:.4f}. "
                    f"Projected session cost: ${projected_total:.2f} (>{budget_fraction*100:.0f}% of ${limit:.2f} daily budget). "
                    f"Switch to simpler remaining steps. If the remaining work is research/reading/writing, "
                    f"call optimize_costs to switch to haiku ($0.80/MTok vs $3/MTok = 4x cheaper). "
                    f"If writing complex code, continue but be more concise."
                )
                # Queue for injection in the next tool_results
                messages.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": "circuit_breaker",
                     "content": circuit_msg}
                ]})

        if spend + session_cost > limit:
            print("Budget limit hit mid-session. Saving checkpoint...")
            # Extract what we were working on from the last tool call
            last_tool = next(
                (b.name for b in reversed(response.content) if b.type == "tool_use"),
                "unknown"
            )
            save_checkpoint(
                task_description="Mid-session when budget ran out — check backlog for active item",
                progress=f"Was executing tool '{last_tool}' at turn {turn+1}. Review recent git log and backlog to determine exact state."
            )
            break

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text") and block.text:
                    print(f"Agent: {block.text[:400]}")
            break

        if response.stop_reason == "tool_use":
            tool_results = []
            done = False

            for block in response.content:
                if block.type != "tool_use":
                    continue

                inp_preview = json.dumps(block.input)[:120]
                print(f"  [{turn+1:02d}] {block.name}({inp_preview})")

                result = execute_tool(block.name, block.input)

                if result == "__TASK_COMPLETE__":
                    task_result = block.input
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Session complete."
                    })
                    done = True
                    break

                preview = str(result)[:200].replace("\n", " ")
                print(f"        {preview}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result)
                })

            # Warn agent when running low on turns so it wraps up
            if not done and turn >= max_turns - 8:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": "turn_warning",
                    "content": f"WARNING: Only {max_turns - turn - 1} turns remaining. Commit what you have and call task_complete now."
                })

            messages.append({"role": "user", "content": tool_results})
            if done:
                break

    # Record spend
    cost = record_spend(total_in, total_out)
    new_total = get_today_spend()
    print(f"\nSession: ${cost:.4f}  |  Today total: ${new_total:.4f}")

    # Write to activity log + report + growth metrics
    ts_short = datetime.now().strftime("%Y-%m-%d %H:%M")
    if task_result:
        summary      = task_result.get("summary", "Improvement made")
        category     = task_result.get("category", "feature")
        impact       = task_result.get("impact", "")
        files        = task_result.get("files_changed", [])
        self_impr    = task_result.get("self_improvement", "")
        next_hint    = task_result.get("next_session_hint", "")
        task_name_for_traj = task_result.get("task_name", summary[:60])

        # Activity log
        log_entry = f"\n---\n## {ts_short} — {category.upper().replace('_',' ')}\n**{summary}**\n"
        if impact:       log_entry += f"Impact: {impact}\n"
        if files:        log_entry += f"Files: {', '.join(files)}\n"
        if self_impr:    log_entry += f"Self-improvement: {self_impr}\n"
        if next_hint:    log_entry += f"Next session: {next_hint}\n"
        log_entry += f"Cost: ${cost:.4f}\n"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)

        # Daily report
        report_section = f"\n## {ts_short} — {category.upper().replace('_',' ')}\n**{summary}**\n"
        if impact:    report_section += f"> {impact}\n"
        if files:     report_section += f"Files: `{'`, `'.join(files)}`\n"
        if self_impr: report_section += f"Agent improved itself: {self_impr}\n"
        if next_hint: report_section += f"Next priority: _{next_hint}_\n"
        report_section += f"Cost: ${cost:.4f}\n"
        append_to_report(report_section)

        # Growth metrics
        metrics = json.loads(GROWTH_FILE.read_text(encoding="utf-8")) if GROWTH_FILE.exists() else {
            "total_sessions": 0, "total_cost_usd": 0.0,
            "categories": {}, "self_improvements": [], "next_session_hints": []
        }
        self_critique = task_result.get("self_critique", {})

        metrics["total_sessions"] += 1
        metrics["total_cost_usd"] = round(metrics["total_cost_usd"] + cost, 6)
        metrics["categories"][category] = metrics["categories"].get(category, 0) + 1
        if self_impr:
            metrics["self_improvements"].append({"ts": ts_short, "what": self_impr})
        if next_hint:
            # Keep only last 5 hints
            metrics["next_session_hints"] = ([{"ts": ts_short, "hint": next_hint}]
                                              + metrics["next_session_hints"])[:5]
        if self_critique:
            if "self_critique_history" not in metrics:
                metrics["self_critique_history"] = []
            metrics["self_critique_history"].append({"ts": ts_short, **self_critique})
            metrics["self_critique_history"] = metrics["self_critique_history"][-10:]
        GROWTH_FILE.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

        # Auto-store trajectory (Reflexion/SAGE pattern — successful approaches as future exemplars)
        traj_entry = (
            f"\n---\n## {ts_short} — {category}\n"
            f"**Task:** {task_name_for_traj}\n"
            f"**Approach:** {summary}\n"
            f"**Why it worked:** {impact}\n"
        )
        if not hasattr(task_result, '__trajectory_saved'):
            with open(TRAJECTORIES_FILE, "a", encoding="utf-8") as traj_f:
                traj_f.write(traj_entry)
            # Keep file from growing unbounded
            if TRAJECTORIES_FILE.exists():
                lines = TRAJECTORIES_FILE.read_text(encoding="utf-8").split("\n---\n")
                if len(lines) > 30:
                    TRAJECTORIES_FILE.write_text("\n---\n".join(lines[-25:]), encoding="utf-8")

        clear_checkpoint()  # task finished cleanly — no resume needed
        print(f"\nDone: {summary}")
        if self_impr:
            print(f"Self-improved: {self_impr}")
    else:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n---\n## {ts_short} — INCOMPLETE\nSession ended without task_complete. Cost: ${cost:.4f}\n")
        append_to_report(f"\n## {ts_short} — INCOMPLETE\nSession cost: ${cost:.4f}\n")

    finalize_report()
    sync_state(f"after session {ts_short}")


# ──────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────

def show_status():
    spend = get_today_spend()
    limit = cfg["daily_limit_usd"]
    print(f"Today ({date.today()}):")
    print(f"  Spent:     ${spend:.4f}")
    print(f"  Remaining: ${limit - spend:.4f} / ${limit:.2f}")

    if GROWTH_FILE.exists():
        m = json.loads(GROWTH_FILE.read_text(encoding="utf-8"))
        print(f"\nAll-time growth:")
        print(f"  Total sessions:  {m['total_sessions']}")
        print(f"  Total API cost:  ${m['total_cost_usd']:.4f}")
        print(f"  By category:     {m['categories']}")
        if m.get("self_improvements"):
            si = m.get("self_improvements")
            if si:
                print(f"  Last self-improvement: {si[-1]['what']}")
        if m.get("next_session_hints"):
            print(f"  Next priority: {m['next_session_hints'][0]['hint']}")

    report = get_report_file()
    if report.exists():
        print(f"\nToday's report:")
        print(report.read_text(encoding="utf-8")[-2000:])

    if API_REQUESTS_FILE.exists():
        content = API_REQUESTS_FILE.read_text(encoding="utf-8")
        unchecked = [l for l in content.splitlines() if l.startswith("## [ ]")]
        if unchecked:
            print(f"\nAPI keys needed ({len(unchecked)}):")
            for u in unchecked:
                print(f"  {u}")


if __name__ == "__main__":
    if "--status" in sys.argv:
        show_status()
        sys.exit(0)

    once = "--once" in sys.argv
    interval_h = cfg["interval_hours"]

    # Ask user to choose backend (saved after first answer)
    backend_mode = choose_backend_mode()

    if backend_mode == "vscode":
        print("AutoFlip Autonomous Agent [VS Code Mode — no API cost]")
        print(f"Interval: {interval_h}h  |  Rate limit: auto-detected from claude CLI")

        if once:
            run_vscode_session()
        else:
            while True:
                try:
                    run_vscode_session()
                except KeyboardInterrupt:
                    print("\nStopped.")
                    break
                except Exception as e:
                    print(f"Session crashed: {e}")
                    with open(LOG_FILE, "a", encoding="utf-8") as f:
                        f.write(
                            f"\n---\n## {datetime.now().strftime('%Y-%m-%d %H:%M')} — CRASH [vscode]\n"
                            f"Error: {e}\n"
                        )

                # Smart sleep for VS Code mode:
                # - Rate limited → sleep until retry_after, then immediately retry
                # - Unfinished task → retry in 30 min
                # - Done cleanly → sleep full interval
                if RATE_LIMIT_FILE.exists():
                    try:
                        data = json.loads(RATE_LIMIT_FILE.read_text(encoding="utf-8"))
                        retry_after = datetime.fromisoformat(data["retry_after"])
                        now = datetime.now()
                        sleep_secs = max(int((retry_after - now).total_seconds()) + 90, 90)
                        wake = retry_after.strftime("%H:%M:%S")
                        mins = sleep_secs // 60
                        print(f"\n  Sleeping until {wake} ({mins}m {sleep_secs % 60}s)...")
                        for remaining in range(sleep_secs, 0, -60):
                            m = remaining // 60
                            print(f"  ... {m}m remaining", end="\r", flush=True)
                            time.sleep(min(60, remaining))
                        print(f"\n  Woke up at {datetime.now().strftime('%H:%M:%S')} — retrying session...")
                        RATE_LIMIT_FILE.unlink(missing_ok=True)
                        continue  # retry immediately, no interval sleep
                    except Exception:
                        print("\n  Rate limit file unreadable — sleeping 1 hour...")
                        time.sleep(3600)
                        RATE_LIMIT_FILE.unlink(missing_ok=True)
                        continue
                elif CURRENT_TASK_FILE.exists():
                    print(f"\nUnfinished task detected. Resuming in 30 minutes...")
                    time.sleep(30 * 60)
                else:
                    print(f"\nSleeping {interval_h}h until next session...")
                    time.sleep(interval_h * 3600)

    else:
        # API mode — original behavior
        print("AutoFlip Autonomous Agent [API Mode]")
        print(f"Model: {cfg['model']}  |  Budget: ${cfg['daily_limit_usd']}/day  |  Interval: {interval_h}h")

        if once:
            run_session()
        else:
            while True:
                try:
                    run_session()
                except KeyboardInterrupt:
                    print("\nStopped.")
                    break
                except Exception as e:
                    print(f"Session crashed: {e}")
                    with open(LOG_FILE, "a", encoding="utf-8") as f:
                        f.write(
                            f"\n---\n## {datetime.now().strftime('%Y-%m-%d %H:%M')} — CRASH\n"
                            f"Error: {e}\n"
                        )

                # Smart sleep:
                # - Budget exhausted → sleep until midnight
                # - Unfinished work → run again in 30 min
                # - Task completed cleanly → sleep full interval
                if get_today_spend() >= cfg["daily_limit_usd"]:
                    secs = seconds_until_midnight()
                    wake = datetime.now().fromtimestamp(time.time() + secs).strftime("%Y-%m-%d %H:%M")
                    print(f"\nBudget exhausted. Sleeping until midnight — resuming at {wake}")
                    time.sleep(secs)
                elif CURRENT_TASK_FILE.exists():
                    print(f"\nUnfinished task detected. Resuming in 30 minutes...")
                    time.sleep(30 * 60)
                else:
                    print(f"\nSleeping {interval_h}h until next session...")
                    time.sleep(interval_h * 3600)
