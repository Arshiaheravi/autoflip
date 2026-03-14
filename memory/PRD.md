# AutoFlip Intelligence - PRD

## Problem Statement
Build a web app that monitors two car dealer websites (Cathcart Auto, Pic N Save), scrapes all vehicle listings, and automatically calculates the estimated profit for each car if bought, fixed, and resold in Ontario, Canada. Calculations must be "perfectly accurate", reflecting a professional car flipper's assessment.

## Tech Stack
- Backend: FastAPI, Motor (MongoDB async), httpx, BeautifulSoup4, emergentintegrations (GPT-4o vision)
- Frontend: React, TailwindCSS, Shadcn/UI, Axios
- Database: MongoDB
- AI: GPT-4o via Emergent Integrations for damage detection from photos

## Architecture
```
/app
├── backend/
│   ├── server.py       # FastAPI app, scrapers, v2 calc engine, AI damage detection, API endpoints
│   ├── tests/          # pytest test files (test_filters.py, test_v2_calc_engine.py)
│   └── .env            # MONGO_URL, DB_NAME, EMERGENT_LLM_KEY
└── frontend/
    ├── src/
    │   ├── App.js      # All pages: Dashboard, About, Settings
    │   ├── lib/api.js  # Axios API client
    │   ├── lib/utils-app.js  # Formatting utilities (fmt, fmtDate, etc.)
    │   └── index.css   # Global styles + CSS vars
    └── .env
```

## Key API Endpoints
- GET /api/listings - Filterable/sortable listing list (source, brand_type, status, search, damage_type, min_profit, max_price, min_score, sort_by including date)
- GET /api/listings/{id} - Single listing with full v2 breakdown
- GET /api/stats - Dashboard stats summary
- GET /api/calc-methodology - Full documentation of calculation engine v2
- POST /api/recalculate - Recalculate all listings with v2 engine + AI damage detection
- POST /api/scrape - Trigger manual scrape
- GET /api/scrape-status - Current scrape status + countdown
- GET /api/scan-history - Past scan log
- GET /api/settings / PUT /api/settings - User settings

## Calculation Engine v2.0 (Completed 2026-03-14)
### Market Value Formula
`Market Value = MSRP × Depreciation × Brand × BodyType × Trim × Color × Mileage × TitleStatus`

8 factors:
1. MSRP Baseline — 100+ model database
2. Depreciation Curve — Canadian Black Book-inspired (Year 1 = 82%, Year 5 = 48%, Year 10 = 25%)
3. Brand Retention — Toyota 1.18, Lexus 1.22, Honda 1.14, Dodge 0.88, Fiat 0.68
4. Body Type Demand — Trucks 1.30x, Off-road SUVs 1.20x, Compact SUVs 1.15x, Sedans 0.95x
5. Trim Level — Limited/Platinum 1.25x, Sport/GT 1.15x, XLT/EX 1.10x
6. Color Premium — White +4%, Black +3%, Silver +2%, Yellow -9%, Pink -12%
7. Mileage Adjustment — 18,000 km/yr avg, continuous curve (low = +8%, high = -18%+)
8. Title Status — Salvage 55%, Rebuilt 75%, Clean 100%

### Repair Cost Formula
`Total Repair = (Base Repair × Severity) + Safety ($100) + Salvage Process ($625 if salvage)`
- 16 damage zones with research-based cost ranges
- Severity multiplier: Minor 0.7x, Moderate 1.0x, Severe 1.4x, Total 1.8x
- Salvage-to-rebuilt: Structural inspection $400 + VIN verification $75 + Appraisal $150

### AI Damage Detection
- When no damage listed but photos exist, GPT-4o vision analyzes the car photo
- Returns damage type, severity, confidence, and details
- Only applied when confidence >= 40%
- 39 AI detections in latest scrape

### Ontario Fees
- HST: 13% of purchase price
- OMVIC: $22, MTO: $32, Safety: $100

### Deal Scoring (1-10)
- Based on average profit + ROI bonus (>60%: +1pt) + risk penalty (worst case < -$2000: -1pt)
- 8-10 = BUY, 5-7 = WATCH, 1-4 = SKIP

## Completed Features
- Full scrapers for Cathcart Auto (rebuilders + used) and Pic N Save
- v2.0 Enhanced calculation engine with 8-factor market value + AI damage detection
- Dashboard with stats, listing table with AI badges, detail dialog with expandable breakdown
- Filters: search, source, title type (Salvage/Clean/Rebuilt), status (For Sale/Coming Soon), sort by date
- Expanded filters: min profit, max price, min score, damage type
- Date Found column with relative dates
- About page, Settings page, Live scan indicator
- /api/calc-methodology documentation endpoint
- /api/recalculate endpoint for re-running calculations

## Backlog
- P1: Update About page to include v2 methodology details
- P1: Real AutoTrader/Kijiji scraping for actual market comps
- P2: Price drop alerts/notifications
- P2: Saved/favorited listings
- P2: "NEW" badge for listings found in last 24 hours
