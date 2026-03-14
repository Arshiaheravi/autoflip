# AutoFlip Intelligence - Product Requirements Document

## Original Problem Statement
Build a full-stack web application called "AutoFlip Intelligence" — a real-time car investment monitoring and profit analysis platform for an individual Ontario car investor. The app monitors three specific websites 24/7, detects new vehicle listings, downloads all listing photos, runs AI-powered damage analysis, calculates profit potential automatically, scores each deal from 0–100, and delivers instant Telegram/SMS/email notifications.

## Architecture
- **Frontend**: React 18 + TailwindCSS + Shadcn UI + Recharts + Zustand
- **Backend**: FastAPI (Python) + MongoDB (Motor async driver)
- **AI Integration**: Claude Sonnet via Emergent SDK (for photo damage analysis)
- **Notifications**: Telegram Bot API, Twilio SMS, SendGrid Email (stubs ready, needs API keys)
- **Real-time**: WebSocket for live listing updates

## User Personas
- Individual Ontario car investor who buys salvage/rebuild vehicles for profit
- Mixed strategy: quick flips (30-day) + seasonal holds (buy winter, sell spring/fall)

## Core Requirements (Static)
1. Monitor 3 car listing websites (Cathcart Rebuilders, Cathcart Used, Pic N Save)
2. AI-powered photo damage analysis
3. Automated profit calculation with Ontario fees
4. Deal scoring (0-100) with BUY NOW/WATCH/SKIP recommendations
5. Multi-channel notifications (Telegram, SMS, Email)
6. Dashboard with 5 pages: Live Feed, Watchlist, Portfolio, Market Intel, Settings

## What's Been Implemented (2026-03-14)
- [x] Complete FastAPI backend with all CRUD endpoints
- [x] MongoDB database with 12 seeded demo listings from 3 sources
- [x] Profit calculation engine (Ontario fees, repair costs, seasonal analysis)
- [x] Deal scoring algorithm (0-100 weighted: profit 35, demand 25, repair 20, timing 20)
- [x] WebSocket endpoint for real-time updates
- [x] AI photo analysis endpoint (Claude Sonnet via Emergent SDK)
- [x] React frontend with 5 pages: Live Feed, Watchlist, Portfolio, Market Intel, Settings
- [x] Dark theme with Barlow Condensed/Manrope/JetBrains Mono typography
- [x] Listing cards with deal scores, profit info, filters, sorting
- [x] Watchlist with notes and tracking
- [x] Portfolio tracker with P&L chart and CSV export
- [x] Market intelligence with demand heatmap and seasonal trends
- [x] Settings page with all notification and calculation configurations
- [x] Notification stubs (Telegram, Twilio, SendGrid) - ready for API keys

## Testing Results
- Backend: 97.4% (38/39 tests passed)
- Frontend: 100% (all core functionality working)

## Prioritized Backlog

### P0 (Critical - Next Phase)
- Live web scraping: RSS monitor (30s polling) + page scraper (90s backup)
- Real-time detection from Cathcart Auto and Pic N Save
- Photo download pipeline from actual listings
- Connect AI analysis to real downloaded photos

### P1 (Important)
- Telegram/SMS/Email notifications (user needs to provide API keys)
- COMING SOON -> FOR SALE status change monitoring
- Price TBD -> real price monitoring
- Price drop monitoring on watched listings
- Daily email digest at 7 AM

### P2 (Nice to have)
- Real market data scraping (AutoTrader, Kijiji, CarGurus)
- Stale listing tracker with orange/red badges
- Side-by-side comparison on Watchlist
- Export portfolio to PDF
- First listing of the day bonus alert
