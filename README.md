# AutoFlip Intelligence

[![CI](https://github.com/Arshiaheravi/autoflip/actions/workflows/ci.yml/badge.svg)](https://github.com/Arshiaheravi/autoflip/actions/workflows/ci.yml)

**Real-time salvage vehicle profit calculator for Ontario, Canada.**

Automatically scrapes dealer inventory, estimates market value using AutoTrader.ca comps + a multi-factor formula, optionally detects damage from photos with Anthropic Claude vision, and calculates flip profit with Ontario-specific fees.

---

## What It Does

AutoFlip monitors Ontario salvage/used car dealers and answers one question for every listing: **"If I buy this car, fix it, and resell it — how much do I make?"**

- **Scrapes** Cathcart Auto, Pic N Save, and SalvageReseller (Copart Ontario) on a schedule
- **Estimates market value** by blending real AutoTrader.ca comparable prices with an 8-factor depreciation formula
- **Detects damage from photos** using Claude vision when the dealer doesn't list damage type (optional)
- **Calculates profit** accounting for repair costs, Ontario HST, licensing, and salvage-to-rebuilt conversion fees
- **Scores every deal** 1-10 with BUY / WATCH / SKIP labels
- **Emails deal alerts** to subscribed users (SendGrid, with SMTP fallback)

---

## Features

| Feature | Description |
|---|---|
| **Blended Market Value** | 60% AutoTrader.ca real comps + 40% multi-factor formula. Falls back to 100% formula when no comps available. |
| **AI Damage Detection** | Sends up to 3 photos per car to Anthropic Claude vision. Context-aware — knows salvage lot cars likely have damage. Optional: skipped entirely when `ANTHROPIC_API_KEY` (or the `anthropic` package) is absent. |
| **Ontario Fee Calculator** | HST 13%, OMVIC $22, MTO $32, Safety $100, Salvage-to-Rebuilt $625 |
| **Smart Filters** | Filter by source, title type (Salvage/Clean/Rebuilt), status (For Sale/Coming Soon/Sold), damage, price range |
| **Deal Scoring** | 1-10 score factoring average profit, ROI bonus, and downside risk |
| **Accounts & Billing** | JWT auth (register/login), Stripe subscriptions (monthly/yearly) for Pro alerts |
| **Live Dashboard** | Auto-refreshing with scan status indicator, countdown timer, and real-time stats |
| **Calculation Transparency** | Click any listing to see the full breakdown — every multiplier, every fee, AutoTrader comp data |

---

## Calculation Engine

### Market Value

```
Market Value = AutoTrader Comps (60%) + Formula (40%)
```

**AutoTrader.ca Comps:**
Scrapes real Ontario dealer listings for the same make/model within +/-1 model year. Extracts median asking price from active listings. Results cached 24 hours in MongoDB.

**8-Factor Formula:**
```
Formula Value = MSRP x Depreciation x Brand x BodyType x Trim x Color x Mileage x TitleStatus
```

| Factor | How It Works |
|---|---|
| **MSRP** | 100+ model database of Canadian new-car MSRPs. Fallback estimate from brand + body type. |
| **Depreciation** | Non-linear curve based on Canadian Black Book data. Year 1 = 82%, Year 5 = 48%, Year 10 = 25%. |
| **Brand Retention** | Toyota 1.18x, Lexus 1.22x, Honda 1.14x ... Fiat 0.68x. Based on historical resale data. |
| **Body Type** | Ontario demand: Trucks 1.30x, Off-road SUVs 1.20x, Compact SUVs 1.15x, Sedans 0.95x. |
| **Trim Level** | Limited/Platinum 1.25x, Sport/GT 1.15x, XLT/EX 1.10x, Base 1.05x. |
| **Color** | White +4%, Black +3%, Silver +2%. Yellow -9%, Pink -12%. Neutral = faster sale. |
| **Mileage** | 18,000 km/yr Ontario average. Low mileage +8%, high mileage -18%+. Continuous curve. |
| **Title Status** | Salvage = 55% of clean value. Rebuilt = 75%. Clean = 100%. |

### Repair Cost

```
Total Repair = (Base Cost x Severity) + Safety Inspection ($100) + Salvage Process ($625 if applicable)
```

16 damage zones mapped with Ontario body shop rates ($110-130/hr):

| Damage Zone | Estimate Range |
|---|---|
| Front / Front End | $3,000 - $6,500 |
| Rear | $2,000 - $4,500 |
| Left/Right Doors | $1,500 - $3,500 |
| Rollover | $6,000 - $16,000 |
| Fire / Flood | $4,000 - $12,000 |
| Roof | $2,500 - $6,000 |
| Undercarriage | $3,000 - $7,000 |

**Severity multiplier** (from AI analysis or listing data): Minor 0.7x, Moderate 1.0x, Severe 1.4x, Total 1.8x.

**Salvage-to-Rebuilt (Ontario):** Structural inspection $400 + VIN verification $75 + Appraisal $150 = $625 added to salvage vehicles.

### AI Damage Detection (optional)

When a listing has no damage description but has photos, and an `ANTHROPIC_API_KEY` is configured:
1. Downloads up to 3 photos from the listing
2. Sends to Claude vision with salvage-lot context ("this car is from a salvage lot, it almost certainly has damage")
3. The model returns damage zone, severity, confidence, and specific details
4. Only applied when confidence >= 40%

If the key or the `anthropic` package is not present, this step is skipped and the app falls back to listing/formula data — the feature is entirely optional.

### Profit Calculation

```
Profit = Market Value - Purchase Price - Repair Cost - Ontario Fees
```

**Ontario Fees:**
- HST: 13% of purchase price
- OMVIC: $22
- MTO Transfer: $32
- Safety Certificate: $100

### Deal Scoring

| Score | Label | Criteria |
|---|---|---|
| 8-10 | **BUY** | Average profit >= $3,000+. Strong flip opportunity. |
| 5-7 | **WATCH** | Average profit $500-$3,000. Monitor for price drops. |
| 1-4 | **SKIP** | Average profit < $500 or negative. Risk of loss. |

**Adjustments:** ROI > 60% = +1 bonus. ROI < -10% = -1 penalty. Worst case loss > $2,000 = -1 risk penalty.

---

## Tech Stack

### Backend
- **Python 3.11+** / **FastAPI** — async API server (modular app under `backend/app/`)
- **Motor** — async MongoDB driver
- **httpx** + **BeautifulSoup4** — web scraping
- **Anthropic Claude** — vision-based damage detection (optional)
- **python-jose** + **bcrypt** — JWT auth
- **Stripe** — subscription billing
- **SendGrid** — deal-alert emails (SMTP fallback)

### Frontend
- **React 19** with React Router
- **CRACO** — Create React App configuration override
- **Tailwind CSS** — utility-first styling
- **Shadcn/UI** (Radix) — component library
- **Axios** — API client
- **Lucide React** — icons

### Database
- **MongoDB** — listings, users, settings, scan history, AutoTrader comp cache

---

## Architecture

```
autoflip/
  backend/
    app/
      main.py                # FastAPI app, CORS, startup/scheduler
      database.py            # Motor client + db handle
      routes/                # listings, scrape, settings, auth, stripe
      services/              # calculations, autotrader, ai_damage, auth, email_alerts
      scrapers/              # cathcart, picnsave, salvagereseller, copart_ontario, runner
      utils/                 # parsers
    tests/                   # 261 pytest tests
    requirements.txt
    .env.example             # MONGO_URL, DB_NAME, ANTHROPIC_API_KEY, STRIPE_*, ...
  frontend/
    src/                     # React app (Dashboard, About, Settings, auth)
    .env.example             # REACT_APP_BACKEND_URL
```

### API Endpoints

All endpoints are mounted under `/api`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/listings` | All listings (filterable: brand_type, status, search, sort_by) |
| `GET` | `/api/listings/{id}` | Single listing with full calculation breakdown |
| `GET` | `/api/listings/{id}/price-history` | Price history for a listing |
| `GET` | `/api/stats` | Dashboard summary stats |
| `GET` | `/api/calc-methodology` | Full documentation of calculation engine |
| `POST` | `/api/scrape` | Trigger manual scrape |
| `POST` | `/api/recalculate` | Recalculate all listings with latest engine |
| `POST` | `/api/fetch-comps` | Fetch AutoTrader comps for all unique vehicles |
| `GET` | `/api/scrape-status` | Current scrape status + countdown |
| `GET` | `/api/scan-history` | Past scan log |
| `GET/PUT` | `/api/settings` | Scan interval configuration |
| `POST` | `/api/auth/register` `/login` `/logout` `/subscribe` | Account management |
| `GET` | `/api/auth/me` | Current user |
| `POST` | `/api/stripe/create-checkout-session` `/webhook` | Billing |

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- MongoDB 6+
- (Optional) Anthropic API key for Claude vision damage detection

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # or requirements-dev.txt for tests

# Configure environment
cp .env.example .env
# Edit .env — at minimum:
#   MONGO_URL=mongodb://localhost:27017
#   DB_NAME=autoflip
#   JWT_SECRET_KEY=<a long random string>
#   ANTHROPIC_API_KEY=  (optional)

# Run
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Run the test suite:

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

### Frontend

```bash
cd frontend
npm install

# Configure environment
cp .env.example .env
# Edit .env:
#   REACT_APP_BACKEND_URL=http://localhost:8001

# Run
npm start
```

The app will:
1. Start the backend on port 8001
2. Automatically trigger an initial scrape when the listings collection is empty
3. Begin scheduled scraping (interval configurable in Settings)
4. Serve the frontend on port 3000

---

## Data Sources

| Source | URL | Type |
|---|---|---|
| Cathcart Auto | cathcartauto.com | Salvage/rebuildable + used vehicles |
| Pic N Save | picnsave.ca/rebuildable-cars | Salvage/rebuildable vehicles |
| SalvageReseller (Copart Ontario) | salvagereseller.com | Salvage/auction vehicles |
| AutoTrader.ca | autotrader.ca (comps) | Ontario market pricing data |

---

## Environment Variables

| Variable | Location | Description |
|---|---|---|
| `MONGO_URL` | backend/.env | MongoDB connection string |
| `DB_NAME` | backend/.env | Database name |
| `JWT_SECRET_KEY` | backend/.env | Secret used to sign JWTs |
| `CORS_ORIGINS` | backend/.env | Comma-separated allowlist of frontend origins |
| `ANTHROPIC_API_KEY` | backend/.env | API key for Claude vision damage detection (optional) |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` / `STRIPE_PRICE_*` | backend/.env | Stripe billing (optional) |
| `SENDGRID_API_KEY` / `SMTP_*` | backend/.env | Deal-alert email delivery (optional) |
| `REACT_APP_BACKEND_URL` | frontend/.env | Backend API URL |

See `backend/.env.example` and `frontend/.env.example` for the full list.

---

## License

MIT — see [LICENSE](LICENSE).
