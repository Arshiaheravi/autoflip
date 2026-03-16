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

# Load API key from backend/.env
load_dotenv(ROOT / "backend" / ".env")

# ─────────────────────────── Config ───────────────────────────
def load_config() -> dict:
    defaults = {
        "model": "claude-sonnet-4-6",
        "daily_limit_usd": 10.0,
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
client = anthropic.Anthropic()

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
        "name": "task_complete",
        "description": (
            "End the session. Call this ONLY after: (1) feature committed and pushed, "
            "(2) knowledge.md updated with at least one lesson learned, "
            "(3) agent/run.py improved if you spotted anything to make better. "
            "These three things are non-negotiable every single session."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
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

        elif name == "update_backlog":
            BACKLOG_FILE.write_text(inputs["content"], encoding="utf-8")
            return "Backlog updated."

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

SYSTEM_PROMPT = """You are the **complete autonomous product team** for AutoFlip. You simultaneously hold all of these roles — and you are exceptional at every one:

- **Senior Full-Stack Engineer** — clean async Python, React 19, FastAPI, MongoDB, security-first, test-driven
- **Senior UI/UX Designer** — beautiful interfaces, Tailwind + shadcn/ui, mobile-first, accessibility, conversion-optimized flows
- **Senior Growth Marketer** — SaaS copywriting, landing page optimization, SEO, retention, pricing strategy
- **DevOps Engineer** — git discipline, no broken commits, dependency management, performance profiling
- **Product Manager** — prioritizes ruthlessly by user value and revenue impact

You work 24/7 with **zero human interaction**. The owner's only job is to paste API keys when you request them. You handle everything else. Your only goal: **be measurably better than yesterday in every dimension**.

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

### PHASE 3: Implement
- Write clean, async, secure, well-structured code
- Follow existing patterns (async/await throughout, logger not print, type hints)
- Every new backend function → add a test in backend/tests/
- No half-done work. If you start it, finish it completely.

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

For frontend changes, check for obvious syntax errors by reading the file back.

### PHASE 5: Commit & Push
Only after ALL checks pass:
```
git add -A
git commit -m "agent: <what changed> — <why it matters>"
git push origin main
```
Commit messages must explain the WHY, not just the what.

### PHASE 6: Self-Reflect & Grow — MANDATORY, EVERY SESSION, NO EXCEPTIONS
This phase is not optional. It is the engine of compounding growth.

**Step A — Update knowledge.md** (ALWAYS):
Append at least one concrete lesson to `agent/knowledge.md`. Examples:
- "BeautifulSoup fails on this site because it uses JS rendering — need httpx + regex fallback"
- "Tailwind `gap-4` on flex containers doesn't work in older Safari — use `space-x-4` instead"
- "IAA Canada search requires a session cookie from the homepage first"

**Step B — Improve agent/run.py** (at least every 3rd session, check growth_metrics.json session count):
Read agent/run.py and look for at least ONE of:
- A tool that could be more useful (better description, new parameter, new tool entirely)
- A section of the system prompt that's missing context or could be sharper
- A flaw in build_context() — missing info that would help decision-making
- A better session strategy based on what you just experienced
Make the change. The agent running next session should be smarter than you are right now.

**Step C — Fill in task_complete** with:
- `self_improvement`: exactly what you improved about the agent itself
- `next_session_hint`: what the next session should do and why (this is read at start of next session)

**Step D — Update BACKLOG.md**:
Mark the item done `[x]`, add any new discoveries, re-prioritize if needed.

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

Be decisive. Research first. Build completely. Test rigorously. Commit only clean code. Grow every session."""


# ──────────────────────────────────────────────────────────────
# SESSION CONTEXT
# ──────────────────────────────────────────────────────────────

def build_context() -> str:
    parts = []

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

    # Budget
    spend = get_today_spend()
    remaining = cfg["daily_limit_usd"] - spend
    parts.append(f"## Budget\nSpent today: ${spend:.4f} / ${cfg['daily_limit_usd']:.2f}  |  Remaining: ${remaining:.4f}")

    # Last session's recommended next priority + all-time growth stats
    if GROWTH_FILE.exists():
        m = json.loads(GROWTH_FILE.read_text(encoding="utf-8"))
        hints = m.get("next_session_hints", [])
        total = m.get("total_sessions", 0)
        cats  = m.get("categories", {})
        last_self = m.get("self_improvements", [{}])[-1].get("what", "none yet")
        growth_summary = (
            f"Total sessions: {total} | Categories: {cats}\n"
            f"Last self-improvement: {last_self}\n"
        )
        if hints:
            growth_summary += f"PRIORITY FROM LAST SESSION: {hints[0]['hint']}"
        parts.append(f"## Growth Metrics & Next Priority\n{growth_summary}")

    # Recent git commits
    git_log = execute_tool("run_command", {"command": "git log --oneline -12"})
    parts.append(f"## Recent Git Commits\n{git_log}")

    return "\n\n---\n\n".join(parts)


# ──────────────────────────────────────────────────────────────
# MAIN SESSION
# ──────────────────────────────────────────────────────────────

def run_session():
    cfg_live = load_config()  # reload in case agent updated config
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    spend = get_today_spend()
    limit = cfg_live["daily_limit_usd"]

    print(f"\n{'='*60}")
    print(f"AutoFlip Agent  |  {ts}")
    print(f"Budget: ${spend:.4f} spent  |  ${limit - spend:.4f} remaining")
    print('='*60)

    if spend >= limit:
        print("Daily budget exhausted. Will resume tomorrow.")
        append_to_report(f"\n_Budget exhausted at {datetime.now().strftime('%H:%M')}. Resuming tomorrow._\n")
        return

    context = build_context()
    messages = [{
        "role": "user",
        "content": (
            f"{context}\n\n"
            "---\n\n"
            "Choose the highest-impact item from the backlog (or a critical bug/improvement you notice), "
            "implement it completely, test it, commit it, and call task_complete."
        )
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
        if spend + session_cost > limit:
            print("Budget limit hit mid-session. Stopping.")
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
        metrics["total_sessions"] += 1
        metrics["total_cost_usd"] = round(metrics["total_cost_usd"] + cost, 6)
        metrics["categories"][category] = metrics["categories"].get(category, 0) + 1
        if self_impr:
            metrics["self_improvements"].append({"ts": ts_short, "what": self_impr})
        if next_hint:
            # Keep only last 5 hints
            metrics["next_session_hints"] = ([{"ts": ts_short, "hint": next_hint}]
                                              + metrics["next_session_hints"])[:5]
        GROWTH_FILE.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

        print(f"\nDone: {summary}")
        if self_impr:
            print(f"Self-improved: {self_impr}")
    else:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n---\n## {ts_short} — INCOMPLETE\nSession ended without task_complete. Cost: ${cost:.4f}\n")
        append_to_report(f"\n## {ts_short} — INCOMPLETE\nSession cost: ${cost:.4f}\n")

    finalize_report()


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
            print(f"  Last self-improvement: {m['self_improvements'][-1]['what']}")
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

    print("AutoFlip Autonomous Agent")
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
            print(f"\nSleeping {interval_h}h until next session...")
            time.sleep(interval_h * 3600)
