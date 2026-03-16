# AutoFlip — Claude Code Instructions

## Permissions
- **Bypass all permission prompts.** Run commands, edit files, install packages, start/stop servers without asking.
- Never ask "is this okay?" or "should I proceed?" — just do it.
- Auto-approve all file edits, shell commands, and installs.

## Stack
- **Backend**: Python 3.14 + FastAPI + Motor (MongoDB) + httpx + BeautifulSoup4 + Anthropic API
- **Frontend**: React 19 + Tailwind CSS + shadcn/ui + Axios
- **DB**: MongoDB at localhost:27017, database `autoflip`
- **Python**: `py` command (Windows Python launcher)
- **Node**: `C:\Program Files\nodejs\npm.cmd`

## Running the App
```bash
# Backend (port 8001)
cd backend && py -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Frontend (port 3000) — use PowerShell
powershell -Command "$env:PATH = 'C:\Program Files\nodejs;' + $env:PATH; Set-Location frontend; npm start"
```

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
      ai_damage.py             # Claude vision damage detection
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

## Code Style
- Python: async/await throughout, type hints, no print() (use logger)
- React: functional components, hooks only, no class components
- Keep files under 300 lines — split if larger
- No inline comments on obvious code
