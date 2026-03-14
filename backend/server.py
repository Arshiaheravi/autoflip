from fastapi import FastAPI, APIRouter, Query, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
import asyncio
import hashlib
from pathlib import Path
from typing import List, Optional
import uuid
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─── Scraper imports ───
import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ─── Repair cost map ───
REPAIR_COST_MAP = {
    "LEFT REAR": [1800, 3500],
    "RIGHT REAR": [1800, 3500],
    "REAR": [1800, 3500],
    "FRONT": [2500, 5500],
    "RIGHT FRONT": [2500, 5500],
    "LEFT FRONT": [2500, 5500],
    "FRONT END": [2500, 5500],
    "RIGHT DOORS": [1500, 3000],
    "LEFT DOORS": [1500, 3000],
    "DOORS": [1500, 3000],
    "ROLLOVER": [5000, 14000],
    "FIRE": [3500, 10000],
    "FLOOD": [3500, 10000],
}
DEFAULT_REPAIR = [500, 1500]  # Clean/no damage - minor reconditioning
SAFETY_INSPECTION = 100

def get_repair_range(damage_text: str) -> list:
    if not damage_text or damage_text.strip() == "" or damage_text.upper() == "NONE":
        return [DEFAULT_REPAIR[0] + SAFETY_INSPECTION, DEFAULT_REPAIR[1] + SAFETY_INSPECTION]
    d = damage_text.upper().strip()
    # Direct match first
    for key, val in REPAIR_COST_MAP.items():
        if key in d:
            return [val[0] + SAFETY_INSPECTION, val[1] + SAFETY_INSPECTION]
    # Fuzzy matches
    if "ROLL" in d:  # ROLLED, ROLLOVER, ROLL OVER
        return [5000 + SAFETY_INSPECTION, 14000 + SAFETY_INSPECTION]
    if "FIRE" in d or "BURN" in d:
        return [3500 + SAFETY_INSPECTION, 10000 + SAFETY_INSPECTION]
    if "FLOOD" in d or "WATER" in d:
        return [3500 + SAFETY_INSPECTION, 10000 + SAFETY_INSPECTION]
    if "HIT" in d or "IMPACT" in d or "COLLISION" in d:
        return [2000 + SAFETY_INSPECTION, 5000 + SAFETY_INSPECTION]
    if "RUST" in d:
        return [1500 + SAFETY_INSPECTION, 4000 + SAFETY_INSPECTION]
    if "REAR" in d:
        return [1800 + SAFETY_INSPECTION, 3500 + SAFETY_INSPECTION]
    if "SIDE" in d or "DOOR" in d:
        return [1500 + SAFETY_INSPECTION, 3000 + SAFETY_INSPECTION]
    # Unknown damage - moderate estimate
    return [2000 + SAFETY_INSPECTION, 5000 + SAFETY_INSPECTION]

def calculate_ontario_fees(purchase_price: float) -> float:
    return purchase_price * 0.13 + 154  # HST + OMVIC $22 + MTO $32 + Safety $100

def calc_deal_score(best_profit: float, worst_profit: float) -> tuple:
    if worst_profit < 0:
        score = 2 if best_profit > 0 else 1
    elif best_profit > 4000:
        score = 10 if best_profit > 5000 else 9
    elif best_profit >= 2500:
        score = 8 if best_profit > 3200 else 7
    elif best_profit >= 1000:
        score = 6 if best_profit > 1750 else 5
    elif best_profit >= 0:
        score = 4 if best_profit > 500 else 3
    else:
        score = 1

    if score >= 8:
        label = "BUY"
    elif score >= 5:
        label = "WATCH"
    else:
        label = "SKIP"
    return score, label

def parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    text_lower = text.lower()
    if "####" in text or "on sale" in text_lower or "call" in text_lower:
        return None
    # Isolate the price portion (before "AS IS", "PLUS HST", etc.)
    price_part = text
    for split_word in ["AS IS", "PLUS", "Plus", "plus"]:
        if split_word in price_part:
            price_part = price_part.split(split_word)[0]
    price_part = price_part.strip()
    # Handle European format like "$29.995.00" -> 29995
    # Count dots: if more than one dot, treat dots as thousand separators
    dollar_match = re.search(r'\$([\d.,]+)', price_part)
    if dollar_match:
        num_str = dollar_match.group(1)
        dot_count = num_str.count('.')
        if dot_count > 1:
            # Format like "$29.995.00" - dots as thousands, last group is cents
            parts = num_str.split('.')
            if len(parts[-1]) == 2:
                # Last part is cents
                whole = ''.join(parts[:-1])
                num_str = whole + '.' + parts[-1]
            else:
                num_str = num_str.replace('.', '').replace(',', '')
        elif dot_count == 1:
            num_str = num_str.replace(',', '')
        else:
            num_str = num_str.replace(',', '')
        try:
            val = float(num_str)
            if val > 100:
                return val
        except ValueError:
            pass
    return None

def parse_mileage(text: str) -> Optional[int]:
    if not text:
        return None
    clean = text.replace(",", "").replace(" ", "").replace("km", "").replace("KM", "")
    match = re.search(r'(\d+)', clean)
    if match:
        return int(match.group(1))
    return None

# ─── Market Value Estimation ───
# Since AutoTrader/Kijiji have anti-bot protection, we use a model-based estimation
# that factors in year depreciation + vehicle type + Ontario market patterns
VEHICLE_BASE_VALUES = {
    "toyota": 1.15, "honda": 1.12, "lexus": 1.20, "subaru": 1.10,
    "mazda": 1.05, "hyundai": 0.95, "kia": 0.93, "nissan": 0.92,
    "ford": 0.95, "chevrolet": 0.88, "gmc": 0.95, "dodge": 0.85, "ram": 0.95,
    "jeep": 1.05, "bmw": 1.00, "mercedes": 1.05, "audi": 1.00,
    "volkswagen": 0.90, "volkswagon": 0.90, "acura": 1.05, "cadillac": 0.90,
    "tesla": 1.10, "fiat": 0.70, "jaguar": 0.75, "yamaha": 0.85,
}

def estimate_market_value(title: str, year: int, mileage: int = None) -> Optional[float]:
    """Estimate Ontario market value based on vehicle attributes"""
    current_year = datetime.now().year
    age = current_year - year
    if age < 0:
        age = 0

    # Base value by age tier
    if age <= 1:
        base = 38000
    elif age <= 3:
        base = 28000
    elif age <= 5:
        base = 20000
    elif age <= 8:
        base = 14000
    elif age <= 12:
        base = 9000
    elif age <= 15:
        base = 5500
    else:
        base = 3500

    # Make multiplier
    title_lower = title.lower()
    make_mult = 1.0
    for make, mult in VEHICLE_BASE_VALUES.items():
        if make in title_lower:
            make_mult = mult
            break

    # Type multiplier
    type_mult = 1.0
    if any(k in title_lower for k in ["f150", "f-150", "sierra", "silverado", "ram", "tundra"]):
        type_mult = 1.25  # Trucks hold value
    elif any(k in title_lower for k in ["rav4", "rav-4", "crv", "cr-v", "forester", "rogue", "escape", "equinox", "sportage", "tucson", "cx-5", "cx5"]):
        type_mult = 1.15  # SUVs/CUVs popular
    elif any(k in title_lower for k in ["wrangler", "4runner", "land cruiser", "landcruiser"]):
        type_mult = 1.35  # Off-road premium
    elif any(k in title_lower for k in ["prius", "hybrid", "electric", "ev"]):
        type_mult = 1.10
    elif any(k in title_lower for k in ["sienna", "odyssey", "promaster", "transit", "van"]):
        type_mult = 1.05
    elif any(k in title_lower for k in ["sedan", "civic", "corolla", "sentra", "accent", "forte", "elantra"]):
        type_mult = 0.95

    # Trim multiplier
    trim_mult = 1.0
    if any(k in title_lower for k in ["limited", "platinum", "calligraphy", "ultimate"]):
        trim_mult = 1.20
    elif any(k in title_lower for k in ["lariat", "sport", "gt", "rs", "performance"]):
        trim_mult = 1.10
    elif any(k in title_lower for k in ["xlt", "ex", "touring", "preferred"]):
        trim_mult = 1.05

    value = base * make_mult * type_mult * trim_mult

    # Mileage adjustment
    if mileage and mileage > 0:
        avg_km_per_year = 18000
        expected_km = age * avg_km_per_year
        if expected_km == 0:
            expected_km = 18000
        km_ratio = mileage / expected_km
        if km_ratio > 1.3:
            value *= 0.88  # High mileage penalty
        elif km_ratio > 1.1:
            value *= 0.94
        elif km_ratio < 0.7:
            value *= 1.06  # Low mileage premium

    return round(value, 0)

def extract_year(title: str) -> Optional[int]:
    match = re.search(r'(19|20)\d{2}', title)
    if match:
        return int(match.group(0))
    return None

# ─── Scrapers ───
async def scrape_cathcart(page_url: str, source_name: str) -> list:
    """Scrape Cathcart Auto listing page and detail pages"""
    listings = []
    try:
        async with httpx.AsyncClient(timeout=30, headers=HEADERS, follow_redirects=True) as http:
            resp = await http.get(page_url)
            if resp.status_code != 200:
                logger.error(f"Failed to fetch {page_url}: {resp.status_code}")
                return []
            soup = BeautifulSoup(resp.text, 'html.parser')

            # Find all inventory links
            inv_links = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/inventory/' in href and href.startswith('http'):
                    inv_links.add(href)

            # Parse listing cards from main page
            # Each listing is in a div with h1 (title), h3 (price), h3 (status)
            h1_tags = soup.find_all('h1')
            card_data = {}

            for h1 in h1_tags:
                title = h1.get_text(strip=True)
                if not title or len(title) < 5:
                    continue
                year = extract_year(title)
                if not year:
                    continue

                # Find associated link
                parent = h1.parent
                link_el = None
                # Look up to 5 parents for a link
                search = h1
                for _ in range(8):
                    search = search.parent
                    if not search:
                        break
                    link_el = search.find('a', href=lambda h: h and '/inventory/' in h)
                    if link_el:
                        break

                url = link_el['href'] if link_el else None
                if not url:
                    continue

                # Find h3 siblings for price and status
                container = h1.parent
                for _ in range(5):
                    if not container:
                        break
                    h3s = container.find_all('h3')
                    if h3s:
                        break
                    container = container.parent

                price_text = ""
                status = "for_sale"
                if h3s:
                    for h3 in h3s:
                        h3_text = h3.get_text(strip=True)
                        if '$' in h3_text or 'AS IS' in h3_text.upper() or 'PLUS HST' in h3_text.upper():
                            price_text = h3_text
                        elif 'COMING SOON' in h3_text.upper():
                            status = "coming_soon"
                        elif 'FOR SALE' in h3_text.upper():
                            status = "for_sale"
                        elif 'SOLD' in h3_text.upper():
                            status = "sold"

                # Find thumbnail image
                photo = None
                if link_el:
                    img = link_el.find('img', src=lambda s: s and 'wp-content/uploads' in s and 'logo' not in s)
                    if img:
                        photo = img['src']
                if not photo and container:
                    img = container.find('img', src=lambda s: s and 'wp-content/uploads' in s and 'logo' not in s)
                    if img:
                        photo = img['src']

                card_data[url] = {
                    "title": title,
                    "price_text": price_text,
                    "status": status,
                    "photo": photo,
                    "url": url,
                }

            # Now fetch detail pages for each listing
            for url, card in card_data.items():
                await asyncio.sleep(0.5)  # Rate limit
                try:
                    detail_resp = await http.get(url)
                    if detail_resp.status_code != 200:
                        continue
                    detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')

                    # Extract fields from strong tags
                    colour = ""
                    mileage_text = ""
                    damage = ""
                    brand = ""
                    description = ""

                    for strong in detail_soup.find_all('strong'):
                        label = strong.get_text(strip=True).lower().rstrip(':')
                        # Get text after strong tag
                        sibling_text = ""
                        for sib in strong.next_siblings:
                            if hasattr(sib, 'get_text'):
                                t = sib.get_text(strip=True)
                            else:
                                t = str(sib).strip()
                            if t:
                                sibling_text = t
                                break

                        if 'colour' in label:
                            colour = sibling_text
                        elif 'mileage' in label:
                            mileage_text = sibling_text
                        elif 'damage' in label:
                            damage = sibling_text
                        elif 'brand' in label:
                            brand = sibling_text
                        elif 'description' in label:
                            # Get all remaining text
                            parent_text = strong.parent.get_text(strip=True) if strong.parent else ""
                            desc_match = re.split(r'description:', parent_text, flags=re.IGNORECASE)
                            if len(desc_match) > 1:
                                description = desc_match[1].strip()[:500]

                    # Get all photos from detail page
                    photos = []
                    for img in detail_soup.find_all('img', src=True):
                        src = img['src']
                        if 'wp-content/uploads' in src and 'logo' not in src.lower():
                            if src not in photos:
                                photos.append(src)

                    price = parse_price(card["price_text"])
                    mileage = parse_mileage(mileage_text)
                    year = extract_year(card["title"])

                    listing = {
                        "source": source_name,
                        "url": url,
                        "title": card["title"],
                        "price": price,
                        "price_raw": card["price_text"],
                        "status": card["status"],
                        "colour": colour,
                        "mileage": mileage,
                        "damage": damage,
                        "brand": brand,
                        "description": description,
                        "photo": photos[0] if photos else card.get("photo"),
                        "photos": photos[:5],
                        "year": year,
                    }
                    listings.append(listing)
                    logger.info(f"  Scraped: {card['title']} - ${price}")

                except Exception as e:
                    logger.warning(f"  Failed detail page {url}: {e}")
                    # Still add with card-level data
                    price = parse_price(card["price_text"])
                    year = extract_year(card["title"])
                    listings.append({
                        "source": source_name, "url": url, "title": card["title"],
                        "price": price, "price_raw": card["price_text"], "status": card["status"],
                        "colour": "", "mileage": None, "damage": "", "brand": "",
                        "description": "", "photo": card.get("photo"), "photos": [],
                        "year": year,
                    })

    except Exception as e:
        logger.error(f"Scraper error for {page_url}: {e}")
    return listings


async def scrape_picnsave() -> list:
    """Scrape Pic N Save rebuildable cars (all pages)"""
    listings = []
    page = 1
    max_pages = 10

    try:
        async with httpx.AsyncClient(timeout=30, headers=HEADERS, follow_redirects=True) as http:
            while page <= max_pages:
                url = "https://picnsave.ca/rebuildable-cars/"
                if page > 1:
                    url += f"page/{page}/"

                resp = await http.get(url)
                if resp.status_code != 200:
                    break

                soup = BeautifulSoup(resp.text, 'html.parser')
                products = soup.find_all('li', class_=lambda c: c and 'product' in str(c))

                if not products:
                    break

                for prod in products:
                    title_el = prod.find('h2')
                    title = title_el.get_text(strip=True) if title_el else ""
                    if not title:
                        continue

                    # Price
                    price_el = prod.find(class_='woocommerce-Price-amount') or prod.find(class_='price')
                    price_text = price_el.get_text(strip=True) if price_el else ""
                    price = parse_price(price_text)

                    # Link
                    link_el = prod.find('a', href=True)
                    detail_url = link_el['href'] if link_el else ""

                    # Photo
                    img_el = prod.find('img', src=True)
                    photo = img_el.get('src', '') if img_el else ""
                    if photo and 'placeholder' in photo.lower():
                        photo = ""

                    # Get brand and mileage from card text
                    all_text = prod.get_text(separator='|', strip=True)
                    brand = ""
                    mileage_text = ""
                    for part in all_text.split('|'):
                        part = part.strip()
                        if part.lower().startswith('brand:'):
                            brand = part.split(':', 1)[1].strip()
                        elif part.lower().startswith('mileage:'):
                            mileage_text = part.split(':', 1)[1].strip()

                    mileage = parse_mileage(mileage_text)
                    year = extract_year(title)

                    # Fetch detail page for damage info
                    damage = ""
                    description = ""
                    detail_photos = []
                    if detail_url:
                        await asyncio.sleep(0.5)
                        try:
                            detail_resp = await http.get(detail_url)
                            if detail_resp.status_code == 200:
                                dsoup = BeautifulSoup(detail_resp.text, 'html.parser')
                                # Look for damage info in product description
                                desc_el = dsoup.find(class_='woocommerce-product-details__short-description') or dsoup.find(class_='product_meta')
                                if desc_el:
                                    desc_text = desc_el.get_text(strip=True)
                                    description = desc_text[:500]
                                    # Try to extract damage from description
                                    for line in desc_text.split('\n'):
                                        ll = line.lower().strip()
                                        if 'damage' in ll:
                                            damage = line.strip()

                                # Check additional info sections
                                for el in dsoup.find_all(['p', 'div', 'span']):
                                    text = el.get_text(strip=True)
                                    if 'damage' in text.lower() and len(text) < 100:
                                        damage = text.split(':')[-1].strip() if ':' in text else text

                                # Get photos
                                for img in dsoup.find_all('img', src=True):
                                    src = img['src']
                                    if 'wp-content/uploads' in src and 'placeholder' not in src.lower() and src not in detail_photos:
                                        detail_photos.append(src)
                        except Exception as e:
                            logger.warning(f"  PicNSave detail failed {detail_url}: {e}")

                    listing = {
                        "source": "picnsave",
                        "url": detail_url,
                        "title": title,
                        "price": price,
                        "price_raw": price_text,
                        "status": "for_sale",
                        "colour": "",
                        "mileage": mileage,
                        "damage": damage,
                        "brand": brand,
                        "description": description,
                        "photo": detail_photos[0] if detail_photos else photo,
                        "photos": detail_photos[:5] if detail_photos else ([photo] if photo else []),
                        "year": year,
                    }
                    listings.append(listing)
                    logger.info(f"  Scraped: {title} - ${price}")

                # Check for next page
                next_page = soup.find('a', class_='next')
                if not next_page:
                    break
                page += 1
                await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"PicNSave scraper error: {e}")
    return listings


async def run_full_scrape():
    """Run scraper for all sources and store results"""
    logger.info("=== Starting full scrape ===")
    now = datetime.now(timezone.utc).isoformat()

    # Update scrape status
    await db.scrape_status.update_one(
        {"id": "global"},
        {"$set": {"status": "running", "started_at": now}},
        upsert=True
    )

    all_listings = []
    try:
        # Scrape all three sources
        logger.info("Scraping Cathcart Rebuilders...")
        cathcart_rebuild = await scrape_cathcart(
            "https://cathcartauto.com/vehicles/rebuilders/",
            "cathcart_rebuilders"
        )
        all_listings.extend(cathcart_rebuild)
        logger.info(f"  Got {len(cathcart_rebuild)} listings")

        logger.info("Scraping Cathcart Used Cars...")
        cathcart_used = await scrape_cathcart(
            "https://cathcartauto.com/vehicles/used-cars/",
            "cathcart_used"
        )
        all_listings.extend(cathcart_used)
        logger.info(f"  Got {len(cathcart_used)} listings")

        logger.info("Scraping Pic N Save...")
        picnsave = await scrape_picnsave()
        all_listings.extend(picnsave)
        logger.info(f"  Got {len(picnsave)} listings")

    except Exception as e:
        logger.error(f"Scrape failed: {e}")

    # Process and store listings
    new_count = 0
    updated_count = 0
    for raw in all_listings:
        url = raw.get("url", "")
        if not url:
            continue

        # Calculate profit data
        year = raw.get("year")
        mileage = raw.get("mileage")
        price = raw.get("price")
        damage = raw.get("damage", "")
        brand = raw.get("brand", "")

        # Market value
        market_value = None
        if year and raw.get("title"):
            market_value = estimate_market_value(raw["title"], year, mileage)
            # Salvage title discount
            if brand and ("SALVAGE" in brand.upper()):
                market_value = round(market_value * 0.75, 0)

        # Repair cost
        repair_low, repair_high = get_repair_range(damage)

        # Profit calc
        profit_best = None
        profit_worst = None
        roi_best = None
        roi_worst = None
        fees = None
        if price and price > 0 and market_value:
            fees = round(calculate_ontario_fees(price), 0)
            profit_best = round(market_value - price - repair_low - fees, 0)
            profit_worst = round(market_value - price - repair_high - fees, 0)
            roi_best = round((profit_best / price) * 100, 1) if price > 0 else None
            roi_worst = round((profit_worst / price) * 100, 1) if price > 0 else None

        # Deal score
        score = None
        score_label = None
        if profit_best is not None and profit_worst is not None:
            score, score_label = calc_deal_score(profit_best, profit_worst)

        listing_doc = {
            "url": url,
            "source": raw.get("source", ""),
            "title": raw.get("title", ""),
            "price": price,
            "price_raw": raw.get("price_raw", ""),
            "status": raw.get("status", "for_sale"),
            "colour": raw.get("colour", ""),
            "mileage": mileage,
            "damage": damage,
            "brand": brand,
            "description": raw.get("description", ""),
            "photo": raw.get("photo"),
            "photos": raw.get("photos", []),
            "year": year,
            "market_value": market_value,
            "repair_low": repair_low,
            "repair_high": repair_high,
            "fees": fees,
            "profit_best": profit_best,
            "profit_worst": profit_worst,
            "roi_best": roi_best,
            "roi_worst": roi_worst,
            "deal_score": score,
            "deal_label": score_label,
            "last_scraped": now,
        }

        # Upsert by URL
        existing = await db.listings.find_one({"url": url}, {"_id": 0})
        if existing:
            # Update existing - preserve first_seen
            listing_doc["first_seen"] = existing.get("first_seen", now)
            listing_doc["id"] = existing.get("id", str(uuid.uuid4()))
            # Track price changes
            old_price = existing.get("price")
            if old_price and price and old_price != price:
                history = existing.get("price_history", [])
                history.append({"price": old_price, "date": existing.get("last_scraped", now)})
                listing_doc["price_history"] = history
            else:
                listing_doc["price_history"] = existing.get("price_history", [])
            await db.listings.update_one({"url": url}, {"$set": listing_doc})
            updated_count += 1
        else:
            listing_doc["id"] = str(uuid.uuid4())
            listing_doc["first_seen"] = now
            listing_doc["price_history"] = []
            await db.listings.insert_one(listing_doc)
            new_count += 1

    # Mark listings not seen in this scrape as inactive — per source only
    # Only mark inactive for sources that actually returned results
    source_urls = {}
    for l in all_listings:
        src = l.get("source", "")
        url = l.get("url", "")
        if src and url:
            if src not in source_urls:
                source_urls[src] = set()
            source_urls[src].add(url)

    for src, urls in source_urls.items():
        if urls:  # Only mark inactive if this source returned results
            await db.listings.update_many(
                {"source": src, "url": {"$nin": list(urls)}, "is_inactive": {"$ne": True}},
                {"$set": {"is_inactive": True}}
            )

    finish_time = datetime.now(timezone.utc).isoformat()
    await db.scrape_status.update_one(
        {"id": "global"},
        {"$set": {
            "status": "completed",
            "finished_at": finish_time,
            "total_listings": len(all_listings),
            "new_count": new_count,
            "updated_count": updated_count,
            "sources": {
                "cathcart_rebuilders": len([l for l in all_listings if l["source"] == "cathcart_rebuilders"]),
                "cathcart_used": len([l for l in all_listings if l["source"] == "cathcart_used"]),
                "picnsave": len([l for l in all_listings if l["source"] == "picnsave"]),
            }
        }},
        upsert=True
    )
    logger.info(f"=== Scrape complete: {new_count} new, {updated_count} updated, {len(all_listings)} total ===")
    return {"new": new_count, "updated": updated_count, "total": len(all_listings)}


# ─── Background scheduler ───
scrape_lock = asyncio.Lock()
scrape_task = None
current_interval = 600  # default 10 minutes

async def get_scan_interval():
    settings = await db.user_settings.find_one({"id": "global"}, {"_id": 0})
    if settings:
        return settings.get("scan_interval", 600)
    return 600

async def scheduled_scrape():
    """Run scrape on user-configured interval"""
    global current_interval
    while True:
        current_interval = await get_scan_interval()
        async with scrape_lock:
            try:
                await run_full_scrape()
            except Exception as e:
                logger.error(f"Scheduled scrape error: {e}")
        # Log this scan to history
        await db.scan_history.insert_one({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "interval": current_interval,
            "status": "completed",
        })
        # Keep only last 50 history entries
        count = await db.scan_history.count_documents({})
        if count > 50:
            oldest = await db.scan_history.find().sort("timestamp", 1).limit(count - 50).to_list(count - 50)
            if oldest:
                ids = [o["id"] for o in oldest]
                await db.scan_history.delete_many({"id": {"$in": ids}})
        await asyncio.sleep(current_interval)

@app.on_event("startup")
async def startup():
    global scrape_task
    # Init settings if not exists
    existing_settings = await db.user_settings.find_one({"id": "global"})
    if not existing_settings:
        await db.user_settings.insert_one({
            "id": "global",
            "scan_interval": 600,
        })
    # Check if we have any listings
    count = await db.listings.count_documents({})
    if count == 0:
        logger.info("No listings in DB, triggering initial scrape...")
        asyncio.create_task(run_full_scrape())
    # Start background scheduler
    scrape_task = asyncio.create_task(scheduled_scrape())

# ─── API Endpoints ───

@api_router.get("/")
async def root():
    return {"message": "AutoFlip Intelligence API", "version": "2.0.0"}

@api_router.get("/listings")
async def get_listings(
    source: Optional[str] = None,
    min_profit: Optional[float] = None,
    max_price: Optional[float] = None,
    min_score: Optional[int] = None,
    damage_type: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "deal_score",
    sort_order: str = "desc",
    status: Optional[str] = None,
    brand_type: Optional[str] = None,
):
    query = {"is_inactive": {"$ne": True}}
    if source:
        query["source"] = source
    if max_price is not None:
        query["price"] = {"$lte": max_price, "$gt": 0}
    if damage_type:
        query["damage"] = {"$regex": damage_type, "$options": "i"}
    if search:
        query["title"] = {"$regex": search, "$options": "i"}
    if status:
        query["status"] = status
    if brand_type:
        if brand_type == "salvage":
            query["brand"] = {"$regex": "SALVAGE", "$options": "i"}
        elif brand_type == "clean":
            query["brand"] = {"$regex": "CLEAN", "$options": "i"}
        elif brand_type == "rebuilt":
            query["brand"] = {"$regex": "REBUILT", "$options": "i"}

    listings = await db.listings.find(query, {"_id": 0}).to_list(500)

    # Post-query filters
    if min_profit is not None:
        listings = [l for l in listings if (l.get("profit_best") or 0) >= min_profit]
    if min_score is not None:
        listings = [l for l in listings if (l.get("deal_score") or 0) >= min_score]

    # Sort
    reverse = sort_order == "desc"
    sort_key = {
        "deal_score": lambda x: x.get("deal_score") or 0,
        "profit": lambda x: x.get("profit_best") or -999999,
        "price": lambda x: x.get("price") or 999999,
        "mileage": lambda x: x.get("mileage") or 999999,
    }.get(sort_by, lambda x: x.get("deal_score") or 0)

    listings.sort(key=sort_key, reverse=reverse)
    return listings

@api_router.get("/listings/{listing_id}")
async def get_listing(listing_id: str):
    listing = await db.listings.find_one({"id": listing_id}, {"_id": 0})
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing

@api_router.get("/stats")
async def get_stats():
    total = await db.listings.count_documents({"is_inactive": {"$ne": True}})
    listings = await db.listings.find({"is_inactive": {"$ne": True}}, {"_id": 0}).to_list(500)

    buy_count = sum(1 for l in listings if l.get("deal_label") == "BUY")
    watch_count = sum(1 for l in listings if l.get("deal_label") == "WATCH")
    skip_count = sum(1 for l in listings if l.get("deal_label") == "SKIP")
    no_score = total - buy_count - watch_count - skip_count

    avg_profit = 0
    profit_listings = [l for l in listings if l.get("profit_best") is not None and l.get("profit_best", 0) > 0]
    if profit_listings:
        avg_profit = sum(l["profit_best"] for l in profit_listings) / len(profit_listings)
    top_profit = max((l.get("profit_best", 0) or 0 for l in listings), default=0)

    source_counts = {}
    for src in ["cathcart_rebuilders", "cathcart_used", "picnsave"]:
        source_counts[src] = sum(1 for l in listings if l.get("source") == src)

    best_deal = None
    scored = [l for l in listings if l.get("deal_score")]
    if scored:
        best_deal = max(scored, key=lambda x: x["deal_score"])
        best_deal = {"title": best_deal["title"], "score": best_deal["deal_score"], "profit_best": best_deal.get("profit_best")}

    scrape_status = await db.scrape_status.find_one({"id": "global"}, {"_id": 0})

    return {
        "total_listings": total,
        "buy_count": buy_count,
        "watch_count": watch_count,
        "skip_count": skip_count,
        "no_score_count": no_score,
        "avg_profit_best": round(avg_profit, 0),
        "top_profit": round(top_profit, 0),
        "source_counts": source_counts,
        "best_deal": best_deal,
        "last_scrape": scrape_status,
    }

@api_router.post("/scrape")
async def trigger_scrape():
    """Manually trigger a scrape"""
    if scrape_lock.locked():
        return {"status": "already_running"}
    asyncio.create_task(run_full_scrape())
    return {"status": "started"}

@api_router.get("/scrape-status")
async def get_scrape_status():
    status = await db.scrape_status.find_one({"id": "global"}, {"_id": 0})
    settings = await db.user_settings.find_one({"id": "global"}, {"_id": 0})
    interval = settings.get("scan_interval", 600) if settings else 600
    result = status or {"status": "never_run"}
    result["scan_interval"] = interval
    result["is_scanning"] = scrape_lock.locked()
    return result

@api_router.get("/scan-history")
async def get_scan_history():
    history = await db.scan_history.find({}, {"_id": 0}).sort("timestamp", -1).to_list(20)
    return history

@api_router.get("/settings")
async def get_settings():
    settings = await db.user_settings.find_one({"id": "global"}, {"_id": 0})
    return settings or {"id": "global", "scan_interval": 600}

@api_router.put("/settings")
async def update_settings(data: dict):
    allowed = {"scan_interval"}
    update = {k: v for k, v in data.items() if k in allowed}
    if "scan_interval" in update:
        val = int(update["scan_interval"])
        if val < 60:
            val = 60
        if val > 3600:
            val = 3600
        update["scan_interval"] = val
    if update:
        await db.user_settings.update_one({"id": "global"}, {"$set": update}, upsert=True)
    settings = await db.user_settings.find_one({"id": "global"}, {"_id": 0})
    return settings

# Include router + CORS
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    global scrape_task
    if scrape_task:
        scrape_task.cancel()
    client.close()
