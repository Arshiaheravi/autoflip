import re
import logging
import random
import asyncio
from datetime import datetime
from typing import Optional
import httpx
from bs4 import BeautifulSoup
from ..database import db

logger = logging.getLogger(__name__)

_autotrader_cache = {}
AUTOTRADER_CACHE_TTL = 3600 * 24
_autotrader_request_count = 0
_autotrader_last_reset = datetime.now()
AUTOTRADER_MAX_REQUESTS_PER_CYCLE = 10
AUTOTRADER_DELAY_MIN = 4.0
AUTOTRADER_DELAY_MAX = 8.0

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

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


def extract_make_model(title_lower: str) -> tuple:
    """Extract make and model slugs from a listing title for AutoTrader search."""
    make_slug = None
    model_slug = None

    best_make_len = 0
    for make, slug in MAKE_SLUGS.items():
        if make in title_lower and len(make) > best_make_len:
            make_slug = slug
            best_make_len = len(make)

    best_model_len = 0
    for model, slug in MODEL_SLUGS.items():
        if len(model) <= 3:
            if re.search(r'\b' + re.escape(model) + r'\b', title_lower):
                if len(model) > best_model_len:
                    model_slug = slug
                    best_model_len = len(model)
        else:
            if model in title_lower and len(model) > best_model_len:
                model_slug = slug
                best_model_len = len(model)

    return make_slug, model_slug


async def load_at_cache_from_db():
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


async def fetch_autotrader_comps(title: str, year: int, mileage: int = None) -> dict:
    """Fetch comparable vehicle prices from AutoTrader.ca for Ontario."""
    global _autotrader_request_count, _autotrader_last_reset

    title_lower = title.lower()
    make_slug, model_slug = extract_make_model(title_lower)

    if not make_slug or not model_slug:
        return {"prices": [], "median": None, "count": 0, "source": "autotrader", "error": "no_make_model_match"}

    cache_key = f"{make_slug}_{model_slug}_{year}"
    now = datetime.now()

    if (now - _autotrader_last_reset).total_seconds() > 1800:
        _autotrader_request_count = 0
        _autotrader_last_reset = now

    if cache_key in _autotrader_cache:
        cached = _autotrader_cache[cache_key]
        age_sec = (now - cached["fetched_at"]).total_seconds()
        if age_sec < AUTOTRADER_CACHE_TTL:
            return cached["result"]

    if _autotrader_request_count >= AUTOTRADER_MAX_REQUESTS_PER_CYCLE:
        return {"prices": [], "median": None, "count": 0, "source": "autotrader", "error": "rate_limit_reached"}

    delay = random.uniform(AUTOTRADER_DELAY_MIN, AUTOTRADER_DELAY_MAX)
    await asyncio.sleep(delay)
    _autotrader_request_count += 1

    year_low = max(year - 1, 2000)
    year_high = year + 1
    url = f"https://www.autotrader.ca/cars/{make_slug}/{model_slug}/on/?rcp=15&rcs=0&srt=35&yRng={year_low}%2C{year_high}&prx=-1&prv=Ontario&loc=Toronto%2C+ON"

    try:
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


async def estimate_market_value_blended(title: str, year: int, mileage: int = None,
                                        colour: str = "", brand_status: str = "") -> dict:
    """Blended market value: AutoTrader.ca real comps + formula."""
    from .calculations import estimate_market_value

    formula_result = estimate_market_value(title, year, mileage, colour, brand_status)

    try:
        comps = await fetch_autotrader_comps(title, year, mileage)
    except Exception:
        comps = {"prices": [], "median": None, "count": 0}

    at_median = comps.get("median")
    at_count = comps.get("count", 0)

    if at_median and at_count >= 3:
        title_mult = formula_result["title_mult"]
        at_adjusted = at_median * title_mult
        blended = round(at_adjusted * 0.6 + formula_result["formula_value"] * 0.4, 0)
        blended = max(blended, 800)
        formula_result.update({
            "market_value": blended,
            "autotrader_median": at_median,
            "autotrader_adjusted": round(at_adjusted, 0),
            "autotrader_count": at_count,
            "autotrader_low": comps.get("low"),
            "autotrader_high": comps.get("high"),
            "blend_method": "autotrader_60_formula_40",
        })
    elif at_median and at_count >= 1:
        title_mult = formula_result["title_mult"]
        at_adjusted = at_median * title_mult
        blended = round(at_adjusted * 0.4 + formula_result["formula_value"] * 0.6, 0)
        blended = max(blended, 800)
        formula_result.update({
            "market_value": blended,
            "autotrader_median": at_median,
            "autotrader_adjusted": round(at_adjusted, 0),
            "autotrader_count": at_count,
            "autotrader_low": comps.get("low"),
            "autotrader_high": comps.get("high"),
            "blend_method": "autotrader_40_formula_60",
        })
    else:
        formula_result["blend_method"] = "formula_only"

    return formula_result
