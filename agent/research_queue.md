# Research Queue

Items to research in the next self-growth session.
Delete an item after researching it and updating knowledge.md.

---

- [HIGH] **Anthropic prompt caching** — Added 2026-03-16
  _Why: Could reduce cost 80% on long context sessions (system prompt + knowledge.md repeated every turn). Official docs at https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching_

- [HIGH] **Stripe Checkout + webhooks best practices 2026** — Added 2026-03-16
  _Why: Stripe integration is top backlog item. Need to know: checkout session creation, webhook idempotency, subscription lifecycle events before implementing._

- [HIGH] **IAA Canada / Copart scraping patterns** — Added 2026-03-16
  _Why: Both are top backlog sources. Need to check: do they require login? JS rendering? Rate limiting? Anti-bot measures? Find community scrapers on GitHub._

- [MEDIUM] **React 19 concurrent features + Suspense patterns** — Added 2026-03-16
  _Why: Using React 19 but not leveraging new features. Could improve UI performance and loading states significantly._

- [MEDIUM] **MongoDB Motor aggregation pipelines** — Added 2026-03-16
  _Why: Currently doing Python-level filtering on listings. Pushing filters to MongoDB aggregations would be faster and reduce memory usage._

- [MEDIUM] **FastAPI background tasks vs APScheduler** — Added 2026-03-16
  _Why: Currently using APScheduler for scrape scheduling. FastAPI has built-in BackgroundTasks — check if it would simplify the scrape runner._

- [MEDIUM] **Autonomous agent self-improvement papers (Reflexion, Voyager, MRKL)** — Added 2026-03-16
  _Why: Understanding the research behind self-improving agents will help improve this agent's architecture. Key papers: Reflexion (Shinn 2023), Voyager (Wang 2023), ReAct (Yao 2022)._

- [LOW] **Ontario car flipping communities + forums** — Added 2026-03-16
  _Why: Find where Ontario car flippers congregate online (Reddit r/flipping, Facebook groups, forums) — these are the target users for marketing._

- [LOW] **WebSocket vs SSE for real-time deal alerts** — Added 2026-03-16
  _Why: Currently users poll for new listings. Push notifications (WebSocket or Server-Sent Events) would be much better UX for deal alerts._
