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

# ─── AI Damage Detection ───
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
import base64

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

async def detect_damage_from_photo(photo_urls, source: str = "", brand_status: str = "") -> dict:
    """Use GPT-4o vision to analyze multiple car photos and detect damage type + severity."""
    if not EMERGENT_LLM_KEY:
        return {"damage": "", "severity": "unknown", "confidence": 0}

    # Accept single URL or list
    if isinstance(photo_urls, str):
        photo_urls = [photo_urls]
    photo_urls = [u for u in photo_urls if u][:3]  # Analyze up to 3 photos
    if not photo_urls:
        return {"damage": "", "severity": "unknown", "confidence": 0}

    try:
        image_contents = []
        async with httpx.AsyncClient(timeout=15, headers=HEADERS, follow_redirects=True) as http:
            for url in photo_urls:
                try:
                    resp = await http.get(url)
                    if resp.status_code == 200:
                        img_b64 = base64.b64encode(resp.content).decode('utf-8')
                        image_contents.append(ImageContent(image_base64=img_b64))
                except Exception:
                    continue

        if not image_contents:
            return {"damage": "", "severity": "unknown", "confidence": 0}

        is_salvage_lot = source in ("cathcart_rebuilders", "picnsave") or (brand_status and "SALVAGE" in brand_status.upper())
        context_note = ""
        if is_salvage_lot:
            context_note = (
                "CRITICAL CONTEXT: This vehicle is listed on a SALVAGE / REBUILDABLE car lot. "
                "It almost certainly has damage — it would not be on a salvage lot otherwise. "
                "Look very carefully for: dents, misaligned panels, scratches, paint damage, "
                "cracked bumpers, broken lights, rust, frame damage, missing parts, "
                "flood marks, fire damage, broken glass, airbag deployment signs. "
                "Even if the damage looks minor, REPORT IT. Do NOT say NONE unless the vehicle "
                "is genuinely perfect (extremely unlikely for a salvage lot car). "
            )

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"damage-detect-{uuid.uuid4()}",
            system_message=(
                "You are an expert automotive damage assessor specializing in salvage and insurance vehicles. "
                f"{context_note}"
                "Analyze ALL provided photos of this vehicle and respond ONLY with a JSON object (no markdown, no explanation) with these fields:\n"
                '{"damage_type": "FRONT|REAR|LEFT FRONT|RIGHT FRONT|LEFT REAR|RIGHT REAR|LEFT SIDE|RIGHT SIDE|LEFT DOORS|RIGHT DOORS|ROLLOVER|FIRE|FLOOD|ROOF|UNDERCARRIAGE|NONE", '
                '"severity": "minor|moderate|severe|total", '
                '"confidence": 0.0-1.0, '
                '"details": "specific description of damage observed across all photos"}\n'
                "If multiple damage areas exist, pick the PRIMARY / most costly one for damage_type. "
                "Be specific in details — mention crumpled panels, broken headlights, airbag deployment, etc."
            )
        ).with_model("openai", "gpt-4o")

        user_msg = UserMessage(
            text=f"Analyze these {len(image_contents)} photo(s) of a vehicle from a {'salvage/rebuildable' if is_salvage_lot else 'used car'} lot. Identify the primary damage area and severity. Return only the JSON.",
            file_contents=image_contents
        )
        response_text = await chat.send_message(user_msg)
        import json
        clean = response_text.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
            clean = clean.rsplit("```", 1)[0]
        result = json.loads(clean)
        logger.info(f"  AI damage detection ({len(image_contents)} photos): {result.get('damage_type')} ({result.get('severity')}) conf={result.get('confidence')}")
        return {
            "damage": result.get("damage_type", ""),
            "severity": result.get("severity", "unknown"),
            "confidence": result.get("confidence", 0),
            "details": result.get("details", ""),
        }
    except Exception as e:
        logger.warning(f"  AI damage detection failed: {e}")
        return {"damage": "", "severity": "unknown", "confidence": 0}


# ─── AutoTrader.ca Market Comp Scraper ───
# In-memory cache: {cache_key: {"prices": [...], "median": float, "fetched_at": datetime}}
_autotrader_cache = {}  # In-memory layer
AUTOTRADER_CACHE_TTL = 3600 * 24  # 24 hours cache
_autotrader_request_count = 0
_autotrader_last_reset = datetime.now()
AUTOTRADER_MAX_REQUESTS_PER_CYCLE = 10  # Only 10 per cycle, spread over time
AUTOTRADER_DELAY_MIN = 4.0
AUTOTRADER_DELAY_MAX = 8.0

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


async def _load_at_cache_from_db():
    """Load AutoTrader comp cache from MongoDB on startup."""
    global _autotrader_cache
    docs = await db.autotrader_cache.find({}, {"_id": 0}).to_list(500)
    for doc in docs:
        key = doc.get("cache_key")
        fetched_at = doc.get("fetched_at")
        if key and fetched_at:
            age = (datetime.now() - datetime.fromisoformat(fetched_at)).total_seconds()
            if age < AUTOTRADER_CACHE_TTL:
                _autotrader_cache[key] = {
                    "result": doc.get("result", {}),
                    "fetched_at": datetime.fromisoformat(fetched_at),
                }
    logger.info(f"Loaded {len(_autotrader_cache)} AutoTrader cached comps from DB")

# Make → AutoTrader URL slug mapping
MAKE_SLUGS = {
    "toyota": "toyota", "honda": "honda", "ford": "ford", "chevrolet": "chevrolet",
    "gmc": "gmc", "dodge": "dodge", "ram": "ram", "jeep": "jeep",
    "hyundai": "hyundai", "hyundia": "hyundai", "kia": "kia", "nissan": "nissan", "subaru": "subaru",
    "mazda": "mazda", "bmw": "bmw", "mercedes": "mercedes-benz", "audi": "audi",
    "volkswagen": "volkswagen", "volkswagon": "volkswagen", "lexus": "lexus",
    "acura": "acura", "cadillac": "cadillac", "tesla": "tesla", "mini": "mini",
    "fiat": "fiat", "mitsubishi": "mitsubishi", "infiniti": "infiniti",
    "volvo": "volvo", "lincoln": "lincoln", "buick": "buick",
    "chrysler": "chrysler", "genesis": "genesis", "porsche": "porsche",
}

# Model → AutoTrader URL slug mapping
MODEL_SLUGS = {
    "civic": "civic", "corolla": "corolla", "camry": "camry", "accord": "accord",
    "cr-v": "cr-v", "crv": "cr-v", "rav4": "rav4", "rav-4": "rav4",
    "highlander": "highlander", "tacoma": "tacoma", "tundra": "tundra",
    "4runner": "4runner", "prius": "prius", "sienna": "sienna",
    "forester": "forester", "outback": "outback", "crosstrek": "crosstrek",
    "impreza": "impreza", "wrx": "wrx",
    "mazda3": "mazda3", "cx-5": "cx-5", "cx5": "cx-5", "cx-30": "cx-30", "cx-50": "cx-50", "cx-90": "cx-90",
    "rogue": "rogue", "pathfinder": "pathfinder", "sentra": "sentra", "altima": "altima",
    "frontier": "frontier", "murano": "murano",
    "elantra": "elantra", "sonata": "sonata", "tucson": "tucson", "santa fe": "santa+fe",
    "palisade": "palisade", "kona": "kona", "ioniq": "ioniq",
    "forte": "forte", "k5": "k5", "sportage": "sportage", "sorento": "sorento",
    "telluride": "telluride", "seltos": "seltos", "niro": "niro",
    "f150": "f-150", "f-150": "f-150", "f250": "f-250", "f-250": "f-250",
    "escape": "escape", "edge": "edge", "explorer": "explorer", "bronco": "bronco",
    "mustang": "mustang", "ranger": "ranger", "maverick": "maverick",
    "silverado": "silverado", "equinox": "equinox", "traverse": "traverse",
    "blazer": "blazer", "colorado": "colorado", "tahoe": "tahoe", "trax": "trax",
    "sierra": "sierra", "terrain": "terrain", "acadia": "acadia", "yukon": "yukon",
    "wrangler": "wrangler", "grand cherokee": "grand+cherokee", "gladiator": "gladiator",
    "challenger": "challenger", "charger": "charger", "durango": "durango",
    "3 series": "3+series", "5 series": "5+series", "x3": "x3", "x5": "x5",
    "model 3": "model+3", "model y": "model+y",
    "rx350": "rx", "rx": "rx", "nx": "nx", "es": "es", "is": "is",
    "rdx": "rdx", "mdx": "mdx",
    "xt4": "xt4", "xt5": "xt5", "escalade": "escalade",
    "golf": "golf", "jetta": "jetta", "tiguan": "tiguan", "atlas": "atlas",
}


def _extract_make_model(title_lower: str) -> tuple:
    """Extract make and model slugs from a listing title for AutoTrader search."""
    make_slug = None
    model_slug = None

    # Match make (longest match wins)
    best_make_len = 0
    for make, slug in MAKE_SLUGS.items():
        if make in title_lower and len(make) > best_make_len:
            make_slug = slug
            best_make_len = len(make)

    # Match model (longest match wins, with word boundary check for short models)
    best_model_len = 0
    for model, slug in MODEL_SLUGS.items():
        if len(model) <= 3:
            # Short models need word boundary: check with regex
            if re.search(r'\b' + re.escape(model) + r'\b', title_lower):
                if len(model) > best_model_len:
                    model_slug = slug
                    best_model_len = len(model)
        else:
            if model in title_lower and len(model) > best_model_len:
                model_slug = slug
                best_model_len = len(model)

    return make_slug, model_slug


async def fetch_autotrader_comps(title: str, year: int, mileage: int = None) -> dict:
    """Fetch comparable vehicle prices from AutoTrader.ca for Ontario."""
    global _autotrader_request_count, _autotrader_last_reset
    import asyncio

    title_lower = title.lower()
    make_slug, model_slug = _extract_make_model(title_lower)

    if not make_slug or not model_slug:
        return {"prices": [], "median": None, "count": 0, "source": "autotrader", "error": "no_make_model_match"}

    cache_key = f"{make_slug}_{model_slug}_{year}"
    now = datetime.now()

    # Reset request counter every 30 minutes
    if (now - _autotrader_last_reset).total_seconds() > 1800:
        _autotrader_request_count = 0
        _autotrader_last_reset = now

    if cache_key in _autotrader_cache:
        cached = _autotrader_cache[cache_key]
        age_sec = (now - cached["fetched_at"]).total_seconds()
        if age_sec < AUTOTRADER_CACHE_TTL:
            return cached["result"]

    # Rate limit check
    if _autotrader_request_count >= AUTOTRADER_MAX_REQUESTS_PER_CYCLE:
        return {"prices": [], "median": None, "count": 0, "source": "autotrader", "error": "rate_limit_reached"}

    # Random delay between requests to avoid detection
    import random
    delay = random.uniform(AUTOTRADER_DELAY_MIN, AUTOTRADER_DELAY_MAX)
    await asyncio.sleep(delay)
    _autotrader_request_count += 1

    year_low = max(year - 1, 2000)
    year_high = year + 1
    url = f"https://www.autotrader.ca/cars/{make_slug}/{model_slug}/on/?rcp=15&rcs=0&srt=35&yRng={year_low}%2C{year_high}&prx=-1&prv=Ontario&loc=Toronto%2C+ON"

    try:
        import random
        ua = random.choice(_USER_AGENTS)
        at_headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.autotrader.ca/",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
        }
        async with httpx.AsyncClient(timeout=15, headers=at_headers, follow_redirects=True) as http:
            resp = await http.get(url)
            if resp.status_code != 200:
                return {"prices": [], "median": None, "count": 0, "source": "autotrader", "error": f"http_{resp.status_code}"}

        soup = BeautifulSoup(resp.text, 'html.parser')
        raw_prices = []
        for el in soup.find_all(class_=re.compile(r'price|Price')):
            text = el.get_text(strip=True)
            if '$' in text:
                match = re.match(r'\$([\d,]+)', text)
                if match:
                    try:
                        p = int(match.group(1).replace(',', ''))
                        if 2000 < p < 200000:
                            raw_prices.append(p)
                    except ValueError:
                        pass

        # Deduplicate (each listing price appears multiple times in the HTML)
        prices = sorted(set(raw_prices))

        if not prices:
            result = {"prices": [], "median": None, "count": 0, "source": "autotrader", "error": "no_prices_found"}
        else:
            median = prices[len(prices) // 2]
            result = {
                "prices": prices,
                "median": median,
                "count": len(prices),
                "avg": round(sum(prices) / len(prices)),
                "low": prices[0],
                "high": prices[-1],
                "source": "autotrader",
                "search_url": url,
            }

        _autotrader_cache[cache_key] = {"result": result, "fetched_at": now}
        # Persist to MongoDB for crash recovery
        try:
            await db.autotrader_cache.update_one(
                {"cache_key": cache_key},
                {"$set": {"cache_key": cache_key, "result": result, "fetched_at": now.isoformat()}},
                upsert=True
            )
        except Exception:
            pass
        logger.info(f"  AutoTrader comps for {make_slug} {model_slug} {year}: {len(prices)} found, median=${result.get('median')}")
        return result

    except Exception as e:
        logger.warning(f"  AutoTrader fetch failed for {make_slug} {model_slug} {year}: {e}")
        return {"prices": [], "median": None, "count": 0, "source": "autotrader", "error": str(e)}

# ─── MSRP Reference Data (Canadian $, approximate new base MSRP) ───
MSRP_DATA = {
    # Japanese
    "civic": 30000, "corolla": 28000, "camry": 35000, "accord": 40000,
    "cr-v": 38000, "crv": 38000, "rav4": 38000, "rav-4": 38000,
    "highlander": 48000, "tacoma": 45000, "tundra": 55000, "4runner": 52000,
    "land cruiser": 75000, "landcruiser": 75000, "prius": 36000,
    "sienna": 48000, "forester": 38000, "outback": 40000, "impreza": 30000,
    "wrx": 38000, "crosstrek": 34000, "mazda3": 28000, "cx-5": 36000, "cx5": 36000,
    "cx-30": 30000, "cx-50": 42000, "cx-90": 50000,
    "rogue": 36000, "pathfinder": 46000, "sentra": 24000, "altima": 34000,
    "frontier": 42000, "murano": 44000,
    # Korean
    "elantra": 26000, "sonata": 34000, "tucson": 36000, "santa fe": 42000,
    "palisade": 52000, "kona": 30000, "ioniq": 45000,
    "forte": 25000, "k5": 34000, "sportage": 36000, "sorento": 42000,
    "telluride": 52000, "seltos": 30000, "carnival": 45000, "niro": 35000,
    # American
    "f150": 52000, "f-150": 52000, "f250": 62000, "f-250": 62000,
    "escape": 36000, "edge": 42000, "explorer": 48000, "bronco": 48000,
    "mustang": 38000, "ranger": 42000, "maverick": 32000,
    "silverado": 52000, "equinox": 38000, "traverse": 44000, "blazer": 42000,
    "colorado": 40000, "tahoe": 65000, "suburban": 70000,
    "trax": 28000, "malibu": 30000,
    "sierra": 55000, "terrain": 38000, "acadia": 44000, "yukon": 68000,
    "ram": 52000, "ram 1500": 52000, "ram 2500": 60000,
    "wrangler": 48000, "grand cherokee": 55000, "cherokee": 42000,
    "gladiator": 50000, "compass": 36000,
    "challenger": 42000, "charger": 42000, "durango": 48000,
    # European
    "3 series": 52000, "5 series": 68000, "x1": 46000, "x3": 52000, "x5": 72000,
    "c-class": 52000, "e-class": 70000, "glc": 55000, "gle": 70000,
    "a3": 40000, "a4": 48000, "q3": 42000, "q5": 50000, "q7": 65000,
    "golf": 32000, "jetta": 28000, "tiguan": 36000, "atlas": 44000, "taos": 32000,
    # Luxury
    "rx350": 60000, "rx": 60000, "nx": 48000, "es": 50000, "is": 45000,
    "rdx": 48000, "mdx": 58000, "tlx": 48000,
    "xt4": 42000, "xt5": 52000, "xt6": 58000, "escalade": 85000,
    "model 3": 50000, "model y": 55000, "model s": 95000, "model x": 100000,
    # Rec vehicles / powersports
    "sidewinder": 22000, "ski doo": 18000, "ski-doo": 18000, "backcountry": 20000,
    "cooper": 32000, "mini": 32000,
}

# ─── Brand Value Retention Multiplier ───
# How well does this brand hold resale value vs average? (1.0 = average)
BRAND_RETENTION = {
    "toyota": 1.18, "lexus": 1.22, "honda": 1.14, "acura": 1.08,
    "subaru": 1.12, "mazda": 1.06, "porsche": 1.25,
    "jeep": 1.08, "ram": 1.05, "gmc": 1.02, "ford": 0.98,
    "chevrolet": 0.92, "dodge": 0.88, "chrysler": 0.82,
    "hyundai": 0.96, "hyundia": 0.96, "kia": 0.94, "nissan": 0.90, "mitsubishi": 0.82,
    "bmw": 0.92, "mercedes": 0.90, "audi": 0.88,
    "volkswagen": 0.88, "volkswagon": 0.88, "volvo": 0.90,
    "tesla": 1.05, "cadillac": 0.85, "buick": 0.82,
    "lincoln": 0.82, "infiniti": 0.80, "genesis": 0.88,
    "fiat": 0.68, "jaguar": 0.70, "land rover": 0.72,
    "yamaha": 0.85, "ski-doo": 0.80, "mini": 0.78,
}

# ─── Body Type Demand Multiplier (Ontario market) ───
BODY_TYPE_KEYWORDS = {
    1.30: ["f150", "f-150", "f250", "f-250", "sierra", "silverado", "ram 1500", "ram 2500", "tundra", "tacoma", "ranger", "frontier", "colorado", "gladiator", "maverick"],
    1.20: ["wrangler", "4runner", "land cruiser", "landcruiser", "bronco"],
    1.15: ["rav4", "rav-4", "crv", "cr-v", "forester", "rogue", "escape", "equinox", "sportage", "tucson", "cx-5", "cx5", "crosstrek", "seltos", "kona", "taos", "cx-30"],
    1.12: ["highlander", "grand cherokee", "palisade", "telluride", "explorer", "traverse", "pathfinder", "santa fe", "sorento", "tahoe", "suburban", "yukon", "4 runner"],
    1.08: ["hybrid", "plug in", "plug-in", "hev", "phev"],
    1.05: ["sienna", "odyssey", "carnival", "van", "promaster", "transit"],
    0.95: ["sedan", "civic", "corolla", "sentra", "elantra", "forte", "accent", "jetta", "mazda3"],
    0.90: ["coupe", "convertible"],
}

# ─── Trim Level Multiplier ───
TRIM_TIERS = {
    1.25: ["limited", "platinum", "calligraphy", "ultimate", "denali", "king ranch", "high country", "pinnacle"],
    1.15: ["lariat", "sport", "gt", "rs", "performance", "st", "type r", "type-r", "trd pro", "trail boss", "rubicon", "sahara", "overland"],
    1.10: ["se", "sel", "xlt", "ex", "ex-l", "touring", "preferred", "premium", "awd", "4x4", "all wheel"],
    1.05: ["le", "xle", "sx", "lx", "base"],
}

# ─── Color Value Multiplier ───
# Ontario market: neutral colors sell faster and for more
COLOR_MULTIPLIER = {
    "white": 1.04, "black": 1.03, "silver": 1.02, "grey": 1.02, "gray": 1.02,
    "blue": 1.00, "red": 0.99, "dark blue": 1.01, "dark grey": 1.02,
    "brown": 0.95, "beige": 0.94, "gold": 0.93, "orange": 0.93,
    "green": 0.93, "yellow": 0.91, "purple": 0.90, "pink": 0.88,
}

# ─── Depreciation Curve (% of MSRP retained by age) ───
# Based on Canadian Black Book / industry averages
DEPRECIATION_CURVE = {
    0: 1.00,   # New
    1: 0.82,   # 1 year old — biggest drop
    2: 0.72,
    3: 0.63,
    4: 0.55,
    5: 0.48,
    6: 0.42,
    7: 0.37,
    8: 0.32,
    9: 0.28,
    10: 0.25,
    11: 0.22,
    12: 0.19,
    13: 0.17,
    14: 0.15,
    15: 0.13,
    16: 0.11,
    17: 0.10,
    18: 0.09,
    19: 0.08,
    20: 0.07,
}

# ─── Repair Cost Map (Ontario body shop rates ~$110-130/hr) ───
# [low, high] in CAD — includes parts + labour estimates
REPAIR_COST_MAP = {
    "FRONT":          [3000, 6500],
    "FRONT END":      [3000, 6500],
    "LEFT FRONT":     [2800, 6000],
    "RIGHT FRONT":    [2800, 6000],
    "REAR":           [2000, 4500],
    "LEFT REAR":      [2000, 4500],
    "RIGHT REAR":     [2000, 4500],
    "LEFT DOORS":     [1500, 3500],
    "RIGHT DOORS":    [1500, 3500],
    "DOORS":          [1500, 3500],
    "LEFT SIDE":      [2000, 4500],
    "RIGHT SIDE":     [2000, 4500],
    "ROOF":           [2500, 6000],
    "UNDERCARRIAGE":  [3000, 7000],
    "ROLLOVER":       [6000, 16000],
    "FIRE":           [4000, 12000],
    "FLOOD":          [4000, 12000],
}
DEFAULT_REPAIR = [500, 1500]

# Ontario fixed costs
SAFETY_INSPECTION_COST = 100  # Mandatory safety standards certificate
STRUCTURAL_INSPECTION_COST = 400  # Required for salvage → rebuilt
VIN_VERIFICATION_COST = 75
APPRAISAL_FEE = 150
OMVIC_FEE = 22
MTO_TRANSFER_FEE = 32
REBUILT_TITLE_PROCESS = STRUCTURAL_INSPECTION_COST + VIN_VERIFICATION_COST + APPRAISAL_FEE  # ~$625


def _find_msrp(title_lower: str) -> float:
    """Find the closest MSRP match from the title."""
    best_match = None
    best_len = 0
    for model, msrp in MSRP_DATA.items():
        if model in title_lower and len(model) > best_len:
            best_match = msrp
            best_len = len(model)
    return best_match


def _get_brand(title_lower: str) -> tuple:
    """Extract brand name and its retention multiplier."""
    for brand, mult in BRAND_RETENTION.items():
        if brand in title_lower:
            return brand, mult
    return "unknown", 0.90


def _get_body_type_mult(title_lower: str) -> float:
    """Get body type demand multiplier."""
    for mult, keywords in BODY_TYPE_KEYWORDS.items():
        if any(k in title_lower for k in keywords):
            return mult
    return 1.0


def _get_trim_mult(title_lower: str) -> float:
    """Get trim level multiplier."""
    for mult, keywords in TRIM_TIERS.items():
        if any(k in title_lower for k in keywords):
            return mult
    return 1.0


def _get_color_mult(colour: str) -> float:
    """Get color-based value multiplier."""
    if not colour:
        return 1.0
    c = colour.lower().strip()
    for color_name, mult in COLOR_MULTIPLIER.items():
        if color_name in c:
            return mult
    return 0.97  # Unknown/unusual color — slight discount


def _get_depreciation(age: int) -> float:
    """Get depreciation factor from curve. Interpolates for ages > 20."""
    if age <= 0:
        return 1.0
    if age in DEPRECIATION_CURVE:
        return DEPRECIATION_CURVE[age]
    if age > 20:
        return max(0.04, 0.07 - (age - 20) * 0.005)
    return 0.07


def _get_mileage_adjustment(mileage: int, age: int) -> float:
    """
    Mileage-based adjustment using a continuous curve.
    Average Ontario driving: ~18,000 km/year.
    Returns a multiplier (e.g., 0.85 for high mileage, 1.08 for low).
    """
    if not mileage or mileage <= 0:
        return 1.0
    avg_km_year = 18000
    expected = max(avg_km_year, age * avg_km_year)
    ratio = mileage / expected

    if ratio <= 0.5:
        return 1.08   # Exceptionally low mileage
    elif ratio <= 0.7:
        return 1.05
    elif ratio <= 0.9:
        return 1.02
    elif ratio <= 1.1:
        return 1.00   # Average
    elif ratio <= 1.3:
        return 0.96
    elif ratio <= 1.5:
        return 0.92
    elif ratio <= 1.8:
        return 0.87
    elif ratio <= 2.0:
        return 0.82
    else:
        return max(0.70, 0.82 - (ratio - 2.0) * 0.06)


def estimate_market_value(title: str, year: int, mileage: int = None,
                          colour: str = "", brand_status: str = "") -> dict:
    """
    Estimate Ontario retail market value using our formula (SYNC version).
    Returns dict with value breakdown for transparency.
    """
    current_year = datetime.now().year
    age = max(0, current_year - year)
    title_lower = title.lower()

    # 1. MSRP baseline
    msrp = _find_msrp(title_lower)
    msrp_source = "model_match"
    if not msrp:
        _, brand_mult = _get_brand(title_lower)
        body_mult = _get_body_type_mult(title_lower)
        msrp = 35000 * brand_mult * body_mult
        msrp_source = "estimated"

    dep_factor = _get_depreciation(age)
    brand_name, brand_mult = _get_brand(title_lower)
    body_mult = _get_body_type_mult(title_lower)
    trim_mult = _get_trim_mult(title_lower)
    color_mult = _get_color_mult(colour)
    mileage_mult = _get_mileage_adjustment(mileage, age) if mileage else 1.0

    clean_value = msrp * dep_factor * brand_mult * body_mult * trim_mult * color_mult * mileage_mult

    is_salvage = brand_status and "SALVAGE" in brand_status.upper()
    is_rebuilt = brand_status and "REBUILT" in brand_status.upper()
    title_mult = 1.0
    title_note = "clean_title"
    if is_salvage:
        title_mult = 0.55
        title_note = "salvage_title"
    elif is_rebuilt:
        title_mult = 0.75
        title_note = "rebuilt_title"

    formula_value = round(clean_value * title_mult, 0)
    formula_value = max(formula_value, 800)

    return {
        "market_value": formula_value,
        "formula_value": formula_value,
        "autotrader_median": None,
        "autotrader_count": 0,
        "blend_method": "formula_only",
        "msrp": round(msrp, 0),
        "msrp_source": msrp_source,
        "depreciation": round(dep_factor, 3),
        "brand": brand_name,
        "brand_mult": brand_mult,
        "body_mult": body_mult,
        "trim_mult": trim_mult,
        "color_mult": color_mult,
        "mileage_mult": round(mileage_mult, 3),
        "title_status": title_note,
        "title_mult": title_mult,
        "age": age,
    }


async def estimate_market_value_blended(title: str, year: int, mileage: int = None,
                                         colour: str = "", brand_status: str = "") -> dict:
    """
    Blended market value: AutoTrader.ca real comps + our formula.
    - If comps found: 60% AutoTrader median × title_mult + 40% formula
    - If no comps: 100% formula
    Returns dict with full breakdown.
    """
    # Get our formula-based estimate
    formula_result = estimate_market_value(title, year, mileage, colour, brand_status)

    # Try to get AutoTrader comps
    try:
        comps = await fetch_autotrader_comps(title, year, mileage)
    except Exception:
        comps = {"prices": [], "median": None, "count": 0}

    at_median = comps.get("median")
    at_count = comps.get("count", 0)

    if at_median and at_count >= 3:
        # Apply title status discount to the AutoTrader median too
        # (AutoTrader shows clean title prices, our cars may be salvage)
        title_mult = formula_result["title_mult"]
        at_adjusted = at_median * title_mult

        # Blend: 60% AutoTrader + 40% formula
        blended = round(at_adjusted * 0.6 + formula_result["formula_value"] * 0.4, 0)
        blended = max(blended, 800)

        formula_result["market_value"] = blended
        formula_result["autotrader_median"] = at_median
        formula_result["autotrader_adjusted"] = round(at_adjusted, 0)
        formula_result["autotrader_count"] = at_count
        formula_result["autotrader_low"] = comps.get("low")
        formula_result["autotrader_high"] = comps.get("high")
        formula_result["blend_method"] = "autotrader_60_formula_40"
    elif at_median and at_count >= 1:
        # Few comps: 40% AutoTrader + 60% formula
        title_mult = formula_result["title_mult"]
        at_adjusted = at_median * title_mult

        blended = round(at_adjusted * 0.4 + formula_result["formula_value"] * 0.6, 0)
        blended = max(blended, 800)

        formula_result["market_value"] = blended
        formula_result["autotrader_median"] = at_median
        formula_result["autotrader_adjusted"] = round(at_adjusted, 0)
        formula_result["autotrader_count"] = at_count
        formula_result["autotrader_low"] = comps.get("low")
        formula_result["autotrader_high"] = comps.get("high")
        formula_result["blend_method"] = "autotrader_40_formula_60"
    else:
        formula_result["blend_method"] = "formula_only"

    return formula_result


def get_repair_range(damage_text: str, severity: str = "", is_salvage: bool = False) -> tuple:
    """
    Estimate repair cost range based on damage type, severity, and title status.
    Returns (low, high, breakdown_dict).
    """
    base_low = 0
    base_high = 0
    damage_source = "listed"

    if not damage_text or damage_text.strip() == "" or damage_text.upper() == "NONE":
        base_low, base_high = DEFAULT_REPAIR
        damage_source = "none"
    else:
        d = damage_text.upper().strip()
        matched = False
        # Direct match
        for key, val in REPAIR_COST_MAP.items():
            if key in d:
                base_low, base_high = val
                matched = True
                break
        if not matched:
            # Fuzzy matches
            if "ROLL" in d:
                base_low, base_high = 6000, 16000
            elif "FIRE" in d or "BURN" in d:
                base_low, base_high = 4000, 12000
            elif "FLOOD" in d or "WATER" in d:
                base_low, base_high = 4000, 12000
            elif "HIT" in d or "IMPACT" in d or "COLLISION" in d:
                base_low, base_high = 2500, 5500
            elif "RUST" in d:
                base_low, base_high = 1500, 4500
            elif "REAR" in d:
                base_low, base_high = 2000, 4500
            elif "SIDE" in d or "DOOR" in d:
                base_low, base_high = 1500, 3500
            elif "ROOF" in d:
                base_low, base_high = 2500, 6000
            else:
                base_low, base_high = 2000, 5000
                damage_source = "unknown_type"

    # Severity multiplier
    sev_mult = 1.0
    if severity:
        sev = severity.lower()
        if sev == "minor":
            sev_mult = 0.7
        elif sev == "moderate":
            sev_mult = 1.0
        elif sev == "severe":
            sev_mult = 1.4
        elif sev == "total":
            sev_mult = 1.8

    repair_low = round(base_low * sev_mult)
    repair_high = round(base_high * sev_mult)

    # Fixed costs
    safety = SAFETY_INSPECTION_COST
    salvage_process = REBUILT_TITLE_PROCESS if is_salvage else 0

    total_low = repair_low + safety + salvage_process
    total_high = repair_high + safety + salvage_process

    breakdown = {
        "repair_labour_parts_low": repair_low,
        "repair_labour_parts_high": repair_high,
        "safety_inspection": safety,
        "salvage_to_rebuilt_cost": salvage_process,
        "severity_applied": severity or "moderate",
        "damage_source": damage_source,
    }

    return total_low, total_high, breakdown


def calculate_ontario_fees(purchase_price: float, is_salvage: bool = False) -> dict:
    """
    Calculate all Ontario transaction fees.
    """
    hst = round(purchase_price * 0.13, 2)
    fees = {
        "hst": hst,
        "omvic": OMVIC_FEE,
        "mto_transfer": MTO_TRANSFER_FEE,
        "safety_cert": SAFETY_INSPECTION_COST,
        "total": round(hst + OMVIC_FEE + MTO_TRANSFER_FEE + SAFETY_INSPECTION_COST, 0),
    }
    return fees


def calc_deal_score(best_profit: float, worst_profit: float, roi_best: float = 0) -> tuple:
    """Enhanced deal scoring that factors in both profit amount and ROI."""
    avg_profit = (best_profit + worst_profit) / 2

    # Base score from average profit
    if avg_profit >= 5000:
        score = 10
    elif avg_profit >= 4000:
        score = 9
    elif avg_profit >= 3000:
        score = 8
    elif avg_profit >= 2000:
        score = 7
    elif avg_profit >= 1200:
        score = 6
    elif avg_profit >= 500:
        score = 5
    elif avg_profit >= 0:
        score = 4
    elif avg_profit >= -500:
        score = 3
    elif avg_profit >= -1500:
        score = 2
    else:
        score = 1

    # ROI bonus/penalty (±1 point)
    if roi_best and roi_best > 60:
        score = min(10, score + 1)
    elif roi_best and roi_best < -10:
        score = max(1, score - 1)

    # Risk penalty: if worst case is very negative
    if worst_profit < -2000 and score > 3:
        score = max(3, score - 1)

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
    price_part = text
    for split_word in ["AS IS", "PLUS", "Plus", "plus"]:
        if split_word in price_part:
            price_part = price_part.split(split_word)[0]
    price_part = price_part.strip()
    dollar_match = re.search(r'\$([\d.,]+)', price_part)
    if dollar_match:
        num_str = dollar_match.group(1)
        dot_count = num_str.count('.')
        if dot_count > 1:
            parts = num_str.split('.')
            if len(parts[-1]) == 2:
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
    ai_detected_count = 0
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
        colour = raw.get("colour", "")
        is_salvage = brand and "SALVAGE" in brand.upper()

        # AI Damage Detection: if no damage listed and photos exist, use vision AI
        ai_damage_result = None
        severity = ""
        if (not damage or damage.strip() == "") and (raw.get("photos") or raw.get("photo")):
            try:
                # Send up to 3 photos for better detection
                photos_to_analyze = raw.get("photos", [])[:3]
                if not photos_to_analyze and raw.get("photo"):
                    photos_to_analyze = [raw["photo"]]
                ai_damage_result = await detect_damage_from_photo(
                    photos_to_analyze,
                    source=raw.get("source", ""),
                    brand_status=brand
                )
                if ai_damage_result.get("confidence", 0) >= 0.4 and ai_damage_result.get("damage", "") not in ["", "NONE"]:
                    damage = ai_damage_result["damage"]
                    severity = ai_damage_result.get("severity", "")
                    ai_detected_count += 1
                    logger.info(f"  AI detected damage for {raw.get('title','')}: {damage} ({severity})")
            except Exception as e:
                logger.warning(f"  AI damage detection skipped: {e}")

        # Market value (blended — AutoTrader comps + formula)
        market_value = None
        mv_breakdown = None
        if year and raw.get("title"):
            mv_result = await estimate_market_value_blended(
                raw["title"], year, mileage,
                colour=colour, brand_status=brand
            )
            market_value = mv_result["market_value"]
            mv_breakdown = mv_result

        # Repair cost (enhanced — uses severity + salvage process costs)
        repair_low, repair_high, repair_breakdown = get_repair_range(
            damage, severity=severity, is_salvage=is_salvage
        )

        # Ontario fees
        profit_best = None
        profit_worst = None
        roi_best = None
        roi_worst = None
        fees = None
        fees_breakdown = None
        if price and price > 0 and market_value:
            fees_result = calculate_ontario_fees(price, is_salvage=is_salvage)
            fees = fees_result["total"]
            fees_breakdown = fees_result
            profit_best = round(market_value - price - repair_low - fees, 0)
            profit_worst = round(market_value - price - repair_high - fees, 0)
            roi_best = round((profit_best / price) * 100, 1) if price > 0 else None
            roi_worst = round((profit_worst / price) * 100, 1) if price > 0 else None

        # Deal score (enhanced — factors ROI)
        score = None
        score_label = None
        if profit_best is not None and profit_worst is not None:
            score, score_label = calc_deal_score(profit_best, profit_worst, roi_best or 0)

        listing_doc = {
            "url": url,
            "source": raw.get("source", ""),
            "title": raw.get("title", ""),
            "price": price,
            "price_raw": raw.get("price_raw", ""),
            "status": raw.get("status", "for_sale"),
            "colour": colour,
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
            # New v2 fields for transparency
            "calc_version": "v2.0",
            "mv_breakdown": mv_breakdown,
            "repair_breakdown": repair_breakdown,
            "fees_breakdown": fees_breakdown,
            "ai_damage_detected": bool(ai_damage_result and ai_damage_result.get("confidence", 0) >= 0.4 and ai_damage_result.get("damage", "") not in ["", "NONE"]),
            "ai_damage_details": ai_damage_result.get("details", "") if ai_damage_result and ai_damage_result.get("damage", "") not in ["", "NONE"] else "",
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
    logger.info(f"=== Scrape complete: {new_count} new, {updated_count} updated, {ai_detected_count} AI damage detections, {len(all_listings)} total ===")
    return {"new": new_count, "updated": updated_count, "total": len(all_listings), "ai_detections": ai_detected_count}


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
    # Load AutoTrader cache from DB
    await _load_at_cache_from_db()
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
    query = {}
    if status == "sold":
        query["is_inactive"] = True
    elif status:
        query["is_inactive"] = {"$ne": True}
        query["status"] = status
    else:
        query["is_inactive"] = {"$ne": True}
    if source:
        query["source"] = source
    if max_price is not None:
        query["price"] = {"$lte": max_price, "$gt": 0}
    if damage_type:
        query["damage"] = {"$regex": damage_type, "$options": "i"}
    if search:
        query["title"] = {"$regex": search, "$options": "i"}
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
        "date": lambda x: x.get("first_seen") or "",
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

@api_router.post("/fetch-comps")
async def fetch_comps_for_all():
    """Slowly fetch AutoTrader comps for all unique vehicles. Runs in background."""
    global _autotrader_request_count, _autotrader_last_reset
    _autotrader_request_count = 0
    _autotrader_last_reset = datetime.now()

    listings = await db.listings.find({}, {"_id": 0, "title": 1, "year": 1, "url": 1, "mileage": 1, "brand": 1, "colour": 1, "mv_breakdown": 1}).to_list(500)
    # Get unique make/model/year combos
    seen = set()
    unique = []
    for l in listings:
        title = l.get("title", "")
        year = l.get("year")
        if not title or not year:
            continue
        make_slug, model_slug = _extract_make_model(title.lower())
        if not make_slug or not model_slug:
            continue
        key = f"{make_slug}_{model_slug}_{year}"
        if key not in seen:
            seen.add(key)
            unique.append(l)

    logger.info(f"Fetching AutoTrader comps for {len(unique)} unique vehicles...")
    fetched = 0
    for l in unique:
        try:
            comps = await fetch_autotrader_comps(l["title"], l["year"], l.get("mileage"))
            if comps.get("median"):
                fetched += 1
                # Update all listings with this make/model/year
                make_slug, model_slug = _extract_make_model(l["title"].lower())
                for listing in listings:
                    lt = listing.get("title", "").lower()
                    ly = listing.get("year")
                    ms, mds = _extract_make_model(lt)
                    if ms == make_slug and mds == model_slug and ly == l["year"]:
                        brand = listing.get("brand", "")
                        colour = listing.get("colour", "")
                        mv_result = await estimate_market_value_blended(
                            listing["title"], listing["year"], listing.get("mileage"),
                            colour=colour, brand_status=brand
                        )
                        market_value = mv_result["market_value"]
                        # Recalculate profit
                        price = None
                        existing = await db.listings.find_one({"url": listing["url"]}, {"_id": 0, "price": 1, "repair_low": 1, "repair_high": 1})
                        if existing:
                            price = existing.get("price")
                            rl = existing.get("repair_low", 0)
                            rh = existing.get("repair_high", 0)
                            if price and price > 0:
                                fees_result = calculate_ontario_fees(price, is_salvage=brand and "SALVAGE" in brand.upper())
                                fees = fees_result["total"]
                                pb = round(market_value - price - rl - fees, 0)
                                pw = round(market_value - price - rh - fees, 0)
                                rb = round((pb / price) * 100, 1) if price > 0 else None
                                rw = round((pw / price) * 100, 1) if price > 0 else None
                                sc, sl = calc_deal_score(pb, pw, rb or 0)
                                await db.listings.update_one({"url": listing["url"]}, {"$set": {
                                    "market_value": market_value, "mv_breakdown": mv_result,
                                    "profit_best": pb, "profit_worst": pw,
                                    "roi_best": rb, "roi_worst": rw,
                                    "deal_score": sc, "deal_label": sl, "fees": fees,
                                }})
                            else:
                                await db.listings.update_one({"url": listing["url"]}, {"$set": {
                                    "market_value": market_value, "mv_breakdown": mv_result,
                                }})
            if comps.get("error") == "rate_limit_reached":
                break
        except Exception as e:
            logger.warning(f"  Comp fetch error: {e}")

    logger.info(f"AutoTrader comp fetch complete: {fetched}/{len(unique)} vehicles got comps")
    return {"unique_vehicles": len(unique), "comps_fetched": fetched}

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

@api_router.post("/recalculate")
async def recalculate_all():
    """Recalculate market value, repair cost, and profit for ALL listings (active + sold) using v2 engine."""
    listings = await db.listings.find({}, {"_id": 0}).to_list(500)
    updated = 0
    ai_count = 0
    for l in listings:
        year = l.get("year")
        mileage = l.get("mileage")
        price = l.get("price")
        damage = l.get("damage", "")
        brand = l.get("brand", "")
        colour = l.get("colour", "")
        is_salvage = brand and "SALVAGE" in brand.upper()

        # AI damage detection if no damage and photos exist
        severity = ""
        ai_damage_result = None
        if (not damage or damage.strip() == "") and (l.get("photos") or l.get("photo")):
            try:
                photos_to_analyze = l.get("photos", [])[:3]
                if not photos_to_analyze and l.get("photo"):
                    photos_to_analyze = [l["photo"]]
                ai_damage_result = await detect_damage_from_photo(
                    photos_to_analyze,
                    source=l.get("source", ""),
                    brand_status=brand
                )
                if ai_damage_result.get("confidence", 0) >= 0.4 and ai_damage_result.get("damage", "") not in ["", "NONE"]:
                    damage = ai_damage_result["damage"]
                    severity = ai_damage_result.get("severity", "")
                    ai_count += 1
            except Exception:
                pass

        market_value = None
        mv_breakdown = None
        if year and l.get("title"):
            mv_result = await estimate_market_value_blended(l["title"], year, mileage, colour=colour, brand_status=brand)
            market_value = mv_result["market_value"]
            mv_breakdown = mv_result

        repair_low, repair_high, repair_breakdown = get_repair_range(damage, severity=severity, is_salvage=is_salvage)

        profit_best = profit_worst = roi_best = roi_worst = fees = None
        fees_breakdown = None
        if price and price > 0 and market_value:
            fees_result = calculate_ontario_fees(price, is_salvage=is_salvage)
            fees = fees_result["total"]
            fees_breakdown = fees_result
            profit_best = round(market_value - price - repair_low - fees, 0)
            profit_worst = round(market_value - price - repair_high - fees, 0)
            roi_best = round((profit_best / price) * 100, 1) if price > 0 else None
            roi_worst = round((profit_worst / price) * 100, 1) if price > 0 else None

        score = score_label = None
        if profit_best is not None and profit_worst is not None:
            score, score_label = calc_deal_score(profit_best, profit_worst, roi_best or 0)

        update_doc = {
            "damage": damage,
            "market_value": market_value,
            "repair_low": repair_low, "repair_high": repair_high,
            "fees": fees,
            "profit_best": profit_best, "profit_worst": profit_worst,
            "roi_best": roi_best, "roi_worst": roi_worst,
            "deal_score": score, "deal_label": score_label,
            "calc_version": "v2.0",
            "mv_breakdown": mv_breakdown,
            "repair_breakdown": repair_breakdown,
            "fees_breakdown": fees_breakdown,
            "ai_damage_detected": bool(ai_damage_result and ai_damage_result.get("confidence", 0) >= 0.4 and ai_damage_result.get("damage", "") not in ["", "NONE"]),
            "ai_damage_details": ai_damage_result.get("details", "") if ai_damage_result and ai_damage_result.get("damage", "") not in ["", "NONE"] else "",
        }
        await db.listings.update_one({"url": l["url"]}, {"$set": update_doc})
        updated += 1

    return {"updated": updated, "ai_damage_detections": ai_count}

@api_router.get("/calc-methodology")
async def get_calc_methodology():
    """Return the complete calculation methodology documentation."""
    return {
        "version": "2.1",
        "engine": "AutoFlip Enhanced Calculation Engine v2.1 (Blended)",
        "market_value": {
            "description": "Blended market value: AutoTrader.ca real comparables + multi-factor formula",
            "blending": {
                "description": "When AutoTrader comps available: 60% AutoTrader median + 40% formula. With few comps (1-2): 40% AT + 60% formula. No comps: 100% formula.",
                "autotrader": "Scrapes AutoTrader.ca Ontario listings for same make/model/year (±1 year). Extracts median asking price from real dealer listings. Title status discount applied to AT prices.",
                "formula": "MSRP × Depreciation × Brand × BodyType × Trim × Color × Mileage × TitleStatus",
                "cache": "AutoTrader results cached for 6 hours to avoid excessive requests.",
            },
            "factors": [
                {"name": "MSRP Baseline", "description": "Looks up the vehicle's approximate new MSRP from a database of 100+ models. If no exact match, estimates from brand + body type."},
                {"name": "Depreciation Curve", "description": "Applies a non-linear depreciation curve based on Canadian Black Book industry data. Year 1 loses ~18%, then gradual decline. 5-year-old car retains ~48% of MSRP."},
                {"name": "Brand Retention", "description": "Each brand has a retention multiplier. Toyota (1.18) and Lexus (1.22) hold value best. Dodge (0.88) and Fiat (0.68) lose value fastest."},
                {"name": "Body Type Demand", "description": "Ontario market demand: trucks (1.30x), off-road SUVs (1.20x), compact SUVs (1.15x), sedans (0.95x). Trucks and SUVs command premiums in Canadian winters."},
                {"name": "Trim Level", "description": "Higher trims add value: Limited/Platinum (1.25x), Sport/GT (1.15x), XLT/EX (1.10x), Base (1.05x)."},
                {"name": "Color Premium", "description": "Neutral colors sell faster: White (+4%), Black (+3%), Silver/Grey (+2%). Unusual colors (yellow -9%, pink -12%) are harder to sell."},
                {"name": "Mileage Adjustment", "description": "Uses Ontario average of 18,000 km/year. Cars with <50% expected mileage get +8%. Cars with >200% expected get -18% or more. Continuous curve, not step function."},
                {"name": "Title Status", "description": "Salvage title: 55% of clean value (buyers pay less for salvage history). Rebuilt title: 75% of clean value. Clean: full value."},
            ],
            "formula": "Market Value = MSRP × Depreciation × Brand × BodyType × Trim × Color × Mileage × TitleStatus",
        },
        "repair_cost": {
            "description": "Damage-specific repair cost estimation using Ontario body shop rates ($110-130/hr)",
            "factors": [
                {"name": "Damage Zone", "description": "16 specific damage zones mapped (Front, Rear, Left/Right Front, Left/Right Rear, Doors, Rollover, Fire, Flood, Roof, Undercarriage). Each has a research-based low-high cost range."},
                {"name": "Severity Multiplier", "description": "AI vision or description analysis determines severity: Minor (0.7x), Moderate (1.0x), Severe (1.4x), Total (1.8x)."},
                {"name": "Salvage-to-Rebuilt Process", "description": "Salvage vehicles require: Structural Inspection ($400), VIN Verification ($75), Appraisal ($150) = $625 additional cost on top of repairs."},
                {"name": "Safety Inspection", "description": "Mandatory Ontario Safety Standards Certificate: $100."},
                {"name": "AI Damage Detection", "description": "When damage type is not listed, GPT-4o vision analyzes the car photo to identify damage zone and severity. Only used when confidence ≥ 40%."},
            ],
            "formula": "Total Repair = (Base Repair × Severity) + Safety ($100) + Salvage Process ($625 if salvage)",
        },
        "ontario_fees": {
            "description": "All mandatory Ontario transaction fees",
            "breakdown": [
                {"name": "HST", "amount": "13% of purchase price", "description": "Ontario Harmonized Sales Tax"},
                {"name": "OMVIC Fee", "amount": "$22", "description": "Ontario Motor Vehicle Industry Council registration"},
                {"name": "MTO Transfer", "amount": "$32", "description": "Ministry of Transportation ownership transfer"},
                {"name": "Safety Certificate", "amount": "$100", "description": "Mandatory safety inspection for resale"},
            ],
            "formula": "Fees = (Price × 0.13) + $22 + $32 + $100",
        },
        "profit_calculation": {
            "formula": "Profit = Market Value - Purchase Price - Repair Cost - Ontario Fees",
            "scenarios": {
                "best_case": "Uses low repair estimate",
                "worst_case": "Uses high repair estimate",
            },
        },
        "deal_scoring": {
            "description": "1-10 score based on average profit + ROI bonus/penalty + risk factor",
            "scale": [
                {"range": "8-10", "label": "BUY", "criteria": "Average profit ≥ $3,000+. Strong flip opportunity."},
                {"range": "5-7", "label": "WATCH", "criteria": "Average profit $500-$3,000. Monitor for price drops."},
                {"range": "1-4", "label": "SKIP", "criteria": "Average profit < $500 or negative. Risk of loss."},
            ],
            "adjustments": [
                "ROI > 60%: +1 point bonus",
                "ROI < -10%: -1 point penalty",
                "Worst case loss > $2,000: -1 point risk penalty",
            ],
        },
        "technologies": [
            "Python/FastAPI backend with async processing",
            "BeautifulSoup4 + httpx for web scraping",
            "AutoTrader.ca real-time comparable pricing (scraped, 6hr cache)",
            "GPT-4o Vision API (via Emergent Integrations) for AI damage detection from photos",
            "MongoDB for data persistence",
            "Canadian Black Book-inspired depreciation curves",
            "Ontario-specific fee schedules and market data",
            "Blended valuation: 60% real market comps + 40% formula (with fallback)",
        ],
    }

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
