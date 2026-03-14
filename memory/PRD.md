# AutoFlip Intelligence - PRD

## Problem Statement
Build a web app that monitors two car dealer websites (Cathcart Auto, Pic N Save), scrapes all vehicle listings, and automatically calculates the estimated profit for each car if bought, fixed, and resold in Ontario, Canada.

## Tech Stack
- Backend: FastAPI, Motor (MongoDB async), httpx, BeautifulSoup4
- Frontend: React, TailwindCSS, Shadcn/UI, Axios
- Database: MongoDB

## Architecture
```
/app
├── backend/
│   ├── server.py       # FastAPI app, scrapers, calc engine, API endpoints
│   ├── tests/          # pytest test files
│   └── .env
└── frontend/
    ├── src/
    │   ├── App.js      # All pages: Dashboard, About, Settings
    │   ├── lib/api.js  # Axios API client
    │   ├── lib/utils-app.js  # Formatting utilities
    │   └── index.css   # Global styles + CSS vars
    └── .env
```

## Key API Endpoints
- GET /api/listings - Filterable/sortable listing list (source, brand_type, status, search, damage_type, min_profit, max_price, min_score, sort_by)
- GET /api/listings/{id} - Single listing detail
- GET /api/stats - Dashboard stats summary
- POST /api/scrape - Trigger manual scrape
- GET /api/scrape-status - Current scrape status + countdown
- GET /api/scan-history - Past scan log
- GET /api/settings - User settings
- PUT /api/settings - Update scan interval

## Completed Features
- Scrapers for Cathcart Auto (rebuilders + used) and Pic N Save
- Market value estimation engine (make/model/year/mileage/trim/type multipliers)
- Repair cost estimation by damage type
- Ontario fees calculation (HST 13% + OMVIC + MTO + Safety)
- Profit calculation (best/worst case)
- Deal scoring (1-10) with BUY/WATCH/SKIP labels
- Dashboard with stats bar, listing table, detail dialog
- Filter bar: search, source, title type (Salvage/Clean/Rebuilt), status (For Sale/Coming Soon), sort
- Expanded filters: min profit, max price, min score, damage type
- About page with full methodology explanation
- Settings page with scan interval config + scan history
- Live scan indicator with countdown
- Auto-refresh every 30s + configurable background scrape interval
- Price history tracking on re-scrapes

## Filter Feature (Added 2026-03-14)
- Brand type filter: Salvage, Clean, Rebuilt (regex match on brand field)
- Status filter: For Sale, Coming Soon
- Both filters combinable with all existing filters
- Backend: brand_type query parameter on GET /api/listings
- Frontend: Two new Select dropdowns with data-testid attributes

## Date Found Feature (Added 2026-03-14)
- Each listing shows "Date Found" — when it was first discovered by the scraper
- Desktop: new "Found" column in the listing table with relative dates (Just now, 2h ago, Yesterday, 3d ago, Mar 15)
- Mobile: date shown inline on each card
- Detail dialog: full date shown in info cells row
- Sort by "Date Found" option added to sort dropdown
- Backend: sort_by=date uses first_seen field

## Backlog
- P0: Enhance calculation engine for hyper-accuracy (user requested "perfectly accurate" calculations)
- P0: Update About page with detailed new calculation methodology
- P1: Actual AutoTrader/Kijiji scraping for real market value comps
- P2: Price drop alerts/notifications
- P2: Saved/favorited listings
