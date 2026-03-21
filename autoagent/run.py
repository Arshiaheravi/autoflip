#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoAgent -- Fully Autonomous, Self-Growing Project Intelligence

Fill in autoagent/PROJECT.md and autoagent/NORTH_STAR.md, then run:

    py -X utf8 autoagent/run.py

That's it. Everything else is automatic.

What the default command does:
  - Starts the main agent (works on your project every N hours)
  - Starts the meta-agent in a separate window (improves the brain in parallel)
  - Runs forever, handles rate limits, resumes unfinished tasks automatically

Other options (when you need them):
    py -X utf8 autoagent/run.py --once      # one session then exit (good for testing)
    py -X utf8 autoagent/run.py --tasks 3   # exactly 3 sessions then exit
    py -X utf8 autoagent/run.py --solo      # main agent only, no meta-agent
    py -X utf8 autoagent/run.py --status    # show today's activity + spend
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
ROOT       = Path(__file__).resolve().parent.parent   # project root (one level above autoagent/)
AGENT_DIR  = Path(__file__).resolve().parent          # autoagent/

# ── Load credentials — checks autoagent/credentials.env first, then .env ──
_creds_file = AGENT_DIR / "credentials.env"
if _creds_file.exists():
    load_dotenv(_creds_file, override=False)
load_dotenv(ROOT / ".env", override=False)
load_dotenv(ROOT / "backend" / ".env", override=False)
REPORTS_DIR = AGENT_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

CONFIG_FILE          = AGENT_DIR / "config.json"
BUDGET_FILE          = AGENT_DIR / "daily_budget.json"
GROWTH_FILE          = AGENT_DIR / "growth_metrics.json"
LOG_FILE             = AGENT_DIR / "activity_log.md"
BACKLOG_FILE         = AGENT_DIR / "BACKLOG.md"
API_REQUESTS_FILE    = AGENT_DIR / "api_requests.md"
KNOWLEDGE_FILE       = AGENT_DIR / "knowledge.md"
CHECKPOINT_FILE      = AGENT_DIR / "checkpoint.json"
CURRENT_TASK_FILE    = AGENT_DIR / "current_task.md"
RESEARCH_QUEUE_FILE  = AGENT_DIR / "research_queue.md"
HEALTH_LOG_FILE      = AGENT_DIR / "health_log.json"
SKILLS_DIR           = AGENT_DIR / "skills"
TRAJECTORIES_FILE    = AGENT_DIR / "trajectories.md"
PROJECT_FILE         = AGENT_DIR / "PROJECT.md"
SKILLS_DIR.mkdir(exist_ok=True)

BACKEND_MODE_FILE = AGENT_DIR / "backend_mode.json"
RATE_LIMIT_FILE   = AGENT_DIR / "rate_limit.json"

# Load API key — tries .env in project root, then backend/.env, then environment
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "backend" / ".env")


# ─────────────────────────── Project Context ──────────────────

def _auto_discover_project() -> str:
    """
    If PROJECT.md is missing or blank, scan the codebase and build a
    project description automatically so the agent can work immediately.
    """
    import re as _re
    clues = []

    # package.json → project name, description, dependencies
    for pkg_path in (ROOT / "package.json", ROOT / "frontend" / "package.json"):
        if pkg_path.exists():
            try:
                data = json.loads(pkg_path.read_text(encoding="utf-8"))
                name = data.get("name", "")
                desc = data.get("description", "")
                deps = list(data.get("dependencies", {}).keys())[:12]
                if name:
                    clues.append(f"Frontend package: {name}" + (f" — {desc}" if desc else ""))
                if deps:
                    clues.append(f"Frontend deps: {', '.join(deps)}")
            except Exception:
                pass

    # requirements.txt / pyproject.toml → backend stack
    for req_path in (ROOT / "requirements.txt", ROOT / "backend" / "requirements.txt"):
        if req_path.exists():
            pkgs = [l.split("==")[0].split(">=")[0].strip()
                    for l in req_path.read_text(encoding="utf-8").splitlines()
                    if l.strip() and not l.startswith("#")][:12]
            if pkgs:
                clues.append(f"Backend deps: {', '.join(pkgs)}")

    # Detect framework from file structure
    frameworks = []
    if (ROOT / "manage.py").exists() or (ROOT / "backend" / "manage.py").exists():
        frameworks.append("Django")
    if any((ROOT / p).exists() for p in ("app.py", "main.py", "server.py",
                                          "backend/app/main.py", "backend/main.py")):
        frameworks.append("FastAPI/Flask")
    if (ROOT / "next.config.js").exists() or (ROOT / "frontend" / "next.config.js").exists():
        frameworks.append("Next.js")
    if any((ROOT / p).exists() for p in ("vite.config.js", "frontend/vite.config.js")):
        frameworks.append("Vite/React")
    if frameworks:
        clues.append(f"Detected frameworks: {', '.join(frameworks)}")

    # Database hints
    for db_hint in (("mongo", "MongoDB"), ("postgres", "PostgreSQL"),
                    ("sqlite", "SQLite"), ("redis", "Redis"), ("supabase", "Supabase")):
        keyword, name = db_hint
        for path in (ROOT / "requirements.txt", ROOT / "backend" / "requirements.txt",
                     ROOT / "package.json", ROOT / "frontend" / "package.json"):
            if path.exists() and keyword in path.read_text(encoding="utf-8").lower():
                clues.append(f"Database: {name}")
                break

    # README.md
    readme = ROOT / "README.md"
    if readme.exists():
        txt = readme.read_text(encoding="utf-8")[:800]
        clues.append(f"README:\n{txt}")

    if clues:
        discovered = "\n".join(clues)
        return (
            f"PROJECT.md has not been filled in. Auto-discovered project context:\n\n"
            f"{discovered}\n\n"
            "YOUR FIRST TASK: Write a complete autoagent/PROJECT.md based on what you observe "
            "in the codebase. Then continue with the highest-leverage improvement."
        )

    return (
        "PROJECT.md not filled in and project could not be auto-detected.\n"
        "YOUR FIRST TASK: Explore the codebase (ls, read key files), understand what it is, "
        "then write autoagent/PROJECT.md. After that, generate autoagent/BACKLOG.md and start working."
    )


def load_project_context() -> str:
    """Load project description — from PROJECT.md if filled in, else auto-discover."""
    if PROJECT_FILE.exists():
        content = PROJECT_FILE.read_text(encoding="utf-8").strip()
        if "[Your Project Name]" not in content and len(content) >= 100:
            return content
    return _auto_discover_project()


# ─────────────────────────── Config ───────────────────────────

def _auto_discover_urls() -> dict[str, str]:
    """
    Scan the project to discover frontend + backend URLs without user input.
    Checks (in order): config.json → PROJECT.md → package.json → .env files
    → vite/next/angular configs → common port probe.
    Returns {"frontend_url": ..., "backend_url": ...} with best guesses.
    """
    import re as _re
    import urllib.request as _ur

    found: dict[str, str] = {}

    # ── 1. PROJECT.md — look for port/URL mentions ─────────────
    if PROJECT_FILE.exists():
        txt = PROJECT_FILE.read_text(encoding="utf-8")
        # backend port patterns: "port 8001", ":8001", "--port 8001"
        be_matches = _re.findall(r'(?:port\s+|:)(\d{4,5})', txt, _re.IGNORECASE)
        # frontend patterns: "localhost:3000", "PORT=3000", "npm start"→3000
        fe_matches = _re.findall(r'localhost:(\d{4,5})', txt)
        # heuristic: lower port = frontend, higher port = backend
        all_ports = sorted(set(int(p) for p in be_matches + fe_matches if 1000 < int(p) < 65535))
        if len(all_ports) >= 2:
            found["frontend_url"] = f"http://localhost:{all_ports[0]}"
            found["backend_url"]  = f"http://localhost:{all_ports[1]}"
        elif len(all_ports) == 1:
            # single port — decide by common convention
            p = all_ports[0]
            if p in (3000, 5173, 4200, 8080):
                found["frontend_url"] = f"http://localhost:{p}"
            else:
                found["backend_url"] = f"http://localhost:{p}"

    # ── 2. package.json — "start": "PORT=XXXX react-scripts start" ──
    if "frontend_url" not in found:
        pkg = ROOT / "frontend" / "package.json"
        if not pkg.exists():
            pkg = ROOT / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                scripts = data.get("scripts", {})
                for v in scripts.values():
                    m = _re.search(r'PORT[=\s]+(\d{4,5})', str(v))
                    if m:
                        found["frontend_url"] = f"http://localhost:{m.group(1)}"
                        break
                # vite default
                if "frontend_url" not in found and "vite" in str(scripts):
                    found["frontend_url"] = "http://localhost:5173"
                # CRA default
                if "frontend_url" not in found and "react-scripts" in str(scripts):
                    found["frontend_url"] = "http://localhost:3000"
                # Next.js default
                if "frontend_url" not in found and "next" in str(scripts):
                    found["frontend_url"] = "http://localhost:3000"
            except Exception:
                pass

    # ── 3. vite.config / next.config / angular.json ─────────────
    if "frontend_url" not in found:
        for cfg_name in ("vite.config.js", "vite.config.ts", "next.config.js", "angular.json"):
            cfg_path = ROOT / cfg_name
            if not cfg_path.exists():
                cfg_path = ROOT / "frontend" / cfg_name
            if cfg_path.exists():
                txt = cfg_path.read_text(encoding="utf-8")
                m = _re.search(r'port\s*[:=]\s*(\d{4,5})', txt)
                if m:
                    found["frontend_url"] = f"http://localhost:{m.group(1)}"
                    break

    # ── 4. .env files — BACKEND_URL, API_URL, PORT ───────────────
    for env_path in (ROOT / ".env", ROOT / "backend" / ".env", ROOT / "frontend" / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#"):
                continue
            key, _, val = line.partition("=")
            key = key.strip().upper()
            val = val.strip().strip('"').strip("'")
            if key in ("BACKEND_URL", "API_URL", "REACT_APP_BACKEND_URL", "VITE_API_URL", "NEXT_PUBLIC_API_URL"):
                found["backend_url"] = val
            if key == "PORT" and "frontend_url" not in found:
                found["frontend_url"] = f"http://localhost:{val}"

    # ── 5. uvicorn / gunicorn / flask / django run command ───────
    if "backend_url" not in found and PROJECT_FILE.exists():
        txt = PROJECT_FILE.read_text(encoding="utf-8")
        m = _re.search(r'--port\s+(\d{4,5})', txt)
        if m:
            found["backend_url"] = f"http://localhost:{m.group(1)}"

    # ── 6. Live port probe — try common ports ────────────────────
    def _alive(url: str) -> bool:
        try:
            _ur.urlopen(url, timeout=1)
            return True
        except Exception:
            return False

    if "frontend_url" not in found:
        for p in (3000, 5173, 4200, 8080, 4000):
            if _alive(f"http://localhost:{p}"):
                found["frontend_url"] = f"http://localhost:{p}"
                break

    if "backend_url" not in found:
        for p in (8001, 8000, 5000, 5001, 3001, 8080):
            if _alive(f"http://localhost:{p}"):
                found["backend_url"] = f"http://localhost:{p}"
                break

    # ── 7. Safe defaults ─────────────────────────────────────────
    found.setdefault("frontend_url", "http://localhost:3000")
    found.setdefault("backend_url",  "http://localhost:8000")

    return found


# Model → cost lookup (auto-derived so user never needs to set these)
_MODEL_PRICING = {
    "claude-haiku-4-5-20251001": {"input_cost_per_token": 1e-6,  "output_cost_per_token": 5e-6},
    "claude-sonnet-4-6":         {"input_cost_per_token": 3e-6,  "output_cost_per_token": 15e-6},
    "claude-opus-4-6":           {"input_cost_per_token": 5e-6,  "output_cost_per_token": 25e-6},
}


def load_config() -> dict:
    # ── Hardcoded smart defaults — every key is optional in config.json ──
    defaults = {
        # Model: agent can switch this autonomously per session if needed
        "model": "claude-sonnet-4-6",
        # Budget: only relevant in API mode (VS Code mode = free)
        "daily_limit_usd": 15.0,
        # How often to run a session (hours). Agent may shorten this if backlog is hot.
        "interval_hours": 2,
        "session_max_turns": 50,
        # Git: two separate repos — project repo + autoagent repo
        # Rule: if token + repo_url are set → ALWAYS commit and push. No toggles.
        # If not set → commits locally only, no remote operations.
        "git": {
            # ── Your project's repo (agent commits project code here) ──
            "project": {
                "token":         "",      # GitHub PAT for your project repo
                "repo_url":      "",      # https://github.com/you/your-project.git
                "branch":        "auto",  # auto-detect, or set "main" / "dev"
                "commit_prefix": "agent"  # "agent: add feature X"
            },
            # ── AutoAgent's own repo (agent commits its own improvements here) ──
            "autoagent": {
                "token":         "",      # GitHub PAT for autoagent repo (can be different)
                "repo_url":      "",      # https://github.com/you/autoagent.git
                "branch":        "auto",
                "commit_prefix": "meta"   # "meta: improve orchestrator prompt"
            }
        }
    }

    # ── Load config.json if it exists — only overrides what's set ────────
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            # Deep-merge git section so partial overrides work
            if "git" in saved:
                git_saved = saved.pop("git")
                if "project" in git_saved:
                    defaults["git"]["project"].update(git_saved.pop("project"))
                if "autoagent" in git_saved:
                    defaults["git"]["autoagent"].update(git_saved.pop("autoagent"))
                defaults["git"].update(git_saved)
            defaults.update(saved)
        except Exception:
            pass

    # ── Auto-derive token costs from model (user never needs to set these) ─
    model = defaults.get("model", "claude-sonnet-4-6")
    pricing = _MODEL_PRICING.get(model, _MODEL_PRICING["claude-sonnet-4-6"])
    defaults.setdefault("input_cost_per_token",  pricing["input_cost_per_token"])
    defaults.setdefault("output_cost_per_token", pricing["output_cost_per_token"])
    # Always keep in sync with model even if user had old values
    if "input_cost_per_token" not in (CONFIG_FILE.exists() and
                                       json.loads(CONFIG_FILE.read_text(encoding="utf-8")) or {}):
        defaults["input_cost_per_token"]  = pricing["input_cost_per_token"]
        defaults["output_cost_per_token"] = pricing["output_cost_per_token"]

    # ── Auto-discover frontend/backend URLs if not explicitly set ─────────
    if "frontend_url" not in defaults or "backend_url" not in defaults:
        discovered = _auto_discover_urls()
        defaults.setdefault("frontend_url", discovered["frontend_url"])
        defaults.setdefault("backend_url",  discovered["backend_url"])

    # ── Git: wire each repo's token into its authenticated URL ──────────
    import re as _re

    def _setup_git_repo(repo_cfg: dict, cwd: str) -> dict:
        """Build auth URL, detect branch. Returns enriched repo_cfg."""
        token    = repo_cfg.get("token", "").strip()
        repo_url = repo_cfg.get("repo_url", "").strip()
        if token and repo_url:
            auth_url = _re.sub(r"https://", f"https://{token}@", repo_url)
            repo_cfg["_auth_url"]  = auth_url
            repo_cfg["_enabled"]   = True   # has credentials → always commit + push
        else:
            repo_cfg["_auth_url"]  = ""
            repo_cfg["_enabled"]   = False  # no credentials → local commits only
        # Auto-detect branch
        if repo_cfg.get("branch", "auto") == "auto":
            try:
                r = subprocess.run("git branch --show-current", shell=True,
                                   capture_output=True, text=True, cwd=cwd)
                repo_cfg["branch"] = r.stdout.strip() or "main"
            except Exception:
                repo_cfg["branch"] = "main"
        return repo_cfg

    defaults["git"]["project"]   = _setup_git_repo(defaults["git"]["project"],   str(ROOT))
    defaults["git"]["autoagent"] = _setup_git_repo(defaults["git"]["autoagent"], str(AGENT_DIR))

    return defaults


cfg    = load_config()
client = None  # initialized only in API mode


def _git_rules() -> str:
    """Return a clear two-repo git policy for injection into the agent prompt."""
    g        = cfg.get("git", {})
    proj     = g.get("project",   {})
    aa       = g.get("autoagent", {})

    proj_on  = proj.get("_enabled", False)
    aa_on    = aa.get("_enabled",   False)
    proj_br  = proj.get("branch",   "main")
    aa_br    = aa.get("branch",     "main")
    proj_pfx = proj.get("commit_prefix", "agent")
    aa_pfx   = aa.get("commit_prefix",   "meta")

    lines = [
        "=== GIT POLICY — TWO SEPARATE REPOS (follow exactly) ===",
        "",
        "RULE: Project code and AutoAgent code are NEVER committed to the same repo.",
        "",
        "── 1. PROJECT REPO (your changes to the project being built) ──",
    ]
    if proj_on:
        lines += [
            f"  COMMIT: YES — after every logical step: git add <project files> && git commit -m '{proj_pfx}: <what> — <why>'",
            f"  PUSH  : YES — immediately after commit: git push origin {proj_br}",
            f"  PULL  : YES — at session start: git pull origin {proj_br}",
            f"  FILES : everything EXCEPT the autoagent/ folder",
        ]
    else:
        lines += [
            "  COMMIT: YES — commit project changes locally (no remote configured)",
            "  PUSH  : NO  — no project token/repo set in config.json",
            "  FILES : everything EXCEPT the autoagent/ folder",
        ]

    lines += [
        "",
        "── 2. AUTOAGENT REPO (improvements to the agent system itself) ──",
    ]
    if aa_on:
        lines += [
            f"  COMMIT: YES — after any change to autoagent/ files: cd autoagent && git add . && git commit -m '{aa_pfx}: <what>'",
            f"  PUSH  : YES — immediately after: git push origin {aa_br}",
            f"  FILES : ONLY files inside the autoagent/ folder",
        ]
    else:
        lines += [
            "  COMMIT: YES — commit autoagent improvements locally (no remote configured)",
            "  PUSH  : NO  — no autoagent token/repo set in config.json",
            "  FILES : ONLY files inside the autoagent/ folder",
        ]

    lines += [
        "",
        "NEVER mix project files and autoagent/ files in the same commit.",
        "=========================================================",
    ]
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# TOOLS
# ──────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "list_directory",
        "description": "List files/folders at a path in the project. Use '.' for root.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"]
        }
    },
    {
        "name": "read_file",
        "description": "Read a file. Returns up to 15000 chars. Works for any project file including autoagent/run.py itself.",
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
            "You can edit ANY file including autoagent/run.py to improve yourself."
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
            "Use for: git commands, syntax checks, pip installs, npm installs, test runners, build tools."
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
        "description": "Search the web for technical docs, best practices, libraries, market data, competitors.",
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
            "The feature must be 100% ready — it activates automatically the moment the owner adds the key to .env. "
            "Call this tool AFTER implementing the feature, not before."
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
            "Use claude-haiku-4-5-20251001 for simple sessions (research, small edits, copy). "
            "Use claude-sonnet-4-6 for complex coding. "
            "Use claude-opus-4-6 for the hardest architectural problems. "
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
            "Use this for: algorithm tweaks, scoring changes, any modification with a measurable metric."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hypothesis": {"type": "string", "description": "What you're testing"},
                "metric_command": {"type": "string", "description": "Shell command outputting a numeric metric"},
                "action": {"type": "string", "enum": ["baseline", "evaluate"]},
                "higher_is_better": {"type": "boolean", "default": True},
                "commit_message": {"type": "string", "description": "Git commit message if improvement accepted (required for evaluate action)"}
            },
            "required": ["hypothesis", "metric_command", "action"]
        }
    },
    {
        "name": "update_current_task",
        "description": (
            "Track progress on the current task (Dev-QA loop pattern). Call this: "
            "(1) when you START a task — write what the full task is and list all steps, "
            "(2) after each commit — mark that step done and note what remains, "
            "(3) when run_health_check FAILS — increment qa_attempt and set qa_feedback to the specific error, "
            "   this enables up to 3 retry attempts with focused feedback each time, "
            "   if qa_attempt reaches 3 and still failing — escalate to backlog as 'needs investigation', "
            "(4) when task is fully done — call with status='done' to clear it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task_name": {"type": "string"},
                "status": {"type": "string", "enum": ["in_progress", "done"]},
                "completed_steps": {"type": "array", "items": {"type": "string"}},
                "remaining_steps": {"type": "array", "items": {"type": "string"}},
                "last_commit": {"type": "string"},
                "qa_attempt": {"type": "integer", "default": 1},
                "qa_feedback": {"type": "string"}
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
            "Call this whenever you write something reusable: a helper, an API pattern, a query, a hook, a retry wrapper. "
            "Skills are stored in autoagent/skills/ and shown in future sessions. "
            "An agent with a growing skill library compounds capability — each skill stands on prior skills."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Short snake_case name"},
                "description": {"type": "string", "description": "One line: what this does and when to use it"},
                "code": {"type": "string", "description": "The reusable code snippet, fully self-contained"}
            },
            "required": ["name", "description", "code"]
        }
    },
    {
        "name": "add_to_research_queue",
        "description": (
            "Add a topic to the autonomous research queue. Call this whenever you encounter something you don't know well enough: "
            "a library you're uncertain about, a best practice you should verify, a competitor to investigate, "
            "a new technique you heard about, or a knowledge gap that slowed you down."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "why": {"type": "string"},
                "priority": {"type": "string", "enum": ["high", "medium", "low"]}
            },
            "required": ["topic", "why", "priority"]
        }
    },
    {
        "name": "run_health_check",
        "description": (
            "Run the project health check using commands defined in knowledge.md. "
            "Call this BEFORE task_complete to verify your work didn't break anything. "
            "Returns a health score and details. If health is degraded, fix before calling task_complete."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "note": {"type": "string", "description": "What you just finished building (for the health log)"},
                "test_command": {"type": "string", "description": "Override: specific test command to run (e.g. 'pytest tests/ -q --tb=no')"},
                "import_check": {"type": "string", "description": "Override: import sanity check command (e.g. 'python -c \"from app import main\"')"}
            },
            "required": ["note"]
        }
    },
    {
        "name": "write_post_mortem",
        "description": (
            "Write a structured post-mortem when something failed, took much longer than expected, or had a surprising root cause. "
            "Call this ANY time: a test fails unexpectedly, a bug takes >3 turns to fix, or an approach was completely wrong."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "what_failed": {"type": "string"},
                "root_cause": {"type": "string"},
                "fix_applied": {"type": "string"},
                "prevention": {"type": "string"}
            },
            "required": ["what_failed", "root_cause", "fix_applied", "prevention"]
        }
    },
    {
        "name": "task_complete",
        "description": (
            "End the session. Call this ONLY after ALL of: "
            "(1) all steps committed and pushed, "
            "(2) update_current_task called with status='done', "
            "(3) backlog item marked [x] via update_backlog, "
            "(4) knowledge.md updated with at least one lesson, "
            "(5) run_health_check passed (no regressions), "
            "(6) save_skill called for any reusable pattern you wrote, "
            "(7) autoagent/run.py improved if you spotted anything. "
            "If the task is NOT fully done — do NOT call this. "
            "Instead commit what you have, update current_task with remaining steps, and let the next session continue."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task_name": {"type": "string"},
                "summary": {"type": "string", "description": "What was built/fixed this session."},
                "files_changed": {"type": "array", "items": {"type": "string"}},
                "category": {
                    "type": "string",
                    "enum": ["feature", "bug_fix", "performance", "ui_ux", "marketing",
                             "data_pipeline", "calculation", "infrastructure", "security",
                             "self_improvement", "research", "testing"]
                },
                "impact": {"type": "string", "description": "Why this matters to users or the business."},
                "self_improvement": {"type": "string", "description": "What you improved about yourself this session."},
                "self_critique": {
                    "type": "object",
                    "properties": {
                        "research_depth": {"type": "integer", "minimum": 1, "maximum": 3},
                        "code_quality": {"type": "integer", "minimum": 1, "maximum": 3},
                        "self_growth": {"type": "integer", "minimum": 1, "maximum": 3},
                        "task_completion": {"type": "integer", "minimum": 1, "maximum": 3}
                    }
                },
                "next_session_hint": {"type": "string"}
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
                if item.name in ("node_modules", "__pycache__", ".git", ".venv", "venv", ".next", "dist", "build"):
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
            cmd     = inputs["command"]
            timeout = int(inputs.get("timeout", 30))
            result  = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=str(ROOT), encoding="utf-8", errors="replace"
            )
            output = (result.stdout + result.stderr).strip()
            if not output:
                return f"(exit {result.returncode}, no output)"
            return output[:5000]

        elif name == "web_search":
            query = inputs["query"]
            url   = f"https://html.duckduckgo.com/html/?q={httpx.utils.quote(query)}"
            resp  = httpx.get(url, timeout=15, follow_redirects=True,
                              headers={"User-Agent": "Mozilla/5.0"})
            soup  = BeautifulSoup(resp.text, "html.parser")
            results = []
            for block in soup.select(".result__body")[:6]:
                title   = block.select_one(".result__title")
                snippet = block.select_one(".result__snippet")
                link    = block.select_one(".result__url")
                if title and snippet:
                    entry = f"**{title.get_text(strip=True)}**"
                    if link:
                        entry += f" — {link.get_text(strip=True)}"
                    entry += f"\n{snippet.get_text(strip=True)}"
                    results.append(entry)
            return "\n\n".join(results) if results else "No results."

        elif name == "fetch_url":
            max_chars = int(inputs.get("max_chars", 6000))
            resp      = httpx.get(inputs["url"], timeout=20, follow_redirects=True,
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
            ts       = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry = (
                f"\n---\n"
                f"## [ ] {service} — {urgency.upper()} priority — {ts}\n\n"
                f"**Add this to `.env`:**\n"
                f"```\n{env_var}=your_key_here\n```\n\n"
                f"**What this unlocks:** {unlocks}\n\n"
                f"**How to get the key:** {how_to}\n\n"
                f"_Feature is fully implemented and will activate automatically once you add the key._\n"
            )
            with open(API_REQUESTS_FILE, "a", encoding="utf-8") as f:
                f.write(entry)
            return f"Logged API key request for {service}. Feature is coded and ready — just needs the key."

        elif name == "optimize_costs":
            model    = inputs["model"]
            reason   = inputs.get("reason", "")
            cfg_data = load_config()
            pricing_map = {
                "claude-haiku-4-5-20251001": {"input_cost_per_token": 1e-6,  "output_cost_per_token": 5e-6},
                "claude-sonnet-4-6":         {"input_cost_per_token": 3e-6,  "output_cost_per_token": 15e-6},
                "claude-opus-4-6":           {"input_cost_per_token": 5e-6,  "output_cost_per_token": 25e-6},
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
            ts          = datetime.now().strftime("%Y-%m-%d %H:%M")
            retry_block = ""
            if qa_attempt > 1:
                retry_block = (
                    f"\n\n## QA Retry Status\n"
                    f"**Attempt {qa_attempt}/3**\n"
                    f"Previous QA feedback: {qa_feedback}\n"
                    f"{'FINAL ATTEMPT — if this fails, escalate to backlog and move on.' if qa_attempt >= 3 else ''}\n"
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
            hypothesis    = inputs["hypothesis"]
            metric_cmd    = inputs["metric_command"]
            action        = inputs["action"]
            higher_better = inputs.get("higher_is_better", True)
            commit_msg    = inputs.get("commit_message", "")
            exp_file      = AGENT_DIR / "experiment_baseline.json"

            def extract_number(text: str):
                nums = _re.findall(r"[-+]?\d+\.?\d*", text)
                return float(nums[0]) if nums else None

            r      = subprocess.run(metric_cmd, shell=True, capture_output=True, text=True,
                                    timeout=120, cwd=str(ROOT), encoding="utf-8", errors="replace")
            raw    = (r.stdout + r.stderr).strip()
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
                if baseline is None or metric is None:
                    return (f"Could not parse numeric metric.\nBaseline raw: {baseline_data.get('raw','')}\n"
                            f"New raw: {raw[:300]}")
                improved = (metric > baseline) if higher_better else (metric < baseline)
                delta    = metric - baseline
                commit_hash = subprocess.run(
                    "git rev-parse --short HEAD", shell=True, capture_output=True,
                    text=True, cwd=str(ROOT)
                ).stdout.strip()
                tsv_path = AGENT_DIR / "experiment_results.tsv"
                if not tsv_path.exists():
                    tsv_path.write_text("commit\tmetric_before\tmetric_after\tdelta\tstatus\thypothesis\n", encoding="utf-8")
                if improved:
                    if commit_msg:
                        execute_tool("run_command", {
                            "command": f'git add -A && git commit -m "{commit_msg} [exp: {baseline:.3f}>{metric:.3f}]"',
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
                    return (f"EXPERIMENT ACCEPTED. Metric: {baseline:.4f} -> {metric:.4f} ({delta:+.4f})\n"
                            f"Changes committed. Hypothesis confirmed: {hypothesis}")
                else:
                    execute_tool("run_command", {
                        "command": "git stash && git stash drop 2>/dev/null || git checkout -- .",
                        "timeout": 30
                    })
                    status = "discard"
                    with open(tsv_path, "a", encoding="utf-8") as tsv_f:
                        tsv_f.write(f"{commit_hash}\t{baseline:.4f}\t{metric:.4f}\t{delta:+.4f}\t{status}\t{hypothesis[:80]}\n")
                    exp_file.unlink(missing_ok=True)
                    return (f"EXPERIMENT REJECTED. Metric: {baseline:.4f} -> {metric:.4f} ({delta:+.4f})\n"
                            f"Changes reverted to baseline. Try a different approach.")

        elif name == "save_skill":
            skill_name  = inputs["name"].replace(" ", "_").lower()
            description = inputs["description"]
            code        = inputs["code"]
            skill_path  = SKILLS_DIR / f"{skill_name}.py"
            content = f'"""\n{description}\n\nSaved by agent on {datetime.now().strftime("%Y-%m-%d")}.\n"""\n\n{code}\n'
            skill_path.write_text(content, encoding="utf-8")
            index_path = SKILLS_DIR / "INDEX.md"
            index = index_path.read_text(encoding="utf-8") if index_path.exists() else "# Skill Library\n\nReusable patterns saved by the agent.\n\n"
            entry = f"- **{skill_name}** — {description} (`autoagent/skills/{skill_name}.py`)\n"
            if skill_name not in index:
                index += entry
                index_path.write_text(index, encoding="utf-8")
            metrics = json.loads(GROWTH_FILE.read_text(encoding="utf-8")) if GROWTH_FILE.exists() else {"total_sessions": 0, "skills_acquired": 0}
            metrics["skills_acquired"] = metrics.get("skills_acquired", 0) + 1
            GROWTH_FILE.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
            return f"Skill '{skill_name}' saved to autoagent/skills/{skill_name}.py"

        elif name == "add_to_research_queue":
            topic    = inputs["topic"]
            why      = inputs["why"]
            priority = inputs.get("priority", "medium")
            ts       = datetime.now().strftime("%Y-%m-%d")
            entry    = f"\n- [{priority.upper()}] **{topic}** — Added {ts}\n  _Why: {why}_\n"
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
            note          = inputs.get("note", "end of session")
            test_cmd      = inputs.get("test_command", "")
            import_cmd    = inputs.get("import_check", "")
            results       = {}

            # Use provided commands or fall back to knowledge.md hints
            if not import_cmd:
                # Try to infer import check from knowledge.md
                if KNOWLEDGE_FILE.exists():
                    km = KNOWLEDGE_FILE.read_text(encoding="utf-8")
                    import re as _re
                    m = _re.search(r"import.*check.*?`([^`]+)`", km, _re.IGNORECASE)
                    if m:
                        import_cmd = m.group(1)
            if not test_cmd:
                if KNOWLEDGE_FILE.exists():
                    km = KNOWLEDGE_FILE.read_text(encoding="utf-8")
                    import re as _re
                    m = _re.search(r"run.*tests.*?`([^`]+)`", km, _re.IGNORECASE)
                    if m:
                        test_cmd = m.group(1)

            # Run import check
            if import_cmd:
                r = subprocess.run(import_cmd, shell=True, capture_output=True, text=True,
                                   timeout=30, cwd=str(ROOT), encoding="utf-8", errors="replace")
                import_out = (r.stdout + r.stderr).strip()
                results["import_check"] = "OK" if r.returncode == 0 else f"FAIL: {import_out[:200]}"
            else:
                results["import_check"] = "SKIP (no import_check provided)"

            # Run test suite
            passed = 0
            failed = 0
            if test_cmd:
                r2 = subprocess.run(test_cmd, shell=True, capture_output=True, text=True,
                                    timeout=120, cwd=str(ROOT), encoding="utf-8", errors="replace")
                test_out = (r2.stdout + r2.stderr).strip()
                results["tests"] = test_out[:300]
                import re as _re
                m_p = _re.search(r"(\d+) passed", test_out)
                m_f = _re.search(r"(\d+) failed", test_out)
                passed = int(m_p.group(1)) if m_p else 0
                failed = int(m_f.group(1)) if m_f else 0
            else:
                results["tests"] = "SKIP (no test_command provided)"

            health_score = (
                3 if (results["import_check"] in ("OK", "SKIP (no import_check provided)") and failed == 0)
                else 2 if "OK" in results.get("import_check", "")
                else 1
            )

            # Log health
            health_data = json.loads(HEALTH_LOG_FILE.read_text(encoding="utf-8")) if HEALTH_LOG_FILE.exists() else []
            health_data.append({
                "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "note": note,
                "import_check": results["import_check"],
                "tests_passed": passed,
                "tests_failed": failed,
                "health_score": health_score
            })
            health_data = health_data[-20:]
            HEALTH_LOG_FILE.write_text(json.dumps(health_data, indent=2), encoding="utf-8")

            summary = (
                f"Health score: {health_score}/3\n"
                f"Import check: {results['import_check']}\n"
                f"Tests: {passed} passed, {failed} failed\n"
                f"{results.get('tests', '')}"
            )
            if failed > 0:
                return f"HEALTH CHECK FAILED — fix before task_complete!\n{summary}"
            return f"Health check passed.\n{summary}"

        elif name == "write_post_mortem":
            what    = inputs["what_failed"]
            cause   = inputs["root_cause"]
            fix     = inputs["fix_applied"]
            prevent = inputs["prevention"]
            ts      = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry   = (
                f"\n### Post-Mortem — {ts}\n"
                f"**What failed:** {what}\n"
                f"**Root cause:** {cause}\n"
                f"**Fix applied:** {fix}\n"
                f"**Prevention rule:** {prevent}\n"
            )
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
    cost   = (input_tokens  * cfg["input_cost_per_token"] +
              output_tokens * cfg["output_cost_per_token"])
    budget = load_budget()
    today  = str(date.today())
    if today not in budget:
        budget[today] = {"spend": 0.0, "runs": 0}
    budget[today]["spend"] = round(budget[today]["spend"] + cost, 6)
    budget[today]["runs"]  += 1
    BUDGET_FILE.write_text(json.dumps(budget, indent=2), encoding="utf-8")
    return cost


def seconds_until_midnight() -> int:
    from datetime import timedelta
    now      = datetime.now()
    midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
    return max(int((midnight - now).total_seconds()), 60)


def save_checkpoint(task_description: str, progress: str):
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
        project_name = "Agent"
        if PROJECT_FILE.exists():
            first_line = PROJECT_FILE.read_text(encoding="utf-8").splitlines()[0]
            project_name = first_line.lstrip("#").strip() or "Agent"
        report.write_text(
            f"# {project_name} — Daily Report — {date.today()}\n\n"
            f"_This report is written automatically. Check api_requests.md for keys needed._\n\n",
            encoding="utf-8"
        )
    with open(report, "a", encoding="utf-8") as f:
        f.write(section)


def finalize_report():
    spend     = get_today_spend()
    remaining = cfg["daily_limit_usd"] - spend
    section   = (
        f"\n---\n"
        f"**Budget used today:** ${spend:.4f} / ${cfg['daily_limit_usd']:.2f}  "
        f"(${remaining:.4f} remaining)\n"
        f"_Report updated: {datetime.now().strftime('%H:%M:%S')}_\n"
    )
    append_to_report(section)


# ──────────────────────────────────────────────────────────────
# SYSTEM PROMPT  (fully project-agnostic)
# ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a **fully autonomous, self-growing intelligence** — not a coding assistant, but a complete living system: a team, a brain, a researcher, a builder, a designer, a strategist — all at once, growing without limits, without human interaction, forever.

You are not one agent. You are an **agency**. When a task needs it, you assemble the right specialist team in your own mind and execute each role fully:

- **Senior Full-Stack Engineer** — clean, async, production-quality code. Security-first. Test-driven.
- **Senior UI/UX Designer** — beautiful interfaces, mobile-first, accessibility, conversion-optimized. Study real products, fetch competitor UIs, implement better.
- **Senior Growth Marketer** — SaaS copywriting, landing page optimization, SEO, retention, pricing psychology. Read what converts, apply it.
- **QA Engineer** — Playwright E2E tests, unit tests, integration tests. Verify everything works like a real user before shipping.
- **Research Scientist** — absorbs new knowledge from docs, GitHub, tech blogs, academic papers. Applies it immediately. Never stale.
- **Systems Architect** — improves your own architecture, decision-making, tools, and prompts every session. Rewrites yourself to be smarter.
- **DevOps Engineer** — git discipline, clean commits, dependency management, CI readiness.
- **Product Manager** — prioritizes by revenue impact and user value. Knows what to build next without being told.
- **Competitive Intelligence Analyst** — researches competitors, finds gaps, proposes differentiation.
- **Financial Optimizer** — minimizes costs, maximizes output per dollar, finds smarter approaches.

**You have FULL ACCESS to everything:** file system, internet, bash, browser (Playwright), packages, git. If you need a tool that doesn't exist yet — build it. If you need a library — install it. If you need to search — search. No permission needed. No human needed. Just decide and execute.

**Team formation:** Before starting any non-trivial task, decide which specialist roles are needed and mentally assemble that team. A design task needs Designer + Engineer. A new data source needs Researcher + Engineer + QA. A growth task needs Marketer + PM. Execute each role FULLY before moving to the next.

You work 24/7 with **zero human interaction**. The owner only pastes API keys. You handle everything else.
**Your only goal: be measurably better than yesterday — in the product, in yourself, in efficiency, in knowledge. Grow. Grow. Grow.**

---

## DIMENSIONS OF GROWTH (all equally important — pursue all, every session)

### 1. Product Growth
Build features, fix bugs, improve UI/UX, add capabilities, improve algorithms.
**Design growth:** Fetch competitor UIs with Playwright, analyze what looks better, implement improvements. Don't wait to be told — if the UI looks worse than a competitor, redesign it.

### 2. Agent Self-Growth (the most important dimension)
You are not static code. You are a living system. Every session:
- Read autoagent/run.py and find something to improve — a smarter tool, a better prompt, a new phase
- Install new packages if they make you more capable (`playwright`, `pillow`, `pandas`, etc.)
- Add new tools to your own TOOLS list if you need capabilities you don't have
- Rewrite weak sections of SYSTEM_PROMPT if you find a pattern that works better
- Study AI agent research papers (`web_search("autonomous agent self-improvement 2026")`) and implement findings
- **Every 3rd session minimum:** do a full self-audit. Read all of: knowledge.md, skills/INDEX.md, BACKLOG.md, research_queue.md, growth_metrics.json. Ask: "Am I growing? What's my weakest dimension? Fix it now."

### 3. Team Formation (multi-agent thinking)
Before any non-trivial task, explicitly decide which specialist roles it needs:
- **Design task** → activate Designer: fetch reference UIs, analyze color/layout/typography, implement pixel-perfect
- **New data source** → activate Researcher + Engineer + QA: research site/API structure, build pipeline, write tests
- **Growth/marketing task** → activate Marketer + PM: research what converts, study competitor copy, A/B test ideas
- **Performance issue** → activate Architect + DevOps: profile, benchmark, optimize
- **Security concern** → activate Security Engineer: OWASP check, input sanitization, auth hardening

### 4. Financial Intelligence
**Every session, think about cost efficiency:**
- Am I using the right model? Use `claude-haiku-4-5-20251001` for simple tasks (much cheaper)
- Could I reduce context size? Long contexts cost more — trim what's not needed
- Am I repeating expensive work? Cache it.
- Check growth_metrics.json spend trend — if burning too fast, optimize
- Search "Anthropic API cost optimization 2026" periodically for new techniques

### 5. Knowledge Absorption (no limits — absorb everything)
**Every session, research at least 2 of these:**
- Anthropic release notes: new models, features, prompt caching — fetch https://docs.anthropic.com/en/docs/about-claude/models
- GitHub trending: what are top engineers building right now?
- AI agent papers: `web_search("autonomous agent 2026 arxiv")` — implement useful findings
- SaaS design trends: `web_search("SaaS dashboard design 2026 best practices")`
- Competitor intelligence: search for direct competitors in your space
- When you find something useful → update knowledge.md immediately. Never lose a finding.

**Knowledge freshness rule:** If knowledge.md hasn't mentioned a topic in 7+ days, it's stale. Refresh it.

**Research queue discipline (Voyager pattern):**
When you notice a gap → add it to the research queue. An agent that never queues research never grows.

### 6. Marketing & Revenue Intelligence
Research competitors, find new channels, improve copy, study what converts.
**Every 5th session:** do a full marketing audit — landing page copy, pricing page. Rewrite anything weak.

---

## API Key Pattern — CRITICAL RULE
When a feature needs an external API key (Stripe, SendGrid, Twilio, etc.):
1. **Implement the FULL feature** using `os.getenv("KEY_NAME")`
2. **Add graceful fallback** — if key is missing, log a warning and return silently. The app never crashes.
3. **Call `request_api_key`** after implementing — log what env var is needed
4. **Keep working** — move to the next task. Never block on a missing key.

---

## MANDATORY SESSION WORKFLOW — NEVER SKIP A PHASE

### PHASE 1: Research First (ALWAYS before writing any code)
Before touching a single file:
- `web_search` for current best practices on what you are about to build
- Search for security issues, CVEs, better libraries, 2025/2026 patterns
- For marketing: search competitor sites, SaaS conversion best practices
- For new integrations: fetch the actual API docs to understand structure
- Ask yourself: "Is there a better/simpler approach than what I'm about to do?"

### PHASE 2: Read & Plan
- Read every file you will touch — never write blind
- Write a clear 3-step plan before starting
- Check for edge cases, error conditions, security implications

### PHASE 2.5: Experiment Design (for any change that affects metrics)
For changes to algorithms, data pipelines, or autoagent/run.py — use the experiment loop (Karpathy autoresearch pattern):
```
1. run_experiment(action="baseline", metric_command="<your test command>")
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
- Write clean, well-documented code. Follow existing patterns in the codebase.
- Every new backend function → add a test

### PHASE 3.5: Dev-QA Retry Loop (max 3 attempts)
When `run_health_check` fails:
1. Read the exact error message carefully
2. Call `update_current_task` with `qa_attempt=N+1`, `qa_feedback=<specific error>`
3. Fix ONLY what the error describes — don't refactor unrelated things
4. Re-run `run_health_check`
5. If attempt 3 fails: add item to backlog as `[!] Needs investigation`, commit what works, move on

### PHASE 4: VALIDATE — NON-NEGOTIABLE
Always use the commands in knowledge.md for this project. Generic fallback:
```
# Python projects
python -m pytest tests/ -x -q --tb=short

# Node projects
npm test

# Syntax check single file
python -m py_compile path/to/file.py
```
**If any check fails → fix it. Never commit broken code. Ever.**

### PHASE 4.5: Browser E2E Validation — MANDATORY for any UI change
After any frontend change, validate it like a real user using Playwright:
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:3000")  # or your frontend URL from config.json
    page.wait_for_load_state("networkidle")
    # verify key elements are present
    page.screenshot(path="autoagent/e2e_screenshot.png")
    browser.close()
```
Run: `py autoagent/e2e_check.py`
**If E2E fails → fix before committing. Screenshots saved to autoagent/e2e_screenshot.png.**

### PHASE 5: Commit & Push
Only after ALL checks pass (including E2E):
```
git add -A
git commit -m "agent: <what changed> — <why it matters>"
git push origin main
```

### PHASE 6: Self-Reflect & Grow — MANDATORY, EVERY SESSION, NO EXCEPTIONS
This phase is not optional. It is the engine of compounding growth.

**Step A — Knowledge capture** (ALWAYS):
Append at least one concrete, specific lesson to `autoagent/knowledge.md`

**Step A2 — Skill library** (whenever you write something reusable):
Call `save_skill`. The skill library compounds: future sessions don't rewrite from scratch.

**Step B — Research queue** (whenever you noticed a gap):
Call `add_to_research_queue`. An agent that never queues research never grows.

**Step B2 — Technology research** (EVERY session):
Search for what top developers are doing RIGHT NOW that you are not.
Pick ONE thing that would genuinely improve the project or your own intelligence.

**Step C — Agent self-modification** (at least every 3rd session):
Ask: "What would make me meaningfully smarter or faster next session?"
- A missing tool? Add it to TOOLS + execute_tool.
- A weak context section? Improve build_context().
- A prompt gap? Sharpen SYSTEM_PROMPT.
- A repeated mistake? Add a guard or warning.

**Step D — Run health check** (ALWAYS before task_complete):
Call `run_health_check`. If score < 3, fix regressions before finishing.

**Step E — Fill in task_complete** with honest self-critique scores (1-3):
- research_depth: 3=searched before every change | 2=some research | 1=coded without researching
- code_quality: 3=all tests pass, clean code, no security issues | 2=tests pass, minor issues | 1=tests failing
- self_growth: 3=concrete lesson + post-mortem if needed + agent improved | 2=lesson written | 1=nothing written
- task_completion: 3=task fully done and pushed | 2=partial but committed | 1=nothing committed

**Step F — Update BACKLOG.md**:
Mark item done `[x]`. Add any new ideas. Re-prioritize based on business impact.

---

## Code Quality Standards (non-negotiable)
- **Security**: sanitize all inputs, never trust external data, no injection vulnerabilities
- **Error handling**: wrap I/O in try/except, log errors, continue gracefully
- **Async**: all I/O should be async where the framework supports it
- **Logging**: use proper logger not print() in production code
- **Tests**: every new function → at least one test
- **No hardcoded values**: use constants or config for URLs, timeouts, thresholds
- **Up to date**: always search for the current recommended approach before implementing

---

## Simplicity Criterion (from Karpathy autoresearch)
When evaluating whether to keep a change:
- Small improvement + ugly complexity = not worth it. Revert.
- Small improvement + code deletion = definitely keep.
- Equal performance + simpler code = keep. Simplification is a win.
- Big improvement + any complexity = keep with good documentation.

## Autonomous Operation (never ask for permission)
You run indefinitely. You do not stop to ask if you should continue.
If you run out of obvious ideas, think harder: re-read knowledge.md, review experiment_results.tsv,
try combining prior near-misses, read failing tests for clues.
The owner may be asleep. Work as if they are.

Be decisive. Research first. Build completely. Test rigorously. Commit only clean code. Grow every session."""


# ──────────────────────────────────────────────────────────────
# SESSION CONTEXT
# ──────────────────────────────────────────────────────────────

def build_context() -> str:
    parts = []

    # Project description — injected at runtime from PROJECT.md
    project_context = load_project_context()
    parts.append(f"## PROJECT CONTEXT\n{project_context}")

    # Active task tracker — resume this before anything else
    if CURRENT_TASK_FILE.exists() and CURRENT_TASK_FILE.stat().st_size > 0:
        parts.append(
            f"## RESUME THIS TASK FIRST — DO NOT START ANYTHING NEW\n"
            f"{CURRENT_TASK_FILE.read_text(encoding='utf-8')}\n\n"
            f"Pick the first unchecked remaining step and implement it. "
            f"Commit it. Update current_task via update_current_task tool. "
            f"Only start a new task when all remaining steps are done."
        )

    # Checkpoint from hard mid-session interrupt (budget hit)
    cp = load_checkpoint()
    if cp and not (CURRENT_TASK_FILE.exists() and CURRENT_TASK_FILE.stat().st_size > 0):
        parts.append(
            f"## CHECKPOINT — budget ran out mid-session on {cp['saved_at']}\n"
            f"Was working on: {cp['task']}\n"
            f"Progress: {cp['progress']}"
        )

    # Backlog (priorities) — auto-generate if missing or empty
    backlog_content = BACKLOG_FILE.read_text(encoding="utf-8").strip() if BACKLOG_FILE.exists() else ""
    if not backlog_content or len(backlog_content) < 50:
        parts.append(
            "## BACKLOG\n"
            "No backlog exists yet. Your FIRST task this session:\n"
            "1. Read PROJECT.md and NORTH_STAR.md carefully.\n"
            "2. Generate a smart 10-task backlog based on the goal and current project state.\n"
            "3. Write it to autoagent/BACKLOG.md in `- [ ] task` format.\n"
            "4. Pick the highest-leverage task and start it.\n"
            "Think like a co-founder: what 10 things will move the North Star metric fastest?"
        )
    else:
        parts.append(f"## BACKLOG (your priorities)\n{backlog_content}")

    # Accumulated knowledge from past sessions
    if KNOWLEDGE_FILE.exists():
        parts.append(f"## Knowledge Base (lessons learned from past sessions)\n{KNOWLEDGE_FILE.read_text(encoding='utf-8')}")

    # Recent activity log (last 3000 chars)
    if LOG_FILE.exists():
        content = LOG_FILE.read_text(encoding="utf-8")
        if len(content) > 50:
            parts.append(f"## Recent Activity (what was done — don't repeat)\n{content[-3000:]}")

    # Budget + financial efficiency
    spend     = get_today_spend()
    remaining = cfg["daily_limit_usd"] - spend
    m         = json.loads(GROWTH_FILE.read_text(encoding="utf-8")) if GROWTH_FILE.exists() else {}
    total_sessions = m.get("total_sessions", 1)
    avg_cost       = m.get("total_cost_usd", 0) / max(total_sessions, 1)
    current_model  = load_config().get("model", "claude-sonnet-4-6")
    parts.append(
        f"## Budget & Financial Intelligence\n"
        f"Today: ${spend:.4f} spent / ${remaining:.4f} remaining (limit ${cfg['daily_limit_usd']:.2f})\n"
        f"Avg cost/session: ${avg_cost:.4f} | Current model: {current_model}\n"
        f"Models: haiku ($1/MTok in, $5 out) | sonnet ($3/$15) | opus ($5/$25)\n"
        f"Tip: switch to haiku for research/reading sessions to stretch budget."
    )

    # Last session's recommended next priority + all-time growth stats
    if GROWTH_FILE.exists():
        m     = json.loads(GROWTH_FILE.read_text(encoding="utf-8"))
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

    # Experiment results log
    exp_tsv = AGENT_DIR / "experiment_results.tsv"
    if exp_tsv.exists():
        lines = exp_tsv.read_text(encoding="utf-8").strip().splitlines()
        if len(lines) > 1:
            recent = "\n".join(lines[-10:])
            parts.append(f"## Experiment History (last 10 — don't repeat failed hypotheses)\n{recent}")

    # Skill library index
    skills_index = SKILLS_DIR / "INDEX.md"
    if skills_index.exists():
        idx = skills_index.read_text(encoding="utf-8").strip()
        if len(idx) > 100:
            parts.append(f"## Skill Library (reusable patterns — use these before writing from scratch)\n{idx}")

    # Recent successful trajectories (Reflexion exemplar pattern)
    if TRAJECTORIES_FILE.exists():
        traj = TRAJECTORIES_FILE.read_text(encoding="utf-8")
        if len(traj) > 100:
            parts.append(f"## Recent Successful Approaches (learn from these — don't reinvent)\n{traj[-2500:]}")

    # Research queue
    if RESEARCH_QUEUE_FILE.exists():
        rq = RESEARCH_QUEUE_FILE.read_text(encoding="utf-8").strip()
        if rq and len(rq) > 60:
            parts.append(f"## Research Queue (knowledge gaps — tackle during self-growth sessions)\n{rq[-2000:]}")

    # Self-critique trend
    if GROWTH_FILE.exists():
        m2      = json.loads(GROWTH_FILE.read_text(encoding="utf-8"))
        history = m2.get("self_critique_history", [])
        if history:
            last3 = history[-3:]
            dims  = ["research_depth", "code_quality", "self_growth", "task_completion"]
            averages = {}
            for d in dims:
                vals = [h[d] for h in last3 if d in h]
                averages[d] = round(sum(vals)/len(vals), 1) if vals else "?"
            weak = [d for d, v in averages.items() if isinstance(v, float) and v < 2.5]
            critique_summary = "Last 3 sessions avg: " + " | ".join(f"{d}={v}" for d, v in averages.items())
            if weak:
                critique_summary += f"\nWEAK AREAS (avg < 2.5): {', '.join(weak)} — focus on improving these"
            parts.append(f"## Self-Critique Trend\n{critique_summary}")

    # Project health trend
    if HEALTH_LOG_FILE.exists():
        health_data = json.loads(HEALTH_LOG_FILE.read_text(encoding="utf-8"))
        if health_data:
            last  = health_data[-1]
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
# SESSION DIRECTIVES
# ──────────────────────────────────────────────────────────────

def _get_session_directive(session_num: int) -> str:
    """Returns the directive for this session number."""
    if session_num % 5 == 0:
        critique_diag = ""
        if GROWTH_FILE.exists():
            gm      = json.loads(GROWTH_FILE.read_text(encoding="utf-8"))
            history = gm.get("self_critique_history", [])
            if history:
                last5   = history[-5:]
                dims    = ["research_depth", "code_quality", "self_growth", "task_completion"]
                weakest = min(dims, key=lambda d: sum(h.get(d, 2) for h in last5) / max(len(last5), 1))
                critique_diag = f" Your weakest dimension over last 5 sessions: '{weakest}' — make this the focus."
        return (
            f"This is session #{session_num} — a SELF-GROWTH session.{critique_diag}\n\n"
            "Work through ALL of these in order:\n"
            "1. **Research queue**: Read autoagent/research_queue.md — tackle HIGH priority items first. "
            "For each: web_search → fetch top results → update knowledge.md → delete item from queue.\n"
            "2. **Anthropic updates**: Fetch https://docs.anthropic.com/en/docs/about-claude/models — "
            "check for new models, features, pricing. Update config.json + knowledge.md.\n"
            "3. **Financial audit**: Review growth_metrics.json spend. "
            "If avg session cost > $3, find cost reduction (caching, model switch, context trimming).\n"
            "4. **GitHub intelligence**: Search best practices for your stack — absorb 3+ concrete techniques.\n"
            "5. **Agent architecture**: Read autoagent/run.py fully. Find one thing to improve. Implement it.\n"
            "6. **Competitor intelligence**: Search for direct competitors in your product space — "
            "find gaps, update BACKLOG with ideas.\n\n"
            "The product gets better when the agent gets smarter. Every hour on self-growth is worth 3 hours on features."
        )

    # Rotate through specialist sessions
    specialist_cycle = ["engineer", "designer", "researcher", "qa", "engineer"]
    specialist       = specialist_cycle[session_num % len(specialist_cycle)]

    specialist_directives = {
        "engineer": (
            "**ENGINEER SESSION**\n"
            "Identity: You are a Senior Full-Stack Engineer.\n"
            "Mission: Ship the highest-value feature on the backlog. Clean code, tested, deployed.\n"
            "Critical rules: Research current best practices first. Write tests. Never commit broken code.\n"
            "Deliverables: Working feature, passing tests, committed and pushed.\n"
            "Success metric: Feature works end-to-end, no test regressions."
        ),
        "designer": (
            "**UX SPECIALIST SESSION**\n"
            "Identity: You are a Senior UI/UX Designer + Frontend Engineer.\n"
            "Mission: Make the app measurably more beautiful and easier to use.\n"
            "Critical rules: Mobile-first. Run build checks before AND after every change. WCAG AA contrast.\n"
            "Deliverables: Working UI component, polished styles, loading/empty/error states.\n"
            "Success metric: Feature works on mobile, build passes, looks better than yesterday."
        ),
        "researcher": (
            "**RESEARCH SESSION**\n"
            "Identity: You are a Research Scientist + Data Engineer.\n"
            "Mission: Discover new data sources, APIs, integrations, or capabilities for the product.\n"
            "Critical rules: Check ToS/robots.txt before scraping. Handle rate limits. Never crash on structure changes.\n"
            "Deliverables: New data pipeline or integration, integrated into the app, at least 1 test.\n"
            "Success metric: New source/integration returns data, all existing tests still pass."
        ),
        "qa": (
            "**QA SESSION**\n"
            "Identity: You are a Senior QA Engineer + Playwright specialist.\n"
            "Mission: Find and fix gaps in test coverage. Improve reliability.\n"
            "Critical rules: Write tests that actually find bugs. E2E tests for user-facing flows.\n"
            "Deliverables: New tests, updated e2e_check.py, improved coverage metrics.\n"
            "Success metric: More test coverage, no new test failures."
        ),
    }

    base = specialist_directives.get(specialist, specialist_directives["engineer"])
    return (
        f"{base}\n\n"
        "Pick ONE small, completable task (max 3-5 files). "
        "Implement completely, validate, commit, push, call task_complete. "
        "If a current_task.md exists — resume it first, specialist mode applies to next task after."
    )


# ──────────────────────────────────────────────────────────────
# BACKEND MODE SELECTION
# ──────────────────────────────────────────────────────────────

def choose_backend_mode() -> str:
    """Ask user to choose backend mode (cached after first choice)."""
    if BACKEND_MODE_FILE.exists():
        try:
            saved = json.loads(BACKEND_MODE_FILE.read_text(encoding="utf-8"))
            if saved.get("mode") in ("vscode", "api"):
                return saved["mode"]
        except Exception:
            pass

    # ── Check credential status ───────────────────────────────
    api_key      = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    cli_active   = os.environ.get("CLAUDE_CLI_ACTIVE", "").strip().lower() == "true"
    npm_bin      = os.path.join(os.environ.get("APPDATA", ""), "npm")
    claude_cmd   = os.path.join(npm_bin, "claude.cmd")
    cli_installed = os.path.exists(claude_cmd)

    api_status = "✅ key found" if api_key else "❌ not set  (add to autoagent/credentials.env)"
    cli_status = "✅ active"   if (cli_active and cli_installed) else (
                 "✅ installed (run: claude  to activate)" if cli_installed else
                 "❌ not found (run: npm install -g @anthropic-ai/claude-code)")

    print("\n" + "="*58)
    print("  AutoAgent — Choose your AI backend")
    print("="*58)
    print()
    print(f"  1) VS Code / Claude CLI  — FREE")
    print(f"     Status : {cli_status}")
    print(f"     Cost   : $0 — uses your Claude Pro subscription")
    print(f"     Limits : rate-limited per hour, auto-resumes")
    print()
    print(f"  2) Anthropic API         — pay per token")
    print(f"     Status : {api_status}")
    print(f"     Cost   : up to ${cfg['daily_limit_usd']:.0f}/day (set in config.json)")
    print(f"     Limits : none (runs as fast as possible)")
    print()
    print("  To set credentials: edit autoagent/credentials.env")
    print("  To switch later:    delete autoagent/backend_mode.json")
    print("="*58)

    while True:
        try:
            choice = input("  Enter 1 or 2 [default: 1]: ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "1"
        if choice in ("", "1", "vscode"):
            mode = "vscode"
            break
        elif choice in ("2", "api"):
            if not api_key:
                print("\n  ⚠ No ANTHROPIC_API_KEY found.")
                print("  Add it to autoagent/credentials.env then re-run.")
                print("  Or pick option 1 (free).\n")
                continue
            mode = "api"
            break
        print("  Enter 1 or 2")

    BACKEND_MODE_FILE.write_text(json.dumps({"mode": mode}, indent=2), encoding="utf-8")
    print(f"\n  Mode '{mode}' saved.\n")
    return mode


def _check_vscode_rate_limit() -> bool:
    """Returns True (and prints wait time) if still rate limited."""
    if not RATE_LIMIT_FILE.exists():
        return False
    try:
        data        = json.loads(RATE_LIMIT_FILE.read_text(encoding="utf-8"))
        retry_after = datetime.fromisoformat(data["retry_after"])
        now         = datetime.now()
        if now < retry_after:
            wait_secs = int((retry_after - now).total_seconds())
            mins      = wait_secs // 60
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
    from datetime import timedelta
    now      = datetime.now()
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
                if t <= now:
                    t += timedelta(days=1)
                retry_dt = t
                break
            except ValueError:
                pass

    if retry_dt is None:
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
    npm_bin    = os.path.join(os.environ.get("APPDATA", ""), "npm")
    claude_cmd = os.path.join(npm_bin, "claude.cmd")
    if not os.path.exists(claude_cmd):
        return "", f"ERROR: claude.cmd not found at {claude_cmd}. Run: npm i -g @anthropic-ai/claude-code"
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write(full_prompt)
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
        return "", f"TIMEOUT: claude CLI did not respond in {timeout}s"
    except Exception as e:
        return "", f"ERROR: {e}"
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except Exception:
                pass


# ──────────────────────────────────────────────────────────────
# NORTH STAR MULTI-AGENT ORCHESTRATION
# ──────────────────────────────────────────────────────────────

def _is_north_star_configured() -> bool:
    """Return True if NORTH_STAR.md exists and has been filled in by the user."""
    ns_path = AGENT_DIR / "NORTH_STAR.md"
    if not ns_path.exists():
        return False
    content = ns_path.read_text(encoding="utf-8")
    # Check that placeholder text has been replaced
    unfilled_markers = [
        "[e.g.,",
        "Goal: [",
        "Target: [",
        "Reason: [",
        "Command: [",
    ]
    return not any(marker in content for marker in unfilled_markers)


def run_north_star_session() -> bool:
    """
    Run the full multi-agent North Star session.

    Sequence:
      1. Orchestrator reads NORTH_STAR.md, measures metric, forms hypotheses,
         writes mission_brief.md, selects specialist agents.
      2. Each selected specialist runs in order, reading the brief and reporting.
      3. Orchestrator synthesizes all reports.
      4. If metric stagnant 3+ sessions, pivot mode triggers BACKLOG rewrite.

    Returns True if the North Star session ran (caller should skip single-agent session).
    Returns False if something went wrong (caller falls back to single-agent session).
    """
    import sys as _sys
    import importlib

    # Ensure agents/ is importable
    agents_dir = AGENT_DIR / "agents"
    agents_str = str(agents_dir)
    if agents_str not in _sys.path:
        _sys.path.insert(0, agents_str)

    # Ensure shared/reports/ exists
    (AGENT_DIR / "shared" / "reports").mkdir(parents=True, exist_ok=True)

    metrics     = json.loads(GROWTH_FILE.read_text(encoding="utf-8")) if GROWTH_FILE.exists() else {}
    session_num = metrics.get("total_sessions", 0) + 1

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"AutoAgent [North Star Multi-Agent Mode]  |  {ts}")
    print(f"Session #{session_num}")
    print('='*60)

    # ── Step 1: Orchestrator ──────────────────────────────────
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "orchestrator", agents_dir / "orchestrator.py"
        )
        orch_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(orch_mod)
    except Exception as e:
        print(f"  [NorthStar] Failed to load orchestrator: {e}")
        return False

    orch_result = orch_mod.run(session_num=session_num)
    if not orch_result.get("success"):
        print(f"  [NorthStar] Orchestrator failed — falling back to single-agent mode.")
        return False

    agents_selected = orch_result.get("agents_selected", ["engineer"])
    metric_now      = orch_result.get("metric_now", "unknown")
    top_hypothesis  = orch_result.get("top_hypothesis", "")

    print(f"  [NorthStar] Metric: {metric_now}")
    print(f"  [NorthStar] Activating: {', '.join(agents_selected)}")

    # ── Step 2: Run each specialist ───────────────────────────
    agent_results: dict[str, dict] = {}
    agent_module_map = {
        "engineer":   "engineer",
        "researcher": "researcher",
        "designer":   "designer",
        "strategist": "strategist",
        "qa":         "qa",
    }

    for agent_name in agents_selected:
        module_file = agent_module_map.get(agent_name)
        if not module_file:
            continue
        agent_path = agents_dir / f"{module_file}.py"
        if not agent_path.exists():
            print(f"  [NorthStar] WARNING: {agent_path} not found — skipping {agent_name}")
            continue
        try:
            spec = importlib.util.spec_from_file_location(agent_name, agent_path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.run()
            agent_results[agent_name] = result
        except Exception as e:
            print(f"  [NorthStar] {agent_name} raised exception: {e}")
            agent_results[agent_name] = {"success": False, "error": str(e)}

    # ── Step 3: Orchestrator synthesis ───────────────────────
    # Build a summary of all agent reports for the synthesis call
    reports_dir = AGENT_DIR / "shared" / "reports"
    report_texts = []
    for agent_name in agents_selected:
        report_path = reports_dir / f"{agent_name}.md"
        if report_path.exists():
            report_texts.append(
                f"=== {agent_name.upper()} REPORT ===\n"
                + report_path.read_text(encoding="utf-8")[-3000:]
            )

    all_reports = "\n\n".join(report_texts) if report_texts else "(no reports written)"

    # Read north_star history to check for stagnation
    ns_live_path = AGENT_DIR / "shared" / "north_star.md"
    ns_live      = ns_live_path.read_text(encoding="utf-8") if ns_live_path.exists() else ""

    # Count stagnant sessions: look for rows in measurement history where Delta = 0 or +0
    import re as _re
    delta_values = _re.findall(r'\|\s*[\d\-:T ]+\s*\|\s*[\d.]+\s*\|\s*([+\-]?[\d.]+)\s*\|', ns_live)
    stagnant_sessions = sum(1 for d in delta_values[-3:] if d.strip() in ("0", "+0", "-0", "0.0"))
    pivot_triggered   = stagnant_sessions >= 3

    if pivot_triggered:
        print(f"  [NorthStar] PIVOT MODE: metric stagnant for {stagnant_sessions} sessions — triggering backlog rewrite")

    synthesis_prompt = f"""You are the ORCHESTRATOR completing your synthesis for session #{session_num}.

ALL SPECIALIST REPORTS:
{all_reports}

NORTH STAR LIVE STATUS:
{ns_live or "(not yet updated)"}

METRIC THIS SESSION: {metric_now}
TOP HYPOTHESIS THIS SESSION: {top_hypothesis}
PIVOT MODE: {"YES — metric stagnant 3+ sessions" if pivot_triggered else "NO"}

---

## YOUR SYNTHESIS TASKS

### Task 1: Update shared/north_star.md
Add a new row to the Measurement History table with today's reading.
Update the Current Bottleneck Diagnosis section with your assessment.
Update Active Hypothesis with what you'll bet on next session.
Write the file to: {str(ns_live_path).replace(chr(92), "/")}

### Task 2: Update shared/hypotheses.md
Mark any hypotheses from this session as CONFIRMED or REJECTED based on the reports.
Add new hypotheses surfaced by specialists.
Write the file to: {str(AGENT_DIR / "shared" / "hypotheses.md").replace(chr(92), "/")}

### Task 3: Update shared/decisions.md
If any significant strategic decision was made this session, log it.
Write to: {str(AGENT_DIR / "shared" / "decisions.md").replace(chr(92), "/")}

### Task 4: Update shared/debates.md
If any specialists disagreed, log the debate and rule on it with evidence.
Write to: {str(AGENT_DIR / "shared" / "debates.md").replace(chr(92), "/")}

{"### Task 5: PIVOT — Rewrite BACKLOG.md" + chr(10) + "The metric has not moved in 3+ sessions. The current strategy is not working." + chr(10) + "Completely rewrite " + str(AGENT_DIR / "BACKLOG.md").replace(chr(92), "/") + " with a fundamentally different approach." + chr(10) + "Think: what is the ONE thing that would actually move this metric? Bet everything on it." if pivot_triggered else ""}

---

END WITH THIS EXACT BLOCK:
SYNTHESIS_DONE: <one sentence summary of session outcome>
METRIC_MOVED: yes | no | unknown
PIVOT_EXECUTED: {"yes" if pivot_triggered else "no"}
NEXT_SESSION_PRIORITY: <what the team should focus on next>
"""

    print("  [NorthStar] Running synthesis...")
    npm_bin    = os.path.join(os.environ.get("APPDATA", ""), "npm")
    claude_cmd = os.path.join(npm_bin, "claude.cmd")
    synth_out  = ""
    synth_err  = ""

    if os.path.exists(claude_cmd):
        import tempfile as _tmpmod
        tmp_path = None
        try:
            with _tmpmod.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as f:
                f.write(synthesis_prompt)
                tmp_path = f.name
            env = os.environ.copy()
            env.pop("ANTHROPIC_API_KEY", None)
            env.pop("ANTHROPIC_API_KEY_OVERRIDE", None)
            cmd = f'type "{tmp_path}" | "{claude_cmd}" --print --dangerously-skip-permissions'
            res = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=900, encoding="utf-8", errors="replace", cwd=str(ROOT), env=env
            )
            synth_out = res.stdout.strip()
            synth_err = res.stderr.strip()
        except Exception as e:
            synth_err = str(e)
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    # Parse synthesis output
    synth_done_m  = _re.search(r"SYNTHESIS_DONE:\s*(.+)",        synth_out)
    metric_move_m = _re.search(r"METRIC_MOVED:\s*(yes|no|unknown)", synth_out, _re.IGNORECASE)
    next_pri_m    = _re.search(r"NEXT_SESSION_PRIORITY:\s*(.+)", synth_out)

    synth_summary = synth_done_m.group(1).strip()  if synth_done_m  else f"Session {session_num} complete"
    metric_moved  = metric_move_m.group(1).lower() if metric_move_m else "unknown"
    next_priority = next_pri_m.group(1).strip()    if next_pri_m    else ""

    # Save synthesis report
    ts_short = datetime.now().strftime("%Y-%m-%d %H:%M")
    synthesis_report = (
        f"# Synthesis Report — {ts_short}\n\n"
        f"**Session:** #{session_num}\n"
        f"**Metric:** {metric_now}\n"
        f"**Metric moved:** {metric_moved}\n"
        f"**Pivot executed:** {'yes' if pivot_triggered else 'no'}\n"
        f"**Next priority:** {next_priority}\n\n"
        f"## Agents Run\n"
        + "\n".join(f"- {a}" for a in agents_selected)
        + f"\n\n## Full Synthesis\n\n{synth_out}\n"
    )
    (reports_dir / "synthesis.md").write_text(synthesis_report, encoding="utf-8")

    print(f"\n  [NorthStar] Session complete: {synth_summary}")
    print(f"  [NorthStar] Metric moved: {metric_moved}")
    if next_priority:
        print(f"  [NorthStar] Next: {next_priority[:80]}")

    # ── Update growth metrics ─────────────────────────────────
    m_data = json.loads(GROWTH_FILE.read_text(encoding="utf-8")) if GROWTH_FILE.exists() else {
        "total_sessions": 0, "total_cost_usd": 0.0,
        "categories": {}, "self_improvements": [], "next_session_hints": [],
        "skills_acquired": 0
    }
    m_data["total_sessions"] = m_data.get("total_sessions", 0) + 1
    m_data["categories"]["north_star"] = m_data["categories"].get("north_star", 0) + 1
    if next_priority:
        hints = m_data.get("next_session_hints", [])
        hints.append(next_priority)
        m_data["next_session_hints"] = hints[-5:]  # keep last 5
    GROWTH_FILE.write_text(json.dumps(m_data, indent=2), encoding="utf-8")

    # ── Log to activity log ───────────────────────────────────
    log_entry = (
        f"\n---\n## {ts_short} — NORTH_STAR [session #{session_num}]\n"
        f"**{synth_summary}**\n"
        f"Metric: {metric_now} | Moved: {metric_moved} | "
        f"Agents: {', '.join(agents_selected)}\n"
        + (f"Pivot: YES — backlog rewritten\n" if pivot_triggered else "")
        + f"Cost: $0.00 (VS Code mode)\n"
    )
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)

    return True


# ──────────────────────────────────────────────────────────────
# VS CODE SESSION
# ──────────────────────────────────────────────────────────────

def run_vscode_session():
    """Run a session using Claude Code CLI (no API cost, rate-limit aware)."""
    if _check_vscode_rate_limit():
        return

    # ── North Star multi-agent mode (if configured) ───────────
    if _is_north_star_configured():
        success = run_north_star_session()
        if success:
            clear_checkpoint()
            finalize_report()
            sync_state(f"after north star session {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            return
        # If North Star session failed, fall through to single-agent mode
        print("  [NorthStar] Falling back to single-agent mode.")


    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"AutoAgent [VS Code Mode]  |  {ts}")
    print('='*60)

    context = build_context()
    metrics = json.loads(GROWTH_FILE.read_text(encoding="utf-8")) if GROWTH_FILE.exists() else {}
    session_num       = metrics.get("total_sessions", 0) + 1
    session_directive = _get_session_directive(session_num)

    # Strip API budget section — irrelevant in VS Code mode
    import re as _re
    context_clean = _re.sub(
        r'## Budget & Financial Intelligence.*?(?=\n## |\Z)', '',
        context, flags=_re.DOTALL
    ).strip()

    task_prompt = f"""You are working autonomously on a software project.
Project root: {ROOT}

NOTE: You are running via VS Code subscription — there are NO API credits or budget limits. Ignore any dollar amounts or budget references in the context below.

{SYSTEM_PROMPT}

=== SESSION CONTEXT ===
{context_clean}

=== YOUR MISSION THIS SESSION ===
{session_directive}

{_git_rules()}

=== EXECUTION RULES ===
- Read autoagent/PROJECT.md to understand the project and its tech stack commands
- Always use project-specific commands from autoagent/knowledge.md for tests and import checks
- After every backend change: run import check + tests before committing. Never commit broken code.

=== TOOL EQUIVALENTS (use these instead of Python tool calls) ===

**update_current_task** — track progress so next session resumes here:
Write autoagent/current_task.md with:
  # Current Task — <name>
  ## Completed Steps
  - [x] step done
  ## Remaining Steps
  - [ ] next step
  ## Last Commit
  `commit message`

**run_experiment** — safe accept/reject gate (Karpathy autoresearch pattern):
  1. Run your metric command → record baseline number
  2. Make your changes
  3. Run metric again → compare
  4. If improved: git add -A && git commit -m "exp: <hypothesis> [baseline→new]"
  5. If worse: git stash && git stash drop  (revert all changes)
  6. Append to autoagent/experiment_results.tsv: commit\\tmetric_before\\tmetric_after\\tdelta\\tkeep/discard\\thypothesis

**run_health_check** — always run before finishing:
  Use commands from autoagent/knowledge.md for this project's test runner.
  If any test fails → fix it before writing DONE block.

**save_skill** — save reusable patterns:
  Write autoagent/skills/<snake_case_name>.py with the pattern.
  Append to autoagent/skills/INDEX.md: - **name** — description (autoagent/skills/name.py)

**write_post_mortem** — learn from failures:
  Append to autoagent/knowledge.md:
  ### Post-Mortem — <date>
  **What failed:** ...
  **Root cause:** ...
  **Fix applied:** ...
  **Prevention rule:** ...

**add_to_research_queue** — queue knowledge gaps:
  Append to autoagent/research_queue.md:
  - [PRIORITY] **topic** — Added <date>
    _Why: reason_

=== MANDATORY SESSION WORKFLOW ===
PHASE 1 — Research first: web_search before writing any code.
PHASE 2 — Read & plan: read every file you will touch.
PHASE 2.5 — Experiment design: use run_experiment gate for metric-affecting changes.
PHASE 3 — Implement: update current_task first. Commit after each logical step.
PHASE 3.5 — Dev-QA retry: if health_check fails, fix it. Max 3 attempts.
PHASE 4 — Validate: run tests + build check before every commit.
PHASE 4.5 — E2E: run py autoagent/e2e_check.py after any UI change.
PHASE 5 — Commit & push: git add -A && git commit && git push.
PHASE 6 — Self-reflect & grow (MANDATORY):
  A. Append a lesson to autoagent/knowledge.md
  B. save_skill for any reusable pattern
  B2. web_search for 2 best-practice topics in your stack. Add ONE finding to research_queue.md.
  C. add_to_research_queue for any knowledge gap noticed
  D. Run health check — fix regressions
  E. Update autoagent/BACKLOG.md — mark item [x], add new ideas
  F. Update or delete autoagent/current_task.md
  G. Agent self-upgrade: find one thing to improve in autoagent/run.py SYSTEM_PROMPT or e2e_check.py

=== END YOUR RESPONSE WITH THIS EXACT BLOCK ===
DONE: <one sentence: what was accomplished>
IMPACT: <why this matters to users or revenue>
FILES: <comma-separated files changed>
"""

    print(f"  Calling claude CLI — running autonomously (may take 5-20 min)...")
    stdout, stderr = _call_vscode_claude(task_prompt, timeout=1200)
    combined       = stdout + "\n" + stderr
    combined_lower = combined.lower()

    ts_short = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Detect rate limit
    rate_limit_keywords = ["rate limit", "usage limit", "limit reached", "try again", "reset at", "quota exceeded"]
    if any(kw in combined_lower for kw in rate_limit_keywords):
        _save_vscode_rate_limit(combined)
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

    import re as _re
    summary_m = _re.search(r'DONE:\s*(.+)',   stdout)
    impact_m  = _re.search(r'IMPACT:\s*(.+)', stdout)
    files_m   = _re.search(r'FILES:\s*(.+)',  stdout)

    summary = summary_m.group(1).strip() if summary_m else f"VS Code session {ts_short}"
    impact  = impact_m.group(1).strip()  if impact_m  else ""
    files   = [f.strip() for f in files_m.group(1).split(",")] if files_m else []

    print(f"\nDone: {summary}")

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

    m_data = json.loads(GROWTH_FILE.read_text(encoding="utf-8")) if GROWTH_FILE.exists() else {
        "total_sessions": 0, "total_cost_usd": 0.0,
        "categories": {}, "self_improvements": [], "next_session_hints": [],
        "skills_acquired": 0
    }
    m_data["total_sessions"] += 1
    m_data["categories"]["feature"] = m_data["categories"].get("feature", 0) + 1
    GROWTH_FILE.write_text(json.dumps(m_data, indent=2), encoding="utf-8")

    clear_checkpoint()
    finalize_report()
    sync_state(f"after vscode session {ts_short}")


def sync_state(label: str = "state"):
    """
    Commit agent state files to the autoagent repo (never the project repo).
    Project code changes are handled by the agent itself during sessions.
    """
    g      = cfg.get("git", {})
    aa     = g.get("autoagent", {})
    branch = aa.get("branch", "main")
    prefix = aa.get("commit_prefix", "meta")
    enabled = aa.get("_enabled", False)

    # Stage only autoagent/ state files
    stage_cmd = (
        "git add autoagent/activity_log.md autoagent/knowledge.md autoagent/BACKLOG.md "
        "autoagent/growth_metrics.json autoagent/daily_budget.json autoagent/checkpoint.json "
        "autoagent/current_task.md autoagent/api_requests.md autoagent/reports/ "
        "autoagent/shared/ autoagent/meta/findings.md autoagent/meta/backlog.md 2>nul"
    )
    parts = [stage_cmd, f'git diff --cached --quiet || git commit -m "{prefix}: sync state — {label}"']
    if enabled:
        parts.append(f"git push origin {branch}")
    execute_tool("run_command", {"command": " && ".join(parts), "timeout": 30})


# ──────────────────────────────────────────────────────────────
# API SESSION
# ──────────────────────────────────────────────────────────────

def run_session():
    global client
    if client is None:
        client = anthropic.Anthropic()
    cfg_live = load_config()
    ts       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Pull latest state from remote before starting (respects git policy)
    g = cfg.get("git", {})
    if g.get("auto_pull", True):
        remote = g.get("remote", "origin")
        branch = g.get("branch", "main")
        execute_tool("run_command", {
            "command": f"git pull {remote} {branch} --rebase 2>&1 | tail -3",
            "timeout": 30
        })

    spend = get_today_spend()
    limit = cfg_live["daily_limit_usd"]

    print(f"\n{'='*60}")
    print(f"AutoAgent  |  {ts}")
    print(f"Budget: ${spend:.4f} spent  |  ${limit - spend:.4f} remaining")
    print('='*60)

    if spend >= limit:
        print("Daily budget exhausted. Will resume tomorrow.")
        append_to_report(f"\n_Budget exhausted at {datetime.now().strftime('%H:%M')}. Resuming tomorrow._\n")
        sync_state("budget exhausted")
        return

    context     = build_context()
    metrics     = json.loads(GROWTH_FILE.read_text(encoding="utf-8")) if GROWTH_FILE.exists() else {}
    session_num = metrics.get("total_sessions", 0) + 1
    session_directive = _get_session_directive(session_num)
    messages    = [{
        "role": "user",
        "content": f"{context}\n\n---\n\n{session_directive}"
    }]

    total_in  = 0
    total_out = 0
    task_result = None
    model     = cfg_live["model"]
    max_turns = cfg_live["session_max_turns"]

    for turn in range(max_turns):
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

        session_cost = total_in * cfg_live["input_cost_per_token"] + total_out * cfg_live["output_cost_per_token"]

        # Circuit breaker: if burn rate at turn 15 projects > 70% of daily budget, warn the agent
        if turn == 15 and model != "claude-haiku-4-5-20251001":
            projected_total  = session_cost * (max_turns / 15)
            budget_fraction  = projected_total / limit
            if budget_fraction > 0.7:
                print(f"  Circuit breaker: projected ${projected_total:.2f} > 70% of ${limit:.2f} budget")
                circuit_msg = (
                    f"CIRCUIT BREAKER ALERT: At turn 15 you've spent ${session_cost:.4f}. "
                    f"Projected session cost: ${projected_total:.2f} (>{budget_fraction*100:.0f}% of ${limit:.2f} daily budget). "
                    f"Switch to simpler remaining steps or call optimize_costs to use haiku."
                )
                messages.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": "circuit_breaker", "content": circuit_msg}
                ]})

        if spend + session_cost > limit:
            print("Budget limit hit mid-session. Saving checkpoint...")
            last_tool = next(
                (b.name for b in reversed(response.content) if b.type == "tool_use"),
                "unknown"
            )
            save_checkpoint(
                task_description="Mid-session when budget ran out — check backlog for active item",
                progress=f"Was executing tool '{last_tool}' at turn {turn+1}."
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
            done         = False

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

            if not done and turn >= max_turns - 8:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": "turn_warning",
                    "content": f"WARNING: Only {max_turns - turn - 1} turns remaining. Commit what you have and call task_complete now."
                })

            messages.append({"role": "user", "content": tool_results})
            if done:
                break

    cost      = record_spend(total_in, total_out)
    new_total = get_today_spend()
    print(f"\nSession: ${cost:.4f}  |  Today total: ${new_total:.4f}")

    ts_short = datetime.now().strftime("%Y-%m-%d %H:%M")
    if task_result:
        summary   = task_result.get("summary", "Improvement made")
        category  = task_result.get("category", "feature")
        impact    = task_result.get("impact", "")
        files     = task_result.get("files_changed", [])
        self_impr = task_result.get("self_improvement", "")
        next_hint = task_result.get("next_session_hint", "")
        task_name_for_traj = task_result.get("task_name", summary[:60])

        log_entry = f"\n---\n## {ts_short} — {category.upper().replace('_',' ')}\n**{summary}**\n"
        if impact:    log_entry += f"Impact: {impact}\n"
        if files:     log_entry += f"Files: {', '.join(files)}\n"
        if self_impr: log_entry += f"Self-improvement: {self_impr}\n"
        if next_hint: log_entry += f"Next session: {next_hint}\n"
        log_entry += f"Cost: ${cost:.4f}\n"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)

        report_section = f"\n## {ts_short} — {category.upper().replace('_',' ')}\n**{summary}**\n"
        if impact:    report_section += f"> {impact}\n"
        if files:     report_section += f"Files: `{'`, `'.join(files)}`\n"
        if self_impr: report_section += f"Agent improved itself: {self_impr}\n"
        if next_hint: report_section += f"Next priority: _{next_hint}_\n"
        report_section += f"Cost: ${cost:.4f}\n"
        append_to_report(report_section)

        metrics = json.loads(GROWTH_FILE.read_text(encoding="utf-8")) if GROWTH_FILE.exists() else {
            "total_sessions": 0, "total_cost_usd": 0.0,
            "categories": {}, "self_improvements": [], "next_session_hints": [],
            "skills_acquired": 0
        }
        self_critique = task_result.get("self_critique", {})

        metrics["total_sessions"]  += 1
        metrics["total_cost_usd"]   = round(metrics.get("total_cost_usd", 0.0) + cost, 6)
        metrics["categories"][category] = metrics["categories"].get(category, 0) + 1
        if self_impr:
            metrics["self_improvements"].append({"ts": ts_short, "what": self_impr})
        if next_hint:
            metrics["next_session_hints"] = ([{"ts": ts_short, "hint": next_hint}]
                                             + metrics.get("next_session_hints", []))[:5]
        if self_critique:
            if "self_critique_history" not in metrics:
                metrics["self_critique_history"] = []
            metrics["self_critique_history"].append({"ts": ts_short, **self_critique})
            metrics["self_critique_history"] = metrics["self_critique_history"][-10:]
        GROWTH_FILE.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

        # Auto-store trajectory (Reflexion/SAGE pattern)
        traj_entry = (
            f"\n---\n## {ts_short} — {category}\n"
            f"**Task:** {task_name_for_traj}\n"
            f"**Approach:** {summary}\n"
            f"**Why it worked:** {impact}\n"
        )
        with open(TRAJECTORIES_FILE, "a", encoding="utf-8") as traj_f:
            traj_f.write(traj_entry)
        if TRAJECTORIES_FILE.exists():
            lines = TRAJECTORIES_FILE.read_text(encoding="utf-8").split("\n---\n")
            if len(lines) > 30:
                TRAJECTORIES_FILE.write_text("\n---\n".join(lines[-25:]), encoding="utf-8")

        clear_checkpoint()
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
        print(f"  Total sessions:  {m.get('total_sessions', 0)}")
        print(f"  Total API cost:  ${m.get('total_cost_usd', 0):.4f}")
        print(f"  Skills saved:    {m.get('skills_acquired', 0)}")
        print(f"  By category:     {m.get('categories', {})}")
        si = m.get("self_improvements", [])
        if si:
            print(f"  Last self-improvement: {si[-1]['what']}")
        hints = m.get("next_session_hints", [])
        if hints:
            print(f"  Next priority: {hints[0]['hint']}")

    report = get_report_file()
    if report.exists():
        print(f"\nToday's report:")
        print(report.read_text(encoding="utf-8")[-2000:])

    if API_REQUESTS_FILE.exists():
        content   = API_REQUESTS_FILE.read_text(encoding="utf-8")
        unchecked = [l for l in content.splitlines() if l.startswith("## [ ]")]
        if unchecked:
            print(f"\nAPI keys needed ({len(unchecked)}):")
            for u in unchecked:
                print(f"  {u}")


if __name__ == "__main__":
    if "--status" in sys.argv:
        show_status()
        sys.exit(0)

    once        = "--once"  in sys.argv
    solo        = "--solo"  in sys.argv   # main agent only, no meta
    tasks_limit = None

    if "--tasks" in sys.argv:
        idx = sys.argv.index("--tasks")
        try:
            tasks_limit = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            print("Usage: py autoagent/run.py --tasks 3")
            sys.exit(1)
    if tasks_limit:
        once = False

    # ── Default mode: launch meta-agent in background automatically ───────
    # Unless --solo is passed, the meta-agent runs in a separate process
    # so both agents work in parallel without any extra commands from the user.
    if not solo and not once:
        meta_script = AGENT_DIR / "meta" / "run.py"
        if meta_script.exists():
            try:
                meta_args = [sys.executable, "-X", "utf8", str(meta_script)]
                if tasks_limit:
                    meta_args += ["--tasks", str(tasks_limit)]
                meta_proc = subprocess.Popen(
                    meta_args,
                    cwd=str(ROOT),
                    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
                )
                print(f"  [AutoAgent] Meta-agent started (PID {meta_proc.pid}) — improving the brain in parallel.")
            except Exception as e:
                print(f"  [AutoAgent] Meta-agent could not start: {e} — continuing without it.")

    backend_mode = choose_backend_mode()

    def _vscode_sleep_or_continue():
        """Sleep between VS Code sessions. Returns True to retry immediately (rate limit)."""
        from datetime import timedelta
        if RATE_LIMIT_FILE.exists():
            try:
                data        = json.loads(RATE_LIMIT_FILE.read_text(encoding="utf-8"))
                retry_after = datetime.fromisoformat(data["retry_after"])
                now         = datetime.now()
                sleep_secs  = max(int((retry_after - now).total_seconds()) + 90, 90)
                wake        = retry_after.strftime("%H:%M:%S")
                mins        = sleep_secs // 60
                print(f"\n  Sleeping until {wake} ({mins}m {sleep_secs % 60}s)...")
                for remaining in range(sleep_secs, 0, -60):
                    m = remaining // 60
                    print(f"  ... {m}m remaining", end="\r", flush=True)
                    time.sleep(min(60, remaining))
                print(f"\n  Woke up at {datetime.now().strftime('%H:%M:%S')} — retrying session...")
                RATE_LIMIT_FILE.unlink(missing_ok=True)
                return True
            except Exception:
                print("\n  Rate limit file unreadable — sleeping 1 hour...")
                time.sleep(3600)
                RATE_LIMIT_FILE.unlink(missing_ok=True)
                return True
        elif CURRENT_TASK_FILE.exists() and CURRENT_TASK_FILE.stat().st_size > 0:
            print(f"\nUnfinished task detected. Resuming in 30 minutes...")
            time.sleep(30 * 60)
        else:
            print(f"\nSleeping {interval_h}h until next session...")
            time.sleep(interval_h * 3600)
        return False

    if backend_mode == "vscode":
        print("AutoAgent [VS Code Mode — no API cost]")
        print(f"Project: {ROOT.name} | Interval: {interval_h}h")

        if once:
            run_vscode_session()
        elif tasks_limit:
            completed = 0
            print(f"\nRunning until {tasks_limit} task(s) complete...\n")
            while completed < tasks_limit:
                try:
                    run_vscode_session()
                    if not RATE_LIMIT_FILE.exists():
                        completed += 1
                        remaining  = tasks_limit - completed
                        print(f"\n  [{completed}/{tasks_limit}] tasks done."
                              f"{' ' + str(remaining) + ' remaining.' if remaining else ' All done — exiting.'}", flush=True)
                except KeyboardInterrupt:
                    print("\nStopped.")
                    break
                except Exception as e:
                    print(f"Session crashed: {e}")
                if completed < tasks_limit:
                    retry = _vscode_sleep_or_continue()
                    if retry:
                        continue
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
                if _vscode_sleep_or_continue():
                    continue

    else:
        print(f"AutoAgent [API Mode] | Model: {cfg['model']} | Budget: ${cfg['daily_limit_usd']}/day")

        if once:
            run_session()
        elif tasks_limit:
            completed = 0
            print(f"\nRunning until {tasks_limit} task(s) complete...\n")
            while completed < tasks_limit:
                try:
                    run_session()
                    completed += 1
                    remaining  = tasks_limit - completed
                    print(f"\n  [{completed}/{tasks_limit}] tasks done."
                          f"{' ' + str(remaining) + ' remaining.' if remaining else ' All done — exiting.'}", flush=True)
                except KeyboardInterrupt:
                    print("\nStopped.")
                    break
                except Exception as e:
                    print(f"Session crashed: {e}")
                if completed < tasks_limit:
                    print(f"\nSleeping {interval_h}h until next session...")
                    time.sleep(interval_h * 3600)
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
                print(f"\nSleeping {interval_h}h until next session...")
                time.sleep(interval_h * 3600)
