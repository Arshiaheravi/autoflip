# Project: AutoFlip Intelligence

---

## North Star

**Maximize the number of profitable salvage flips identified — make every BUY signal trustworthy and every calculation accurate.**

---

## What We're Building

AutoFlip monitors Ontario salvage/used car dealers in real-time and answers one question for every listing: "If I buy this car, fix it, and resell it — how much do I make?"

It scrapes Cathcart Auto and Pic N Save every 10 minutes, estimates market value using AutoTrader.ca comps + an 8-factor depreciation formula, detects damage from photos via GPT-4o vision, and calculates flip profit with Ontario-specific fees. Every listing gets a BUY / WATCH / SKIP score.

---

## Tech Stack

- **Backend**: Python 3.14 + FastAPI + Motor (async MongoDB) + httpx + BeautifulSoup4 + Anthropic/GPT-4o API
- **Frontend**: React 19 + Tailwind CSS + shadcn/ui + Axios
- **Database**: MongoDB at localhost:27017, database `autoflip`
- **Python command**: `py` (Windows Python launcher)
- **Node command**: `C:\Program Files\nodejs\npm.cmd`

---

## Project Structure

```
backend/
  app/
    main.py                    # FastAPI app, CORS, startup/shutdown
    database.py                # MongoDB client (exports: db, client)
    routes/
      listings.py              # GET /listings, /listings/{id}, /stats
      scrape.py                # POST /scrape, /fetch-comps, GET /scrape-status, /scan-history, /recalculate, /calc-methodology
      settings.py              # GET/PUT /settings
    services/
      calculations.py          # MSRP data, depreciation, repair costs, deal scoring
      autotrader.py            # AutoTrader.ca comp scraping + blended market value
      ai_damage.py             # GPT-4o vision damage detection
    scrapers/
      cathcart.py              # Cathcart Auto scraper
      picnsave.py              # Pic N Save scraper
      runner.py                # run_full_scrape, scheduled_scrape, scrape_lock
    utils/
      parsers.py               # parse_price, parse_mileage, extract_year
  server.py                    # LEGACY monolith (do not edit — use app/ modules)
frontend/
  src/
    pages/
      Dashboard.jsx            # Main listings view with filters and stats
      AboutPage.jsx            # How it works documentation
      SettingsPage.jsx         # Scan interval + history
    components/
      shared/
        NavBar.jsx             # Top navigation with live scan status
        ListingDetail.jsx      # Modal dialog with full profit breakdown
    lib/                       # API client + utils
```

---

## Running the App

```bash
# Backend (port 8001)
cd backend && py -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Frontend (port 3000) — use PowerShell
powershell -Command "$env:PATH = 'C:\Program Files\nodejs;' + $env:PATH; Set-Location frontend; npm start"
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/listings` | All listings (filterable: source, brand_type, status, search, sort_by) |
| `GET` | `/api/listings/:id` | Single listing with full calculation breakdown |
| `GET` | `/api/stats` | Dashboard summary stats |
| `GET` | `/api/calc-methodology` | Full documentation of calculation engine |
| `POST` | `/api/scrape` | Trigger manual scrape |
| `POST` | `/api/recalculate` | Recalculate all listings with latest engine |
| `POST` | `/api/fetch-comps` | Fetch AutoTrader comps for all unique vehicles |
| `GET` | `/api/scrape-status` | Current scrape status + countdown |
| `GET` | `/api/scan-history` | Past scan log |
| `GET/PUT` | `/api/settings` | Scan interval configuration |

---

## Deal Scoring System

| Score | Label | Criteria |
|---|---|---|
| 8-10 | **BUY** | Avg profit >= $3,000. Strong flip opportunity. |
| 5-7 | **WATCH** | Avg profit $500–$3,000. Monitor for price drops. |
| 1-4 | **SKIP** | Avg profit < $500 or negative. Risk of loss. |

Adjustments: ROI > 60% = +1. ROI < -10% = -1. Worst-case loss > $2,000 = -1.

---

## Backlog — Ordered by Impact

### High Priority
- [ ] Improve AutoTrader comp matching accuracy (year +/- 1 is too loose for some models)
- [ ] Add email/SMS alert when a BUY-rated listing appears
- [ ] Track listing price history (detect price drops on WATCH listings)
- [ ] Improve AI damage detection confidence thresholds
- [ ] Add more dealers: iaai.com Canada, copart.com Canada

### Medium Priority
- [ ] Add mileage trend chart per make/model
- [ ] Export BUY listings to CSV
- [ ] Add user notes on individual listings
- [ ] Mobile-responsive improvements

### Low Priority
- [ ] Historical flip success tracking (buy → sell outcome)
- [ ] Slack/Discord webhook notifications

---

## Hard Rules

1. `server.py` is the LEGACY monolith — do NOT edit it. All new code goes in `backend/app/` modules.
2. Backend is async throughout — use `async/await` and `Motor` for all MongoDB calls.
3. Keep files under 300 lines — split into modules if larger.
4. No `print()` in backend — use `logger`.
5. React frontend: functional components and hooks only, no class components.

---

## REMOVED FEATURES — DO NOT RE-ADD

| Feature | Removed | Why |
|---------|---------|-----|
| (none yet) | — | — |

---

## Agent Technical Config

### Test Command
```bash
cd backend && py -m pytest tests/ -v
```

### Python Command
`py` (Windows)

### Git Repos
- **Project repo**: `git -C "/c/Users/arshi/OneDrive/Desktop/autoflip"`
  - Remote: `https://github.com/Arshiaheravi/autoflip.git`
  - Branch: `main`
  - Commit prefix: `agent`
- **AutoAgent repo**: `git -C "/c/Users/arshi/OneDrive/Desktop/autoflip/autoagent"`
  - Remote: `https://github.com/Arshiaheravi/autoagent.git`
  - Branch: `master`
  - Commit prefix: `meta`
- NEVER run `git add autoagent/` from project root — autoagent is tracked separately

### Codebase Rules
- All calculation logic lives in `backend/app/services/calculations.py`
- All scraping logic lives in `backend/app/scrapers/`
- Frontend API calls go through `frontend/src/lib/api.js`
