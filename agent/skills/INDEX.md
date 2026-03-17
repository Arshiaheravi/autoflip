# Skill Library

Reusable patterns saved by the agent. Check here before writing from scratch.

- **mongodb_upsert_with_history** — Upsert a listing and track price history atomically (`agent/skills/mongodb_upsert_with_history.py`)
- **httpx_scraper_base** — Resilient httpx scraper with retry, User-Agent, timeout, BeautifulSoup parse (`agent/skills/httpx_scraper_base.py`)
- **fastapi_jwt_dependency** — FastAPI dependency that validates JWT and returns current user (`agent/skills/fastapi_jwt_dependency.py`)
- **sendgrid_with_smtp_fallback** — Send email via SendGrid with SMTP fallback and silent fail if keys missing (`agent/skills/sendgrid_with_smtp_fallback.py`)
- **auction_listing_scraper** — Paginated auction site scraper with crawl-delay, miles→km conversion, buy-now/bid price extraction, brand status mapping (`agent/skills/auction_listing_scraper.py`)
- **localstorage_watchlist_hook** — React useWatchlist hook: toggle/isSaved/count backed by localStorage, with mock pattern for jest.mock, stopPropagation rule, and lucide fill trick (`agent/skills/localstorage_watchlist_hook.py`)
- **stripe_checkout_fastapi** — Stripe Checkout Session creation + webhook handler for FastAPI/Motor: raw body for sig verification, customer reuse, checkout.session.completed upgrade flow, frontend redirect + success banner pattern (`agent/skills/stripe_checkout_fastapi.py`)
- **compare_modal_react** — Multi-listing side-by-side comparison modal: winnerIndex helper, CompareRow with direction/formatter, dynamic grid columns via inline style, floating compare bar with max-3 enforcement, jest mock pattern (`agent/skills/compare_modal_react.py`)
