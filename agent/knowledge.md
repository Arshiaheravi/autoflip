# Agent Knowledge Base

This file is written and updated by the agent itself after every session.
It captures patterns, lessons, discoveries, and best practices that persist across sessions.
The agent reads this at the start of every session to avoid repeating mistakes.

---

## Project Patterns

- Backend entry point: `backend/app/main.py` — runs as `py -m uvicorn app.main:app --port 8001`
- All routes use relative imports: `from ..database import db`, `from ..services.calculations import ...`
- MongoDB collections: `listings`, `scan_history`, `autotrader_cache`, `settings`, `users`
- Scraper pattern: each scraper returns list of dicts with keys: `title`, `price`, `damage`, `brand_status`, `colour`, `mileage`, `photo_urls`, `source`, `url`
- Calculations pipeline: `estimate_market_value_blended()` → `get_repair_range()` → `calculate_ontario_fees()` → `calc_deal_score()`
- Auth pattern: JWT Bearer token in `Authorization` header. `get_current_user()` helper in `routes/auth.py` reusable across any route.
- User document keys: `id`, `email`, `name`, `password_hash`, `plan` (free/pro), `subscription_status`, `billing_period`, `alerted_listings` (list of listing IDs already emailed about)

## Email Alert Pattern

- Email service lives in two files: `email.py` (SendGrid only) and `email_alerts.py` (SendGrid + SMTP fallback)
- `email_alerts.py` is the more complete one — use it for new features
- Deal alerts fire in `runner.py` `run_full_scrape()` — only for **new** listings with score >= 8 (not re-scans of existing)
- `send_bulk_deal_alerts(listing, db)` queries `db.users` for `plan="pro"` + `subscription_status="active"` + not already alerted
- After sending, marks listing ID in `user.alerted_listings` using `$addToSet` — prevents duplicate alerts
- If `SENDGRID_API_KEY` missing → silent warning, returns 0 (never crashes)

## Validation Commands

```bash
# Backend syntax check (run after any .py edit)
py -c "import sys; sys.path.insert(0,'backend'); from app.main import app; print('OK')"

# Run all tests
py -m pytest backend/tests/ -x -q --tb=short

# Compile-check a single file
py -m py_compile backend/app/routes/scrape.py

# Frontend build check (MANDATORY before any frontend commit — catches JSX syntax errors)
cd frontend && PATH="/c/Program Files/nodejs:$PATH" "C:\Program Files\nodejs\npm.cmd" run build 2>&1 | tail -20

# Frontend unit tests (run from /tmp copy because OneDrive blocks scoped npm packages)
# IMPORTANT: Always run with NODE_ENV=development first to ensure devDeps install
cp -r frontend/src /tmp/autoflip-fe/src && NODE_ENV=test PATH="/c/Program Files/nodejs:$PATH" "C:\Program Files\nodejs\npm.cmd" --prefix /tmp/autoflip-fe test -- --watchAll=false --forceExit 2>&1 | tail -10
```

### OneDrive + npm scoped packages issue (known)
- OneDrive's "Files On-Demand" prevents scoped packages (`@testing-library/*`, `@craco/craco`) from installing in top-level node_modules when `NODE_ENV=production` (the default in shell)
- Fix: always run `npm install` with `NODE_ENV=development`
- For tests: maintain a shadow copy at `/tmp/autoflip-fe/` with packages properly installed
- The frontend build still works via `npm run build` because npm's internal PATH resolution uses Windows-native file access (which triggers OneDrive download-on-demand)

## Known Issues / Watch Out For

- Windows console: use `py -X utf8` to avoid UnicodeEncodeError
- httpx requests to auction sites need User-Agent headers or they return 403
- Motor (async MongoDB) — never use sync pymongo calls inside async functions
- BeautifulSoup: always specify parser (`"html.parser"`) to avoid warnings
- Frontend `@/` alias maps to `frontend/src/` (configured in jsconfig.json + craco.config.js)
- **Python 3.14**: `asyncio.get_event_loop()` raises RuntimeError in test threads — always use `asyncio.run()` in test code instead
- **pytest-asyncio STRICT mode**: `@pytest.mark.asyncio` tests work fine but non-async tests using `asyncio.run()` are more portable
- **Two email service files exist** (`email.py` + `email_alerts.py`) — don't import from the wrong one. `email_alerts.py` supports SMTP fallback, `email.py` is SendGrid-only.

## Subscription Flow (ready for Stripe)

- `/api/auth/subscribe` POST endpoint: updates `plan`, `billing_period`, `subscription_status` for authenticated user
- Accepts: `plan` (free/pro), `billing_period` (monthly/yearly), `subscription_status` (active/inactive/cancelled/past_due)
- Also accepts `stripe_customer_id` and `stripe_subscription_id` for Stripe webhook reconciliation
- `safe_user()` now returns `billing_period` and `subscribed_at` fields
- Stripe webhook handler just needs to call this endpoint (or directly call `db.users.update_one`) — all fields already exist

## Self-Improvement Research (2026-03-16)

Key findings from real papers — apply these techniques actively:

### Reflexion (Shinn et al., NeurIPS 2023) — PROVEN: 80% → 91% on HumanEval
- After every failure: generate a verbal critique (what went wrong, why, what to do differently)
- Store critique in memory → next attempt reads it → avoids repeating the exact same mistake
- "Verbal gradients" are more informative than scalar rewards — write specific lessons not generic ones
- Already implemented: `write_post_mortem` tool stores root_cause + prevention rule to knowledge.md

### Voyager (Wang et al., 2023) — PROVEN: 3.1x more capability, 15x faster milestone completion
- Skills as executable code > skills as prompts — code is testable, composable, doesn't degrade
- Three-gate validation before storing a skill: (1) executes without error, (2) achieves desired state, (3) peer review
- Skills retrieved by embedding similarity — describe each skill well so retrieval finds it
- Already implemented: `save_skill` tool + `agent/skills/` + `agent/skills/INDEX.md`

### Live-SWE-agent (2025) — PROVEN: 77.4% SWE-bench at near-zero cost vs DGM's 53.3% at 1,231 GPU-hours
- Starting with only bash tools, the agent creates custom tools at runtime as it needs them
- Custom tools provide better error messages than generic bash → richer feedback → faster learning
- Runtime tool creation > offline evolutionary search for most production use cases
- Lesson: when a task is hard with current tools, consider adding a new specialized tool to run.py

### Reflexion + Few-Shot Exemplars — PROVEN: 73% → 93% on ALFWorld
- Store successful task trajectories as exemplars
- When starting a similar new task, retrieve the relevant past trajectory as a few-shot example
- Already implemented: auto-stored in `agent/trajectories.md` on every successful `task_complete`

### Prompt Caching (Anthropic) — can reduce cost 80%+
- System prompt + knowledge.md repeated every turn = the biggest cost driver in long sessions
- Implement prompt caching: mark system prompt as cacheable using cache_control breakpoints
- See: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- This is in research_queue.md as HIGH priority — implement it in next self-growth session

### External Verifiers > Self-Evaluation
- When ground truth exists (test pass/fail, benchmark scores), use it — don't rely on LLM self-assessment
- `run_health_check` already implements this — call it before EVERY task_complete
- If health score < 3, fix the regressions before completing

### Conservative Acceptance Gates
- Every self-modification system that works has a gate: only accept changes that improve measurable metrics
- When modifying agent/run.py: verify the change actually helps by checking health_score trend in HEALTH_LOG_FILE
- Never make multiple speculative changes at once — change one thing, verify it, then change another

## Lessons Learned

### 2026-03-16 — Session 3
- **Always run `npm run build` before committing any frontend file.** JSX syntax errors (unescaped apostrophes in single-quoted JS strings: `'We're'` → `"We're"`) only surface at build time, not in the editor. The fix: use double quotes around strings containing apostrophes, or use `&apos;` in JSX string literals.

### 2026-03-16 — Session 2
- **Read before coding**: Email service and tests were partially implemented from a previous session. Always check `backend/app/services/` and `backend/tests/` before implementing "new" features.
- **asyncio.run() vs get_event_loop()**: Python 3.14 drops implicit event loop. Use `asyncio.run(coro)` in all test code, never `asyncio.get_event_loop().run_until_complete(coro)`.
- **pytestmark skipif pattern**: For integration tests that need a running server, always add `pytestmark = pytest.mark.skipif(not BASE_URL, reason="...")` at module level — CI-safe and already done for filter/calc tests.
- **Deal alerts should only fire for NEW listings** (first insert), not updates. This prevents alert spam on every re-scrape of existing listings.
- **`$addToSet` in MongoDB** is perfect for tracking "already alerted" listings — idempotent, no duplicates, single atomic operation.

## Autonomous Optimization Architect (agency-agents, 2026-03-16)

**Circuit breaker rule:** If session burn rate projects >70% of daily budget by turn 15 → switch to haiku or reduce context. Already implemented in run_session() — fires automatically.

**Model routing by task type:**
- Research/web_search/knowledge updates/marketing copy = haiku ($0.80/MTok) — 4x cheaper
- Complex coding/architecture/debugging = sonnet ($3/MTok)
- Rule: at session start, if task is research-heavy, call `optimize_costs` to switch to haiku

**"Never unbounded":** Every httpx request needs `timeout=20`. Every subprocess.run needs `timeout=N`. Every retry loop needs a cap. The run_health_check enforces 3-attempt cap on QA retries.

**40% cost reduction path:** Track task categories that worked on haiku. If scraper research, marketing sessions, knowledge absorption all work on haiku → route them there permanently.

## agents-orchestrator Dev-QA Loop (agency-agents, 2026-03-16)

**Max 3 QA attempts per step.** update_current_task now accepts qa_attempt (1-3) + qa_feedback (specific error text).
Pattern: run_health_check → FAIL → update_current_task(qa_attempt=2, qa_feedback="test_deal_score failed: expected 8.5 got 6.0") → fix exactly that → recheck.
After attempt 3: add `[!] Needs investigation: {error}` to BACKLOG.md and move to next task. Never loop forever.
