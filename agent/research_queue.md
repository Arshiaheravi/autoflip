# Research Queue

Items to research in the next self-growth session.
Delete an item after researching it and updating knowledge.md.

---

- [HIGH] **Prompt caching — implement in agent/run.py** — Added 2026-03-16
  _Why: Research confirmed 90% cost reduction on cache reads. System prompt + knowledge.md are massive repeated context every turn. Add cache_control breakpoints to build_context() in run.py to cut per-session cost by 60-80%. Min 2,048 tokens for Sonnet 4.6 — easily met. See knowledge.md for API details._

- [HIGH] **Manual VIN/URL import feature** — Added 2026-03-16
  _Why: IAA Canada and Copart are blocked by Cloudflare (confirmed). Alternative: let users paste a VIN or auction URL and we enrich with deal scoring. Unlocks any auction source without scraping._

- [MEDIUM] **React 19 React Compiler integration** — Added 2026-03-16
  _Why: React Compiler (stable 2025) auto-memoizes components — can remove useMemo/useCallback from Dashboard.jsx. Check compatibility with CRA/craco. useTransition for filter operations improves responsiveness._

- [MEDIUM] **MongoDB Motor aggregation pipelines** — Added 2026-03-16
  _Why: Currently doing Python-level filtering on listings. Pushing filters to MongoDB aggregations would be faster and reduce memory usage._

- [MEDIUM] **FastAPI background tasks vs APScheduler** — Added 2026-03-16
  _Why: Currently using APScheduler for scrape scheduling. FastAPI has built-in BackgroundTasks — check if it would simplify the scrape runner._

- [LOW] **Ontario car flipping communities + forums** — Added 2026-03-16
  _Why: Find where Ontario car flippers congregate online (Reddit r/flipping, Facebook groups, forums) — these are the target users for marketing._

- [LOW] **WebSocket vs SSE for real-time deal alerts** — Added 2026-03-16
  _Why: Currently users poll for new listings. Push notifications (WebSocket or Server-Sent Events) would be much better UX for deal alerts._
