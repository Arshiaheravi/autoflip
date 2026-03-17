# AutoFlip — Agent Backlog

This file is maintained by the autonomous agent. It reads this every session,
picks the highest-value task, implements it, then updates this file.

---

## 🔴 HIGH PRIORITY — Revenue / Core

- [x] **Deal alert email notifications** — When a new BUY deal (score 8+) is scraped, email subscribed users within 10 minutes. SendGrid + SMTP fallback. `/api/auth/subscribe` endpoint added. 58+ unit tests passing. Needs `SENDGRID_API_KEY` in .env to activate.
- [x] **Subscription payment (Stripe)** — PricingPage Pro CTA now calls `/api/stripe/create-checkout-session`, redirects to Stripe hosted checkout, webhook upgrades `user.plan → 'pro'`. Dashboard shows success banner on return. 239 backend + 42 frontend tests passing. Needs Stripe env vars in .env to go live (see agent/api_requests.md).
- [x] **Add SalvageReseller.com** — Server-side rendered, no login, Ontario salvage/rebuild, 75 listings/run. Integrated into runner.py, 22 tests passing.
- [x] **Add Copart Ontario (via SalvageReseller broker)** — Scrapes `salvagereseller.com/cars-for-sale/state/ontario` (2,138 Ontario Copart lots). Source key `copart_on`. 150 listings/run (6 pages × 25). 20 tests passing. No dealer license required (SalvageReseller acts as registered broker).
- [ ] **Add IAA Canada auctions** — BLOCKED: Incapsula anti-bot + robots.txt disallows /Search. Need API or JS rendering approach.
- [ ] **Add Copart Canada direct** — BLOCKED: Anti-bot protection. Covered indirectly via SalvageReseller broker above.

---

## 🟡 MEDIUM PRIORITY — User Value

- [x] **Price history tracking** — Backend tracks price_history array + has_price_drop/price_drop_amount fields. Frontend now shows ↓ $X (Y%) badge on cards (desktop + mobile), price drop stat card in stats bar, and "Price drops only" filter toggle.
- [x] **Watchlist / saved listings** — Bookmark button on every listing (desktop + mobile), localStorage persistence via useWatchlist hook, "Saved" tab with count badge and empty state. 42 tests passing.
- [ ] **Side-by-side comparison** — Select 2-3 listings with checkboxes and open a comparison modal showing profit, mileage, damage, ROI side by side.
- [x] **Improved deal scoring** — Graduated worst-case penalty: worst<-2k→-1, worst<-5k→-2, worst<-10k→-3. Mileage + colour already affect score via market value pipeline. 261 tests passing.
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

- [x] **Research queue** — Researched prompt caching (90% savings on cache reads), IAA/Copart (blocked — Cloudflare), models pricing update.
- [x] **Financial audit** — Reviewed spend. VS Code mode = $0 cost. Pricing bug fixed in run.py (Haiku was $0.80→$1, Opus was $15→$5 per MTok).
- [x] **Absorb Anthropic updates** — Fetched models page. All 3 current models confirmed: Opus 4.6 ($5/$25), Sonnet 4.6 ($3/$15), Haiku 4.5 ($1/$5). Haiku 3 deprecated Apr 2026.
- [x] **GitHub knowledge absorption** — Searched FastAPI 2026, React 19 patterns. Key: React Compiler stable, auto-memoizes. FastAPI async best practices confirmed.
- [x] **Competitor intelligence** — Flipped.ca (Canadian), vAuto Stockwave (dealer). Marketing angle: "alerted in 10 minutes" is THE differentiator.
- [x] **Agent architecture review** — Read run.py fully. Fixed pricing bug. Prompt caching implementation queued as HIGH priority.
- [ ] **Implement prompt caching in run.py** — Add cache_control breakpoints to build_context(). 90% savings on cache reads. See research_queue.md HIGH item.

## 💡 Research & Ideas (to be investigated)

- Kijiji auto listings — Can we scrape without violating ToS? Research.
- Facebook Marketplace cars — API access? Probably not. Manual note: tell users to check.
- Insurance write-off databases — Is there a public Ontario source for salvage titles?
- Real-time notifications via WebSocket — Push new deals to browser without polling.
- WhatsApp / Telegram bot — Send BUY deal alerts to a WhatsApp group or Telegram channel.
- **Manual VIN/URL import** — User pastes any auction URL/VIN → we score it. Bypasses Copart/IAA anti-bot entirely.
- **Marketing copy refresh** — Lead with "Get alerted on BUY deals in 10 minutes" — speed + specificity is the 2026 SaaS differentiator for auction tools (confirmed via competitor research).
