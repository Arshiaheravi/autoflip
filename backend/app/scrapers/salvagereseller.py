"""
Scraper for SalvageReseller.com — Ontario salvage/rebuild vehicle auctions.

Site: https://www.salvagereseller.com/cars-for-sale/location/ontario_auction-on
robots.txt: Crawl-Delay: 5 (respected), blocks /admin/ /my-account/ only.
Data: Server-side rendered HTML, no login required.
"""
import re
import logging
import asyncio
import httpx
from bs4 import BeautifulSoup
from ..utils.parsers import parse_price, parse_mileage, extract_year

logger = logging.getLogger(__name__)

BASE_URL = "https://www.salvagereseller.com"
ONTARIO_URL = f"{BASE_URL}/cars-for-sale/location/ontario_auction-on"
CRAWL_DELAY = 5.0   # robots.txt specifies Crawl-Delay: 5
MAX_PAGES = 3       # 25 listings/page × 3 = up to 75 Ontario listings per run
PER_PAGE = 25

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Miles to km conversion constant
MILES_TO_KM = 1.60934


def _miles_to_km(miles: float) -> int:
    return round(miles * MILES_TO_KM)


def _extract_brand_status(text: str) -> str:
    """Map title/brand text to SALVAGE or REBUILT."""
    t = text.upper()
    if "SALVAGE" in t or "PERMIT" in t:
        return "SALVAGE"
    if "REBUILT" in t or "REBUILD" in t:
        return "REBUILT"
    return ""


def _parse_listing_card(row) -> dict | None:
    """Extract all available fields from a vehicle-row div."""
    # Title and URL
    title_link = row.find("a", class_=lambda c: c and "vehicle-model" in str(c))
    if not title_link:
        # Try any link with a vehicle slug pattern
        title_link = row.find("a", href=lambda h: h and "/cars-for-sale/" in str(h) and "-20" in str(h))
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
    if not url or "/cars-for-sale/" not in url:
        return None

    # Price — prefer "Buy It Now" over current bid (bid can be $0)
    price = 0.0
    price_raw = ""
    bids_section = row.find("div", class_=lambda c: c and "bids" in str(c))
    if bids_section:
        # Look for "Buy it now" price first
        buy_now_text = bids_section.get_text(separator=" ", strip=True)
        buy_match = re.search(r'Buy\s+it\s+now\s+for\s+[^\d]*([\d,]+)', buy_now_text, re.IGNORECASE)
        if buy_match:
            num_str = buy_match.group(1).replace(",", "")
            try:
                price = float(num_str)
            except ValueError:
                price = 0.0
            price_raw = f"Buy it now: ${buy_match.group(1)} CAD"

        if not price:
            # Current bid
            all_spans = bids_section.find_all("span")
            for span in all_spans:
                cls = " ".join(span.get("class", []))
                if "display-4" in cls or "font-weight-bolder" in cls:
                    val = parse_price(span.get_text(strip=True))
                    if val and val > 0:
                        price = val
                        price_raw = f"${val} CAD"
                        break

    # Thumbnail photo
    photo = None
    img = row.find("img", src=lambda s: s and ("salvagereseller" in s or "images." in s))
    if img:
        photo = img.get("src") or img.get("data-src")
    if not photo:
        img = row.find("img", src=lambda s: s and s.startswith("http"))
        if img:
            photo = img.get("src")

    # Full card text for field extraction
    card_text = row.get_text(separator="\n", strip=True)
    lines = [ln.strip() for ln in card_text.splitlines() if ln.strip()]

    # Damage (primary) — inline "Primary Damage: Front end" or next-line label
    damage = ""
    for i, line in enumerate(lines):
        m = re.search(r'primary\s+damage[:\s]+(.+)', line, re.IGNORECASE)
        if m:
            damage = m.group(1).strip()
            break
        if line.strip().lower() in ("primary damage:", "damage:"):
            if i + 1 < len(lines):
                damage = lines[i + 1]
            break

    # Mileage (odometer in miles — convert to km)
    mileage = None
    for line in lines:
        if "odometer" in line.lower() or "mi)" in line.lower():
            # Inline: "90,784 mi (Actual)"
            m = re.search(r'([\d,]+)\s*mi', line, re.IGNORECASE)
            if m:
                raw_miles = parse_mileage(m.group(1) + " miles")
                if raw_miles:
                    mileage = _miles_to_km(raw_miles)
            break
        if re.search(r'([\d,]+)\s*miles?', line, re.IGNORECASE):
            m = re.search(r'([\d,]+)\s*miles?', line, re.IGNORECASE)
            raw_miles = parse_mileage(m.group(0))
            if raw_miles:
                mileage = _miles_to_km(raw_miles)
            break

    # Brand / title status
    brand = ""
    for line in lines:
        b = _extract_brand_status(line)
        if b:
            brand = b
            break

    # Colour
    colour = ""
    for line in lines:
        if line.lower() in ("black", "white", "silver", "grey", "gray", "blue", "red",
                             "green", "brown", "beige", "gold", "orange", "yellow", "purple"):
            colour = line.title()
            break
        m = re.search(r'colou?r[:\s]+(\w+)', line, re.IGNORECASE)
        if m:
            colour = m.group(1).strip().title()
            break

    return {
        "source": "salvagereseller",
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


async def scrape_salvagereseller() -> list:
    """Scrape Ontario salvage vehicle listings from SalvageReseller.com."""
    listings = []
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
                        logger.warning("salvagereseller: page %d returned %d", page_num, resp.status_code)
                        break

                    soup = BeautifulSoup(resp.text, "html.parser")
                    rows = soup.find_all("div", class_=lambda c: c and "vehicle-row" in str(c))

                    if not rows:
                        logger.info("salvagereseller: no rows on page %d — done", page_num)
                        break

                    page_count = 0
                    for row in rows:
                        parsed = _parse_listing_card(row)
                        if parsed:
                            listings.append(parsed)
                            page_count += 1

                    logger.info("salvagereseller: page %d → %d listings", page_num, page_count)

                    # Respect crawl-delay before next page
                    if page_num < MAX_PAGES - 1:
                        await asyncio.sleep(CRAWL_DELAY)

                except Exception as e:
                    logger.error("salvagereseller: error on page %d: %s", page_num, e)
                    break

    except Exception as e:
        logger.error("salvagereseller: scraper error: %s", e)

    logger.info("salvagereseller: total %d Ontario listings scraped", len(listings))
    return listings
