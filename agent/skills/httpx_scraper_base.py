"""
Resilient async httpx scraper with retry, User-Agent, timeout, and BeautifulSoup parse.
Use for: any new scraper that fetches HTML from auction sites.

Saved by agent on 2026-03-16.
"""

import asyncio
import logging
from bs4 import BeautifulSoup
import httpx

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


async def fetch_html(url: str, retries: int = 3, timeout: int = 20) -> BeautifulSoup | None:
    """
    Fetch URL with retries and return a BeautifulSoup object, or None on failure.
    Handles: 403, timeouts, connection errors, rate limits.
    """
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=timeout) as client:
        for attempt in range(retries):
            try:
                resp = await client.get(url)
                if resp.status_code == 429:
                    wait = 2 ** attempt * 5
                    logger.warning(f"Rate limited on {url}, waiting {wait}s")
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return BeautifulSoup(resp.text, "html.parser")
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                logger.warning(f"Fetch attempt {attempt+1}/{retries} failed for {url}: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
    logger.error(f"All {retries} attempts failed for {url}")
    return None


async def scrape_listing_page(url: str) -> dict:
    """
    Example: scrape a single listing page. Adapt selectors for each site.
    Returns a dict with standard AutoFlip keys.
    """
    soup = await fetch_html(url)
    if not soup:
        return {}

    return {
        "url": url,
        "title": (soup.select_one("h1") or soup.select_one(".listing-title") or soup.select_one("title") or "").get_text(strip=True),
        "price": None,   # parse with parse_price() from utils/parsers.py
        "photo_urls": [img["src"] for img in soup.select("img.listing-photo") if img.get("src")],
        "source": "unknown",
    }
