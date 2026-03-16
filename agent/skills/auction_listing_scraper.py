"""
skill: auction_listing_scraper
description: Paginated auction site scraper with crawl-delay respect, miles-to-km
conversion, buy-now/bid price extraction, brand status mapping (SALVAGE/REBUILT).
Used for SalvageReseller.com — adapt for similar sites.

Key patterns:
- Respect robots.txt Crawl-Delay with asyncio.sleep between pages
- parse_price() requires "$" prefix — use float(str.replace(",","")) for raw numbers
- Use [^\\d]* instead of \\$? in regex (Python 3.14 compat)
- Mileage in miles → km: miles * 1.60934
- Brand: "PERMIT SALVAGE" or "SALVAGE" → "SALVAGE", "REBUILT" → "REBUILT"
- Auction bid can be $0 — prefer "Buy It Now" price; if $0, let runner handle
"""

import re
import asyncio
import httpx
from bs4 import BeautifulSoup

MILES_TO_KM = 1.60934
CRAWL_DELAY = 5.0  # from robots.txt Crawl-Delay

def miles_to_km(miles: float) -> int:
    return round(miles * MILES_TO_KM)

def extract_brand_status(text: str) -> str:
    t = text.upper()
    if "SALVAGE" in t or "PERMIT" in t:
        return "SALVAGE"
    if "REBUILT" in t or "REBUILD" in t:
        return "REBUILT"
    return ""

def parse_buy_now_price(text: str) -> float:
    """Extract price from 'Buy it now for $12,000 CAD' style text."""
    # Use [^\\d]* not \\$? for Python 3.14 regex compat
    m = re.search(r'Buy\s+it\s+now\s+for\s+[^\d]*([\d,]+)', text, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            pass
    return 0.0

async def scrape_paginated_auction(base_url: str, source_name: str,
                                    max_pages: int = 3, per_page: int = 25) -> list:
    """
    Generic paginated auction scraper.
    Assumes ?page=OFFSET pagination with vehicle-row divs.
    """
    listings = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0",
        "Accept": "text/html,application/xhtml+xml",
    }
    async with httpx.AsyncClient(timeout=30, headers=headers, follow_redirects=True) as http:
        for page_num in range(max_pages):
            offset = page_num * per_page
            url = base_url if offset == 0 else f"{base_url}?page={offset}"
            resp = await http.get(url)
            if resp.status_code != 200:
                break
            soup = BeautifulSoup(resp.text, "html.parser")
            rows = soup.find_all("div", class_=lambda c: c and "vehicle-row" in str(c))
            if not rows:
                break
            for row in rows:
                # Parse each row — implement site-specific logic
                pass
            if page_num < max_pages - 1:
                await asyncio.sleep(CRAWL_DELAY)
    return listings
