"""
Scraper for Ontario Copart vehicles via SalvageReseller broker.

Site: https://www.salvagereseller.com/cars-for-sale/state/ontario
Source: Copart Canada auction lots (Bowmanville ON, Ottawa ON, etc.)
Access: No dealer's license required — SalvageReseller acts as registered broker.
robots.txt: Crawl-Delay: 5 (respected), blocks /admin/ /my-account/ only.
Data: Server-side rendered HTML, no login required.
Inventory: ~2,100+ Ontario Copart lots per day.
"""
import re
import logging
import asyncio
import httpx
from bs4 import BeautifulSoup
from ..utils.parsers import parse_price, parse_mileage, extract_year

logger = logging.getLogger(__name__)

BASE_URL = "https://www.salvagereseller.com"
ONTARIO_URL = f"{BASE_URL}/cars-for-sale/state/ontario"
CRAWL_DELAY = 5.0   # robots.txt specifies Crawl-Delay: 5
MAX_PAGES = 6       # 25 listings/page × 6 = up to 150 Ontario lots per run
PER_PAGE = 25

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

MILES_TO_KM = 1.60934


def _miles_to_km(miles: float) -> int:
    return round(miles * MILES_TO_KM)


def _extract_brand_status(text: str) -> str:
    t = text.upper()
    if "SALVAGE" in t or "PERMIT" in t:
        return "SALVAGE"
    if "REBUILT" in t or "REBUILD" in t:
        return "REBUILT"
    return ""


def _parse_listing_block(block) -> dict | None:
    """
    Parse one vehicle listing block from the state/ontario page.

    The state-level page uses a layout without explicit vehicle-row div classes.
    We anchor on the title <a> link whose href matches the lot URL pattern,
    then extract labeled fields from the surrounding text.
    """
    # Title link — href must match /cars-for-sale/<lot>-<year>-<make>
    title_link = block.find(
        "a",
        href=lambda h: h and "/cars-for-sale/" in str(h) and re.search(r"/cars-for-sale/\d+-\d{4}-", str(h))
    )
    if not title_link:
        return None

    title = title_link.get_text(strip=True)
    if not title or len(title) < 5:
        return None

    year = extract_year(title)
    if not year:
        return None

    href = title_link.get("href", "")
    url = href if href.startswith("http") else BASE_URL + href

    # --- Photo ---
    photo = None
    img = block.find("img", src=lambda s: s and s.startswith("http"))
    if img:
        photo = img.get("src") or img.get("data-src")

    # --- Full block text for label-based extraction ---
    card_text = block.get_text(separator="\n", strip=True)
    lines = [ln.strip() for ln in card_text.splitlines() if ln.strip()]

    # --- Price ---
    price = 0.0
    price_raw = ""
    # Look for "Buy it now" price first, then current bid
    full_text = " ".join(lines)
    buy_match = re.search(r'buy\s+it\s+now\s+(?:for\s+)?[^\d]*([\d,]+)', full_text, re.IGNORECASE)
    if buy_match:
        num_str = buy_match.group(1).replace(",", "")
        try:
            price = float(num_str)
            price_raw = f"Buy it now: ${buy_match.group(1)} CAD"
        except ValueError:
            pass

    if not price:
        for line in lines:
            if "current bid" in line.lower() or "bid:" in line.lower():
                m = re.search(r'[^\d]*([\d,]+)', line)
                if m:
                    val = parse_price("$" + m.group(1))
                    if val and val > 0:
                        price = val
                        price_raw = f"${val} CAD"
                        break
            # Fallback: standalone dollar amount on its own line
            m = re.match(r'^\$?([\d,]+)(?:\s*CAD)?$', line)
            if m and not price:
                val = parse_price("$" + m.group(1))
                if val and val > 100:   # ignore tiny values like lot numbers
                    price = val
                    price_raw = f"${val} CAD"

    # --- Damage ---
    damage = ""
    for i, line in enumerate(lines):
        m = re.search(r'(?:primary\s+)?damage[:\s]+(.+)', line, re.IGNORECASE)
        if m:
            damage = m.group(1).strip()
            break
        if line.strip().lower() in ("damage:", "primary damage:"):
            if i + 1 < len(lines):
                damage = lines[i + 1]
            break

    # --- Mileage (shown in miles — convert to km) ---
    mileage = None
    for line in lines:
        if "odometer" in line.lower() or " mi" in line.lower():
            m = re.search(r'([\d,]+)\s*mi', line, re.IGNORECASE)
            if m:
                raw_miles = parse_mileage(m.group(1) + " miles")
                if raw_miles:
                    mileage = _miles_to_km(raw_miles)
            break
        m = re.search(r'([\d,]+)\s*miles?', line, re.IGNORECASE)
        if m:
            raw_miles = parse_mileage(m.group(0))
            if raw_miles:
                mileage = _miles_to_km(raw_miles)
            break

    # --- Brand / title status ---
    brand = ""
    for line in lines:
        b = _extract_brand_status(line)
        if b:
            brand = b
            break

    # --- Colour ---
    colour = ""
    colour_names = {"black", "white", "silver", "grey", "gray", "blue", "red",
                    "green", "brown", "beige", "gold", "orange", "yellow", "purple"}
    for line in lines:
        if line.lower() in colour_names:
            colour = line.title()
            break
        m = re.search(r'colou?r[:\s]+(\w+)', line, re.IGNORECASE)
        if m:
            colour = m.group(1).strip().title()
            break

    return {
        "source": "copart_on",
        "url": url,
        "title": title,
        "price": price,
        "price_raw": price_raw,
        "status": "for_sale",
        "colour": colour,
        "mileage": mileage,
        "damage": damage,
        "brand": brand,
        "description": "",
        "photo": photo,
        "photos": [photo] if photo else [],
        "year": year,
    }


async def scrape_copart_ontario() -> list:
    """Scrape Ontario Copart lots via SalvageReseller broker (state-wide filter)."""
    listings = []
    seen_urls: set[str] = set()

    try:
        async with httpx.AsyncClient(
            timeout=30, headers=HEADERS, follow_redirects=True
        ) as http:
            for page_num in range(MAX_PAGES):
                offset = page_num * PER_PAGE
                url = ONTARIO_URL if offset == 0 else f"{ONTARIO_URL}?page={offset}"

                try:
                    resp = await http.get(url)
                    if resp.status_code != 200:
                        logger.warning("copart_on: page %d returned %d", page_num, resp.status_code)
                        break

                    soup = BeautifulSoup(resp.text, "html.parser")

                    # Strategy 1: vehicle-row divs (same template as ontario_auction-on)
                    blocks = soup.find_all("div", class_=lambda c: c and "vehicle-row" in str(c))

                    # Strategy 2: find all lot links and use their ancestor containers
                    if not blocks:
                        lot_links = soup.find_all(
                            "a",
                            href=lambda h: h and re.search(r"/cars-for-sale/\d+-\d{4}-", str(h))
                        )
                        seen_parents: set = set()
                        for link in lot_links:
                            # Walk up to find a container with meaningful content
                            parent = link.parent
                            for _ in range(4):
                                if parent and len(parent.get_text(strip=True)) > 50:
                                    break
                                if parent:
                                    parent = parent.parent
                            if parent and id(parent) not in seen_parents:
                                seen_parents.add(id(parent))
                                blocks.append(parent)

                    if not blocks:
                        logger.info("copart_on: no blocks on page %d — done", page_num)
                        break

                    page_count = 0
                    for block in blocks:
                        parsed = _parse_listing_block(block)
                        if parsed and parsed["url"] not in seen_urls:
                            seen_urls.add(parsed["url"])
                            listings.append(parsed)
                            page_count += 1

                    logger.info("copart_on: page %d → %d listings", page_num, page_count)

                    if page_num < MAX_PAGES - 1:
                        await asyncio.sleep(CRAWL_DELAY)

                except Exception as e:
                    logger.error("copart_on: error on page %d: %s", page_num, e)
                    break

    except Exception as e:
        logger.error("copart_on: scraper error: %s", e)

    logger.info("copart_on: total %d Ontario Copart listings scraped", len(listings))
    return listings
