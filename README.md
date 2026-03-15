

Here you go — copy this:

---

# AutoFlip Intelligence

**Real-time salvage vehicle profit calculator for Ontario, Canada.**

Automatically scrapes dealer inventory, estimates market value using AutoTrader.ca comps + a multi-factor formula, detects damage from photos with GPT-4o vision, and calculates flip profit with Ontario-specific fees.

---

## What It Does

AutoFlip monitors two Ontario salvage/used car dealers in real-time and answers one question for every listing: **"If I buy this car, fix it, and resell it — how much do I make?"**

- **Scrapes** Cathcart Auto (rebuilders + used) and Pic N Save every 10 minutes
- **Estimates market value** by blending real AutoTrader.ca comparable prices with an 8-factor depreciation formula
- **Detects damage from photos** using GPT-4o vision when the dealer doesn't list damage type
- **Calculates profit** accounting for repair costs, Ontario HST, licensing, and salvage-to-rebuilt conversion fees
- **Scores every deal** 1-10 with BUY / WATCH / SKIP labels

---

## Features

| Feature | Description |
|---|---|
| **Blended Market Value** | 60% AutoTrader.ca real comps + 40% multi-factor formula. Falls back to 100% formula when no comps available. |
| **AI Damage Detection** | Sends up to 3 photos per car to GPT-4o. Context-aware — knows salvage lot cars likely have damage. |
| **Ontario Fee Calculator** | HST 13%, OMVIC $22, MTO $32, Safety $100, Salvage-to-Rebuilt $625 |
| **Smart Filters** | Filter by source, title type (Salvage/Clean/Rebuilt), status (For Sale/Coming Soon/Sold), damage, price range |
| **Deal Scoring** | 1-10 score factoring average profit, ROI bonus, and downside risk |
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

### AI Damage Detection

When a listing has no damage description but has photos:
1. Downloads up to 3 photos from the listing
2. Sends to GPT-4o with salvage-lot context ("this car is from a salvage lot, it almost certainly has damage")
3. AI returns damage zone, severity, confidence, and specific details
4. Only applied when confidence >= 40%

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
- **Python 3.11** / **FastAPI** — async API server
- **Motor** — async MongoDB driver
- **httpx** + **BeautifulSoup4** — web scraping
- **emergentintegrations** — GPT-4o vision API (damage detection)
- **APScheduler** — background scrape scheduling

### Frontend
- **React 19** with React Router
- **Tailwind CSS** — utility-first styling
- **Shadcn/UI** — component library (Select, Dialog, Separator, etc.)
- **Axios** — API client
- **Lucide React** — icons

### Database
- **MongoDB** — listings, settings, scan history, AutoTrader comp cache

---

## Architecture

```
autoflip/
  backend/
    server.py          # All backend logic: scrapers, calc engine, API, AI detection
    requirements.txt
    .env               # MONGO_URL, EMERGENT_LLM_KEY
  frontend/
    src/
      App.js           # Dashboard, About, Settings pages
      lib/api.js       # Axios API client
      lib/utils-app.js # Formatting helpers (currency, dates, etc.)
      index.css        # Global styles, CSS variables
    .env               # REACT_APP_BACKEND_URL
```

### API Endpoints

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

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB 6+
- Emergent LLM API key (for GPT-4o damage detection)

### Backend

```bash
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env:
#   MONGO_URL=mongodb://localhost:27017
#   DB_NAME=autoflip
#   EMERGENT_LLM_KEY=your-key-here

# Run
uvicorn server:app --host 0.0.0.0 --port 8001
```

### Frontend

```bash
cd frontend
yarn install

# Configure environment
cp .env.example .env
# Edit .env:
#   REACT_APP_BACKEND_URL=http://localhost:8001

# Run
yarn start
```

The app will:
1. Start the backend on port 8001
2. Automatically trigger an initial scrape of all dealer sites
3. Begin scheduled scraping every 10 minutes (configurable in Settings)
4. Frontend available on port 3000

---

## Data Sources

| Source | URL | Type |
|---|---|---|
| Cathcart Auto (Rebuilders) | cathcartauto.com/vehicles/rebuilders | Salvage/rebuildable vehicles |
| Cathcart Auto (Used) | cathcartauto.com/vehicles/used-vehicles | Clean title used cars |
| Pic N Save | picnsave.ca/vehicles | Salvage/rebuildable vehicles |
| AutoTrader.ca | autotrader.ca (comps) | Ontario market pricing data |

---

## Environment Variables

| Variable | Location | Description |
|---|---|---|
| `MONGO_URL` | backend/.env | MongoDB connection string |
| `DB_NAME` | backend/.env | Database name |
| `EMERGENT_LLM_KEY` | backend/.env | API key for GPT-4o vision (damage detection) |
| `REACT_APP_BACKEND_URL` | frontend/.env | Backend API URL |

---

## License

MIT
