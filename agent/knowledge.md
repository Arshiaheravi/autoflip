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

### 2026-03-16 — Data Specialist Session
- **IAA Canada and Copart are not scrapeable**: Both use Incapsula anti-bot protection. IAA explicitly disallows /Search in robots.txt. Don't attempt direct HTTP scraping — need JS rendering or API access.
- **SalvageReseller.com is a viable Ontario auction source**: Server-side rendered HTML, robots.txt allows listing pages (only blocks /admin/ /my-account/), requires 5-second crawl-delay. ~1,900+ Ontario salvage listings. Similar site: salvageautosauction.com.
- **parse_price() requires a $ sign**: Calling `parse_price("12,000")` returns None. Must pass `parse_price("$12,000")` or convert directly with `float(str.replace(",",""))`.
- **`\$?` regex in Python 3.14 is problematic** in certain contexts. Use `[^\d]*` to match optional non-digit chars (like `$`) before a number instead of `\$?`.
- **Miles to km**: SalvageReseller shows odometer in miles. 1 mile = 1.60934 km. Always convert for consistency with Canadian car buyers.
- **Auction current bid starts at $0**: Don't use current bid as price for profit calculations if it's $0 — it skews deal scores. Prefer "Buy It Now" price when available.

### 2026-03-16 — UX Session
- **Always update test mocks when adding new imports from mocked modules.** The `utils-app` mock in Dashboard.test.jsx must include every function imported by the component — otherwise tests crash at render time, not at assertion time, making it harder to debug.
- **`hasPriceDrop` and `priceDroplabel` helpers already existed in utils-app.js** — always check that file before implementing display logic. The backend fields (`has_price_drop`, `price_drop_amount`, `price_drop_pct`, `price_drop_only` filter) were also already in place. This session was purely a frontend wiring job.
- **Stats grid can grow from 5 → 6 columns**: use `md:grid-cols-6` not `md:grid-cols-5` when adding a new stat card. Mobile stays 2-col automatically.

### 2026-03-16 — UX Watchlist Session
- **Hooks that use localStorage must be mocked in tests.** `useWatchlist` lives in utils-app.js and is imported by Dashboard — the jest.mock for `@/lib/utils-app` must include it or the component crashes at render time with a "hooks must be called inside a component" error.
- **Adding a column to a CSS grid row requires updating both the row container AND the header row.** Desktop grid was `grid-cols-[…11 cols]` — adding a bookmark column required changing it to 12 cols in both `ListingRow` and the header div. Missing either causes misaligned columns.
- **`e.stopPropagation()` is essential for buttons inside clickable rows.** Without it, clicking the bookmark button also opens the listing modal. Always add stopPropagation to nested interactive elements inside click-to-open containers.
- **`fill` prop on lucide icons creates filled vs outline variants.** `<Bookmark fill="currentColor" />` renders a filled bookmark; `fill="none"` renders the outline. This is the cleanest way to show active/inactive state for icon-only buttons.

### 2026-03-16 — Stripe Checkout Session
- **Check for existing files before implementing**: Both `stripe_routes.py` and `test_stripe_routes.py` were already fully written in a prior session — this session just needed to commit the files and wire the frontend. Always check `git status` and read the file tree before assuming a feature needs to be written from scratch.
- **Stripe webhook requires raw request body**: Never let FastAPI/Starlette parse the body as JSON before `stripe.Webhook.construct_event()` — call `await request.body()` directly. The signature verification will fail on a parsed body.
- **`window.location.href = url` for cross-origin redirects**: Stripe Checkout is on `checkout.stripe.com`. React Router `navigate()` only works for same-origin routes. Use `window.location.href` to redirect to an external URL.
- **Clear checkout params from URL after success**: After Stripe redirects back to `/?checkout=success&session_id=...`, call `window.history.replaceState({}, '', pathname)` to clean the URL so a page refresh doesn't re-show the banner.
- **Stripe price IDs must be created in the Stripe Dashboard**: The backend references `STRIPE_PRICE_MONTHLY_ID` and `STRIPE_PRICE_YEARLY_ID` env vars. The owner must create Products + Prices in Stripe Dashboard and copy the Price IDs — the backend cannot create them automatically.

### 2026-03-16 — Deal Intelligence Session
- **ROI tiers in calc_deal_score must match flipper economics**: A single ±1 ROI adjustment was too coarse — $2k profit on $2k car (100% ROI) and $2k profit on $20k car (10% ROI) got the same base score. Extended to: roi>100%→+2, roi>60%→+1, roi<-30%→-2, roi<-10%→-1. Two new tests added (225 total).
- **run_experiment gate works best when changes add new tests**: The previous mileage experiment failed with delta=0 because it modified scores but no new tests were added to capture the expected new behavior. Always add tests that assert the specific new behavior — this makes the metric_after > metric_before clear.
- **Simplicity criterion**: The ROI tier extension is 4 lines net for a meaningful scoring improvement. Compare to the discarded mileage experiment which added a complex function call with 0 measurable improvement. Small, principled changes beat large speculative refactors.

### 2026-03-16 — Self-Growth Session #15

#### Anthropic Model Pricing (verified 2026-03-16 — update if stale)
| Model | Input $/MTok | Output $/MTok | Context | Notes |
|---|---|---|---|---|
| claude-opus-4-6 | $5 | $25 | 1M | Best for complex coding/agents |
| claude-sonnet-4-6 | $3 | $15 | 1M | Best balance speed/quality |
| claude-haiku-4-5-20251001 | $1 | $5 | 200k | Fastest, cheapest — use for research |
- **Bug fixed in run.py**: `optimize_costs` had Haiku at $0.80/$4 (wrong) and Opus at $15/$75 (old Opus 4 pricing). Corrected to $1/$5 and $5/$25 respectively.
- **Claude Haiku 3 deprecated**: Retires April 19, 2026. Already using Haiku 4.5.
- All current models support extended thinking, 1M context (Haiku 4.5 = 200k).

#### Prompt Caching — Key Facts
- Cache reads cost **10% of base input** — 90% savings on repeated content
- Minimum cacheable: 2,048 tokens for Sonnet 4.6 / 4,096 for Opus 4.6 and Haiku 4.5
- TTL: 5 minutes default, 1 hour available at 2x base price
- Automatic caching: add `cache_control={"type": "ephemeral"}` at top level — system moves breakpoint forward each turn
- Explicit breakpoints: up to 4 per request, placed on individual content blocks
- Cache reads don't count against rate limits
- Implementation: system prompt (huge in this agent) + knowledge.md are prime candidates to cache
- This is in the research queue for agent/run.py integration — implement in a dedicated self-growth session

#### React 19 New Patterns (2026)
- `use()` hook: read async resources + context without useEffect
- `useActionState()`: handle form action state + pending/error states
- `useOptimistic()`: show optimistic UI updates before server confirms
- **React Compiler** (stable 2025): auto-memoizes — can remove most `useMemo`/`useCallback` calls
- Server Components: cut initial JS payload 30-50% — not applicable to our CRA setup
- `useTransition`: wrap heavy filter/sort operations to keep UI responsive

#### FastAPI Best Practices 2026
- Always use async DB drivers (Motor for MongoDB — already doing this)
- Connection pooling: Motor handles this internally — no extra config needed
- Never mix `async def` route handlers with sync blocking libraries
- Use `BackgroundTasks` for light async work after response; use APScheduler/Celery for heavy scheduled work
- FastAPI benchmarks: ~900 req/s at 70ms latency with proper async usage

#### IAA Canada / Copart Canada — Research Conclusion
- **Both sites are protected by Cloudflare + JS rendering** — direct httpx scraping will never work
- Rebrowser and parser.best offer commercial scraper APIs for these sites
- **Strategy**: Accept these as blocked for DIY scraping. Consider adding a "manual import" feature where users paste a VIN or URL and we enrich it with our calculation pipeline. This avoids the anti-bot problem entirely.
- Available fields if we ever get API access: VIN, damage type, bid price, auction date, mileage, location

#### Competitor Intelligence (2026-03-16)
- **Flipped.ca** — Direct Canadian competitor. Sells cars online, trade-in focused. Different angle (consumer) but overlapping market.
- **vAuto Stockwave** — Dealer-focused wholesale vehicle sourcing SaaS. We serve the flip/private market they ignore.
- **2026 trend**: "Super App" consolidation — buyers want buying + selling + watchlist + push notifications in one app.
- **Differentiator**: "Smart watchlist notifications — get alerted before a deal is gone" is called out as THE key differentiating feature in 2026 SaaS auction tools. AutoFlip already has email alerts — this is a marketing angle to emphasize.
- **Marketing copy update**: Lead with "Get alerted on BUY deals in 10 minutes" rather than "monitor auctions". Speed + specificity is what converts in this market.

### 2026-03-16 — Data Specialist Session (Copart Ontario scraper)
- **SalvageReseller has two different URL templates**: `/cars-for-sale/location/ontario_auction-on` uses `div.vehicle-row` structure (25 listings per page). `/cars-for-sale/state/ontario` uses a different div-based layout without the `vehicle-row` class (2,138 Ontario Copart lots total). The two URLs serve different page templates on the same platform.
- **Multi-strategy HTML parsing is essential for resilient scrapers**: When the primary CSS class selector fails, fall back to finding anchor tags matching the lot URL pattern (`/cars-for-sale/\d+-\d{4}-`), then walk up the DOM to find the containing block. This handles template changes gracefully.
- **SalvageReseller.com IS the Copart broker access point**: The `state/ontario` URL returns all ~2,138 Ontario Copart lots (Bowmanville, Ottawa, other yards) accessible to non-license holders via SalvageReseller's broker service. This is the workaround for Copart's direct anti-bot protection.
- **Ontario salvage auction landscape**: After exhaustive research, the viable public sources are: Cathcart Auto, Pic N Save, SalvageReseller (ontario_auction-on), and SalvageReseller state-wide (copart_on). IAA/Copart direct = blocked. abetter.bid = 403. barga.ca = no automotive listings + robots.txt disallows categories. autoauctionsalvage.com = same network as SalvageReseller (duplicate data risk). GCSurplus = error/empty.
- **Copart broker sites share infrastructure**: salvageautosauction.com and salvagereseller.com use the same CDN (`images.salvagereseller.com`). Adding salvageautosauction.com as a source would return duplicate vehicle URLs. Always check image CDN to detect sister sites.
- **URL-based deduplication in runner.py handles overlapping sources**: If the same vehicle URL appears in multiple scraper runs, the `existing = await db.listings.find_one({"url": url})` check prevents duplicates. New sources with different lot URLs add genuinely new data.
