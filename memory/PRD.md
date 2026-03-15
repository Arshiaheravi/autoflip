# AutoFlip Intelligence - PRD

## Problem Statement
Build a web app that monitors two car dealer websites (Cathcart Auto, Pic N Save), scrapes all vehicle listings, and calculates profit if bought, fixed, and resold in Ontario. Must use real market data + sophisticated formula for accuracy.

## Tech Stack
- Backend: FastAPI, Motor (MongoDB), httpx, BeautifulSoup4, emergentintegrations (GPT-4o vision)
- Frontend: React, TailwindCSS, Shadcn/UI, Axios
- Database: MongoDB
- AI: GPT-4o (damage detection), AutoTrader.ca (market comps)

## Calculation Engine v2.1 (Blended)
### Market Value = 60% AutoTrader Comps + 40% Formula
- **AutoTrader.ca**: Scrapes real Ontario listings for same make/model/year (±1yr). Extracts median asking price. 24hr DB-persisted cache. Rotating user agents, rate limiting (10 req/cycle).
- **Formula**: MSRP × Depreciation × Brand × BodyType × Trim × Color × Mileage × TitleStatus
- **Blend**: ≥3 comps → 60/40 AT/formula. 1-2 comps → 40/60. No comps → 100% formula.

### Repair Cost
- 16 damage zones with Ontario body shop rates ($110-130/hr)
- Severity multiplier: Minor 0.7x, Moderate 1.0x, Severe 1.4x, Total 1.8x
- Salvage→Rebuilt: Structural $400 + VIN $75 + Appraisal $150 = $625

### AI Damage Detection (GPT-4o Vision)
- Analyzes up to 3 photos per car, context-aware (salvage lot = look harder)
- Only flags when confidence ≥ 40%

### Ontario Fees: HST 13% + OMVIC $22 + MTO $32 + Safety $100
### Deal Score: 1-10 with BUY/WATCH/SKIP labels, factors ROI + risk

## Completed Features
- Scrapers: Cathcart Auto (rebuilders + used), Pic N Save
- v2.1 Blended calculation engine (AutoTrader + formula)
- AI damage detection from photos (GPT-4o vision)
- Dashboard with filters: source, title type, status (incl. Sold), sort by date
- Date Found column, expandable calculation breakdown in detail dialog
- About page, Settings page, Live scan indicator
- AutoTrader cache persisted to MongoDB (survives restarts)
- /api/calc-methodology, /api/recalculate, /api/fetch-comps endpoints

## Backlog
- P1: Update About page with v2.1 methodology
- P1: Gradually expand AutoTrader comp coverage (background task)
- P2: Price drop alerts
- P2: Saved/favorited listings
