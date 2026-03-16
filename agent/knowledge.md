# Agent Knowledge Base

This file is written and updated by the agent itself after every session.
It captures patterns, lessons, discoveries, and best practices that persist across sessions.
The agent reads this at the start of every session to avoid repeating mistakes.

---

## Project Patterns

- Backend entry point: `backend/app/main.py` — runs as `py -m uvicorn app.main:app --port 8001`
- All routes use relative imports: `from ..database import db`, `from ..services.calculations import ...`
- MongoDB collections: `listings`, `scan_history`, `autotrader_cache`, `settings`
- Scraper pattern: each scraper returns list of dicts with keys: `title`, `price`, `damage`, `brand_status`, `colour`, `mileage`, `photo_urls`, `source`, `url`
- Calculations pipeline: `estimate_market_value_blended()` → `get_repair_range()` → `calculate_ontario_fees()` → `calc_deal_score()`

## Validation Commands

```bash
# Backend syntax check (run after any .py edit)
py -c "import sys; sys.path.insert(0,'backend'); from app.main import app; print('OK')"

# Run all tests
py -m pytest backend/tests/ -x -q --tb=short

# Compile-check a single file
py -m py_compile backend/app/routes/scrape.py
```

## Known Issues / Watch Out For

- Windows console: use `py -X utf8` to avoid UnicodeEncodeError
- httpx requests to auction sites need User-Agent headers or they return 403
- Motor (async MongoDB) — never use sync pymongo calls inside async functions
- BeautifulSoup: always specify parser (`"html.parser"`) to avoid warnings
- Frontend `@/` alias maps to `frontend/src/` (configured in jsconfig.json + craco.config.js)

## Lessons Learned

_(agent appends here after each session)_
