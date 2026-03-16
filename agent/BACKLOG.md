# AutoFlip — Agent Backlog

This file is maintained by the autonomous agent. It reads this every session,
picks the highest-value task, implements it, then updates this file.

---

## 🔴 HIGH PRIORITY — Revenue / Core

- [x] **Deal alert email notifications** — When a new BUY deal (score 8+) is scraped, email subscribed users within 10 minutes. SendGrid + SMTP fallback. `/api/auth/subscribe` endpoint added. 58+ unit tests passing. Needs `SENDGRID_API_KEY` in .env to activate.
- [ ] **Subscription payment (Stripe)** — Wire up the existing PricingPage Pro CTA to a real Stripe Checkout. Users can pay $4.99/mo or $39.99/yr. Webhook updates user.plan → 'pro'. `/api/auth/subscribe` endpoint already built and ready.
- [x] **Add SalvageReseller.com** — Server-side rendered, no login, Ontario salvage/rebuild, 75 listings/run. Integrated into runner.py, 22 tests passing.
- [ ] **Add IAA Canada auctions** — BLOCKED: Incapsula anti-bot + robots.txt disallows /Search. Need API or JS rendering approach.
- [ ] **Add Copart Canada** — BLOCKED: Anti-bot protection. Same issue as IAA. Research API access.

---

## 🟡 MEDIUM PRIORITY — User Value

- [x] **Price history tracking** — Backend tracks price_history array + has_price_drop/price_drop_amount fields. Frontend now shows ↓ $X (Y%) badge on cards (desktop + mobile), price drop stat card in stats bar, and "Price drops only" filter toggle.
- [x] **Watchlist / saved listings** — Bookmark button on every listing (desktop + mobile), localStorage persistence via useWatchlist hook, "Saved" tab with count badge and empty state. 42 tests passing.
- [ ] **Side-by-side comparison** — Select 2-3 listings with checkboxes and open a comparison modal showing profit, mileage, damage, ROI side by side.
- [ ] **Improved deal scoring** — Factor in mileage (high mileage = more risk), colour (black/white sell faster), and time on market when scoring deals.
- [ ] **Better mobile layout** — The desktop table is hidden on mobile but the card view is basic. Add swipe gestures, better photo display, and a sticky filter bar.
- [ ] **AutoTrader live comps in listing detail** — Show a "View comparable listings on AutoTrader" button that deep-links to AutoTrader with the correct make/model/year/location pre-filled.

---

## 🟢 LOW PRIORITY — Polish & Marketing

- [ ] **SEO meta tags** — Add Open Graph + Twitter Card meta tags to the React app so links shared on social look good.
- [ ] **About page marketing copy** — Rewrite the About page to be more sales-focused.
- [ ] **Referral system** — Give users a referral code. If someone subscribes through their link, they get 1 month free.
- [ ] **Export to CSV** — Add a button on Dashboard to export current filtered listings as CSV.
- [ ] **Dark/light mode toggle** — Currently dark-only. Add a toggle.
- [ ] **Analytics dashboard** — Show historical stats: average profit per source, best performing damage types, best day of week to find deals.

---

## ✅ COMPLETED

- [x] Modular backend refactor (server.py → app/ with 10 focused modules)
- [x] Frontend split (App.js → Dashboard, AboutPage, SettingsPage, NavBar, ListingDetail)
- [x] Bilingual support (English + Persian with RTL)
- [x] AI damage detection (Claude Opus 4.6 vision)
- [x] Blended market valuation (AutoTrader comps 60% + formula 40%)
- [x] Deal scoring 1-10 (BUY / WATCH / SKIP)
- [x] Ontario fees calculation (HST, OMVIC, MTO, Safety)
- [x] User authentication (JWT + bcrypt, register/login/me routes, frontend LoginPage + SignupPage)
- [x] Subscription landing page (PricingPage.jsx with plan cards, billing toggle, FAQ, CTAs)
- [x] Price history tracking (price_history array, has_price_drop badge, price_drop_amount/pct fields)
- [x] Deal alert email notifications (SendGrid + SMTP fallback, /api/auth/subscribe endpoint, 58+ unit tests)

---

## 🧠 AGENT SELF-GROWTH (schedule every 5th session)

- [ ] **Research queue** — Work through agent/research_queue.md HIGH items: prompt caching (80% cost reduction), Stripe patterns (needed for payment), IAA/Copart scraping feasibility.
- [ ] **Financial audit** — Review spend per session in growth_metrics.json. If avg > $4/session, implement prompt caching (system prompt repeated every turn = huge cost). Switch to haiku for simpler sessions.
- [ ] **Absorb Anthropic updates** — Fetch https://docs.anthropic.com/en/docs/about-claude/models — check new models, features, prompt caching status. Update config.json + knowledge.md.
- [ ] **GitHub knowledge absorption** — Search "Claude agent CLAUDE.md", "FastAPI best practices 2026", "autonomous agent self-improvement GitHub" — absorb 3+ concrete techniques.
- [ ] **Anthropic Cookbook** — Fetch https://github.com/anthropics/anthropic-cookbook — look for tool use, vision, caching, agent patterns to improve this agent or app.
- [ ] **Competitor intelligence** — Search "car auction SaaS Canada 2026", "vehicle flipping app Ontario" — find gaps, update marketing copy in AboutPage.
- [ ] **Agent architecture review** — Read agent/run.py fully. Check self_critique_history in growth_metrics.json — improve weakest scoring dimension.

## 💡 Research & Ideas (to be investigated)

- Kijiji auto listings — Can we scrape without violating ToS? Research.
- Facebook Marketplace cars — API access? Probably not. Manual note: tell users to check.
- Insurance write-off databases — Is there a public Ontario source for salvage titles?
- Real-time notifications via WebSocket — Push new deals to browser without polling.
- WhatsApp / Telegram bot — Send BUY deal alerts to a WhatsApp group or Telegram channel.
