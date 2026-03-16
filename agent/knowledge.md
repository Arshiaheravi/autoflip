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
```

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

## Lessons Learned

### 2026-03-16 — Session 3
- **Always run `npm run build` before committing any frontend file.** JSX syntax errors (unescaped apostrophes in single-quoted JS strings: `'We're'` → `"We're"`) only surface at build time, not in the editor. The fix: use double quotes around strings containing apostrophes, or use `&apos;` in JSX string literals.

### 2026-03-16 — Session 2
- **Read before coding**: Email service and tests were partially implemented from a previous session. Always check `backend/app/services/` and `backend/tests/` before implementing "new" features.
- **asyncio.run() vs get_event_loop()**: Python 3.14 drops implicit event loop. Use `asyncio.run(coro)` in all test code, never `asyncio.get_event_loop().run_until_complete(coro)`.
- **pytestmark skipif pattern**: For integration tests that need a running server, always add `pytestmark = pytest.mark.skipif(not BASE_URL, reason="...")` at module level — CI-safe and already done for filter/calc tests.
- **Deal alerts should only fire for NEW listings** (first insert), not updates. This prevents alert spam on every re-scrape of existing listings.
- **`$addToSet` in MongoDB** is perfect for tracking "already alerted" listings — idempotent, no duplicates, single atomic operation.
