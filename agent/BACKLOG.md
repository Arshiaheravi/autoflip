# AutoFlip — Agent Backlog

This file is maintained by the autonomous agent. It reads this every session,
picks the highest-value task, implements it, then updates this file.

---

## 🔴 HIGH PRIORITY — Revenue / Core

- [ ] **Subscription landing page** — Build a dedicated `/subscribe` or `/pricing` page with plan cards ($4.99/mo, $39.99/yr), feature list ("Get new deal alerts every 10 min", "Profit analysis on every car", "AI damage detection"), and a CTA button. This is the #1 revenue driver.
- [ ] **User authentication** — Add email/password signup + login using JWT. Required before subscription can work. Store users in MongoDB `users` collection.
- [ ] **Deal alert email notifications** — When a new BUY deal (score 8+) is scraped, email subscribed users within 10 minutes. Use FastAPI BackgroundTasks + SMTP or SendGrid.
- [ ] **Add IAA Canada auctions** — Scrape https://www.iaai.com/vehiclesearch?lang=en_CA for Ontario salvage/rebuild vehicles. Massive untapped source.
- [ ] **Add Copart Canada** — Scrape https://www.copart.com/lotSearchResults/?free=true&query=ontario for Ontario listings.

---

## 🟡 MEDIUM PRIORITY — User Value

- [ ] **Price history tracking** — When a listing is scraped again with a changed price, log the old price. Show a "price dropped $X" badge on listings that dropped in price. Store in MongoDB `price_history` collection.
- [ ] **Watchlist / saved listings** — Let users click a ★ to save a listing. Persist in localStorage (no auth needed for v1). Show a "Saved" tab in Dashboard.
- [ ] **Side-by-side comparison** — Select 2-3 listings with checkboxes and open a comparison modal showing profit, mileage, damage, ROI side by side.
- [ ] **Improved deal scoring** — Factor in mileage (high mileage = more risk), colour (black/white sell faster), and time on market when scoring deals.
- [ ] **Better mobile layout** — The desktop table is hidden on mobile but the card view is basic. Add swipe gestures, better photo display, and a sticky filter bar.
- [ ] **AutoTrader live comps in listing detail** — Show a "View comparable listings on AutoTrader" button that deep-links to AutoTrader with the correct make/model/year/location pre-filled.

---

## 🟢 LOW PRIORITY — Polish & Marketing

- [ ] **SEO meta tags** — Add Open Graph + Twitter Card meta tags to the React app so links shared on social look good.
- [ ] **About page marketing copy** — Rewrite the About page to be more sales-focused: "Stop wasting hours checking auction sites manually. AutoFlip alerts you to profitable cars before anyone else even knows they're listed."
- [ ] **Referral system** — Give users a referral code. If someone subscribes through their link, they get 1 month free.
- [ ] **Export to CSV** — Add a button on Dashboard to export current filtered listings as CSV (title, price, profit, score, URL).
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

---

## 💡 Research & Ideas (to be investigated)

- Kijiji auto listings — Can we scrape without violating ToS? Research.
- Facebook Marketplace cars — API access? Probably not. Manual note: tell users to check.
- Insurance write-off databases — Is there a public Ontario source for salvage titles?
- Real-time notifications via WebSocket — Push new deals to browser without polling.
- WhatsApp / Telegram bot — Send BUY deal alerts to a WhatsApp group or Telegram channel.
