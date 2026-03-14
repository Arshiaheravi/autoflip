# AutoFlip Intelligence - PRD

## Original Problem Statement
Build a web app that monitors two car dealer websites (Cathcart Auto: rebuilders + used, and Pic N Save), scrapes all vehicle listings, and calculates estimated profit for each car (buy, fix, resell) in Ontario, Canada.

## Architecture
- **Backend**: FastAPI + MongoDB + httpx + BeautifulSoup (scraping)
- **Frontend**: React + TailwindCSS + Shadcn UI
- **Scraping**: Real-time scraping of cathcartauto.com and picnsave.ca every 5 minutes
- **Market Value**: Formula-based estimation (AutoTrader/Kijiji scraping planned)

## What's Implemented (2026-03-14)
- [x] Real scraping of 3 dealer sources: Cathcart Rebuilders (51), Cathcart Used (12), Pic N Save (59)
- [x] 122 real vehicle listings with photos, prices, mileage, damage, brand
- [x] Profit calculation engine: market value, repair costs, Ontario fees, best/worst case
- [x] Deal scoring (1-10) with BUY/WATCH/SKIP labels
- [x] One-page dashboard with table view, filters, sorting, detail dialogs
- [x] Auto-scrape every 5 minutes + manual "Scrape Now" button
- [x] Price parsing handles edge cases ($On Sale, $####, $29.995.00)
- [x] 100% test pass rate (backend + frontend + integration)

## Testing (2026-03-14)
- Backend: 100% (38/38)
- Frontend: 100%
- Integration: 100%

## Backlog
### P0
- Real AutoTrader.ca/Kijiji market value scraping (currently formula-based)

### P1
- Watchlist feature to track specific vehicles
- Price change detection and alerts
- New listing notifications

### P2
- Mobile-optimized view
- CSV/PDF export
- Historical price tracking charts
