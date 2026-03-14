# AutoFlip Intelligence - PRD

## Original Problem Statement
Build a web app that monitors two car dealer websites (Cathcart Auto: rebuilders + used, and Pic N Save), scrapes all vehicle listings, and calculates estimated profit for each car (buy, fix, resell) in Ontario, Canada. User-configurable scan interval, live status indicator, and an About page explaining the app.

## Architecture
- **Backend**: FastAPI + MongoDB + httpx + BeautifulSoup (scraping) + asyncio scheduler
- **Frontend**: React + TailwindCSS + Shadcn UI
- **Scraping**: Real-time scraping of cathcartauto.com and picnsave.ca every N minutes (configurable)
- **Market Value**: Formula-based estimation (AutoTrader/Kijiji live scraping planned)

## What's Implemented (2026-03-14)
- [x] Real scraping of 3 dealer sources (122 total listings): Cathcart Rebuilders (51), Cathcart Used (12), Pic N Save (59)
- [x] Profit calculation: market value, repair costs by damage type, Ontario fees, best/worst case, ROI
- [x] Deal scoring (1-10) with BUY/WATCH/SKIP recommendations
- [x] Dashboard page: table view with photos, prices, scores, filters, sorting
- [x] About page: hero section, features, website descriptions, profit calc explanation, repair cost table, scoring system, how-to guide
- [x] Settings page: scan frequency control (5/10/15/30 min), scan history log, data sources
- [x] Live scanning indicator: pulsing dot, countdown timer, interval display
- [x] Navigation: Dashboard / About / Settings tabs
- [x] Auto-scrape on configurable interval + manual "Scan Now" button
- [x] Smart inactive marking (per-source, only when source returns results)
- [x] Price parsing handles edge cases ($On Sale, $####, $29.995.00 European format)
- [x] 100% test pass rate (42/42 backend, all frontend + integration)

## Backlog
### P0
- Real AutoTrader.ca / Kijiji Autos market value scraping

### P1
- Watchlist feature to save/track specific vehicles
- Price change detection alerts
- New listing notifications (Telegram/email)

### P2
- Mobile-optimized card view improvements
- CSV/PDF export
- Historical price tracking charts
