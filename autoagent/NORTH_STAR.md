# North Star

---

## The Mission

**Make AutoFlip the most accurate salvage flip calculator in Ontario — every BUY signal should be a real money-making opportunity.**

---

## The Core Loop

```
SCRAPE → CALCULATE → SCORE → ALERT → FLIP → PROFIT → repeat
```

---

## The Four Pillars

### 1. Accuracy
- What it means: Every BUY listing is a genuine flip opportunity with real profit potential
- How it's measured: % of BUY listings where avg_profit >= $3,000
- Current baseline: unknown
- Target: 80%+ of BUY signals have avg_profit >= $3,000

### 2. Coverage
- What it means: Every profitable listing on Cathcart + Pic N Save is captured
- How it's measured: # of listings scraped per scan
- Current baseline: unknown
- Target: 0 missed listings

### 3. Speed
- What it means: User sees new listings within 10 minutes of them appearing online
- How it's measured: Time from listing posted → appears in AutoFlip dashboard
- Current baseline: 10 min (scrape interval)
- Target: < 5 minutes

### 4. Usability
- What it means: User can identify and act on a BUY signal in < 30 seconds
- How it's measured: # of clicks from dashboard to full breakdown
- Current baseline: 2 clicks
- Target: 1 click

---

## Success Metrics

| Metric | Current | Target | Trend |
|--------|---------|--------|-------|
| BUY signal accuracy (profit >= $3k) | unknown | 80% | — |
| Listings per scan | unknown | 100% coverage | — |
| Scan interval | 10 min | 5 min | — |
| AutoTrader comp fetch rate | unknown | 95% | — |
| AI damage detection confidence | 40% threshold | 70% threshold | — |

---

## North Star Measurement Command

```bash
cd /c/Users/arshi/OneDrive/Desktop/autoflip && curl -s http://localhost:8001/api/stats | py -c "import sys,json; d=json.load(sys.stdin); print(d.get('total_listings', 0))"
```

Target: 50+ listings tracked at all times.

---

## What the Agent Should Optimize For

Every task the agent picks should move at least one of these metrics:
1. **Accuracy** — better comps, better formula, better AI damage detection
2. **Coverage** — more dealers, better scrapers, no missed listings
3. **Usability** — faster to identify and act on BUY signals

If a task doesn't move any of these — skip it.
