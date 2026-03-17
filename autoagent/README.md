# AutoAgent

A fully autonomous, self-growing AI agent that works for **any software project**.

Drop it into your repo, fill in `PROJECT.md`, and it runs forever — building features, writing tests, researching best practices, improving itself, and growing a skill library across every session.

---

## Quick Start

```bash
# 1. Install dependencies (once)
py autoagent/setup.py

# 2. Describe your project
# Edit autoagent/PROJECT.md

# 3. Configure (optional)
# Edit autoagent/config.json

# 4. Run
py -X utf8 autoagent/run.py
```

---

## Files You Fill In

| File | Purpose |
|---|---|
| `PROJECT.md` | Describe your project, stack, goals. **Required.** |
| `config.json` | Model choice, budget, interval, URLs. |
| `BACKLOG.md` | Seed with initial tasks (optional — agent discovers its own). |
| `knowledge.md` | Pre-seed with your project's gotchas (optional). |

---

## Files the Agent Manages

| File | Purpose |
|---|---|
| `activity_log.md` | What the agent did across all sessions |
| `growth_metrics.json` | Sessions, cost, categories, skill count |
| `knowledge.md` | Lessons learned — grows every session |
| `BACKLOG.md` | Task backlog — agent reads, updates, marks done |
| `current_task.md` | Active task tracker (auto-resume on restart) |
| `research_queue.md` | Topics to research in next self-growth session |
| `skills/INDEX.md` | Reusable code patterns the agent has saved |
| `skills/*.py` | Individual saved skill files |
| `reports/YYYY-MM-DD.md` | Daily session reports |
| `health_log.json` | Test pass/fail history per session |
| `trajectories.md` | Successful approaches (used as few-shot examples) |
| `experiment_results.tsv` | Hypothesis test results — what worked, what didn't |
| `daily_budget.json` | API spend tracker per day |
| `backend_mode.json` | Saved choice: vscode or api mode |

---

## Command Reference

```bash
# Run forever (default: every 2 hours)
py -X utf8 autoagent/run.py

# Run one session and exit
py -X utf8 autoagent/run.py --once

# Run exactly N sessions and exit
py -X utf8 autoagent/run.py --tasks 3

# Show today's spend and recent activity
py -X utf8 autoagent/run.py --status

# Run E2E smoke test
py autoagent/e2e_check.py

# Reset backend mode choice
del autoagent\backend_mode.json
```

---

## Backend Modes

When you first run the agent, it asks:

**VS Code mode** — Uses Claude Code CLI (`claude.cmd`). Zero API cost. Requires Claude Pro subscription + `npm i -g @anthropic-ai/claude-code`. Auto-detects and waits through rate limits.

**API mode** — Uses Anthropic API directly. Pay-per-token. Budget enforcement built in. Requires `ANTHROPIC_API_KEY` in `.env`.

The choice is saved in `backend_mode.json`. Delete it to re-select.

---

## How the Agent Grows

Every session the agent:

1. **Research first** — searches for current best practices before touching any file
2. **Plans** — reads every file it will touch, writes a 3-step plan
3. **Implements** — commits after every logical step, tracks progress in `current_task.md`
4. **Validates** — runs tests + build checks before every commit
5. **E2E tests** — runs Playwright browser test for any UI change
6. **Self-reflects** — writes a concrete lesson to `knowledge.md`
7. **Saves skills** — saves reusable patterns to `skills/`
8. **Self-modifies** — improves its own `run.py` when it finds a better approach

Every 5th session is a **self-growth session**: research queue, Anthropic updates, financial audit, agent architecture review.

---

## Multi-Specialist Agency

The agent assembles the right specialist team for each task:

- **Engineer session** — ships the highest-value backlog feature
- **Designer session** — improves UI/UX, fetches competitor UIs, implements better
- **Research session** — finds new data sources, APIs, integrations
- **QA session** — fills test coverage gaps, improves E2E checks

Sessions rotate automatically. Session 5, 10, 15, ... are self-growth sessions.

---

## Configuration Reference (`config.json`)

```json
{
  "model": "claude-sonnet-4-6",
  "daily_limit_usd": 15.0,
  "interval_hours": 2,
  "session_max_turns": 50,
  "input_cost_per_token": 0.000003,
  "output_cost_per_token": 0.000015,
  "frontend_url": "http://localhost:3000",
  "backend_url": "http://localhost:8000"
}
```

| Field | Description |
|---|---|
| `model` | `claude-haiku-4-5-20251001` / `claude-sonnet-4-6` / `claude-opus-4-6` |
| `daily_limit_usd` | Max spend per day (API mode only) |
| `interval_hours` | Hours between sessions in loop mode |
| `session_max_turns` | Max tool-call turns per session |
| `frontend_url` | Used by `e2e_check.py` for browser tests |
| `backend_url` | Used by health checks if applicable |

The agent updates `model` and cost fields automatically via the `optimize_costs` tool.

---

## Adapting for Your Project

The agent reads `PROJECT.md` at the start of every session and injects it into context. Fill it in with:

- What the project does
- Tech stack and how to run it
- Business model / goals
- Any project-specific commands (how to run tests, build, etc.)

The agent will also learn project-specific commands from `knowledge.md` as it works — it saves lessons automatically.

---

## Requirements

- Python 3.10+
- `anthropic`, `httpx`, `beautifulsoup4`, `python-dotenv`, `playwright`
- For VS Code mode: Node.js + `npm i -g @anthropic-ai/claude-code`
- For API mode: `ANTHROPIC_API_KEY` in `.env`
