from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
import json
import asyncio
from datetime import datetime, timezone, timedelta

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─── WebSocket Manager ───
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# ─── Pydantic Models ───
class ListingCreate(BaseModel):
    source: str
    external_id: str = ""
    url: str
    title: str
    price: float
    price_raw_text: str = ""
    status: str = "for_sale"
    colour: str = ""
    mileage: int = 0
    damage_text: str = ""
    brand_text: str = ""
    description: str = ""
    photos: List[str] = []

class WatchlistAdd(BaseModel):
    listing_id: str
    notes: str = ""
    tags: List[str] = []

class WatchlistUpdate(BaseModel):
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

class PortfolioCreate(BaseModel):
    listing_id: Optional[str] = None
    vehicle_description: str
    buy_date: str
    buy_price: float
    repair_items: List[Dict[str, Any]] = []
    sale_date: Optional[str] = None
    sale_price: Optional[float] = None
    notes: str = ""

class PortfolioUpdate(BaseModel):
    repair_items: Optional[List[Dict[str, Any]]] = None
    sale_date: Optional[str] = None
    sale_price: Optional[float] = None
    notes: Optional[str] = None

class SettingsUpdate(BaseModel):
    alert_filters: Optional[Dict[str, Any]] = None
    telegram_chat_id: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    twilio_sid: Optional[str] = None
    twilio_token: Optional[str] = None
    twilio_from: Optional[str] = None
    twilio_to: Optional[str] = None
    sendgrid_key: Optional[str] = None
    sendgrid_to_email: Optional[str] = None
    diy_mode: Optional[bool] = None
    shop_rate: Optional[float] = None
    available_capital: Optional[float] = None
    notifications_telegram: Optional[bool] = None
    notifications_sms: Optional[bool] = None
    notifications_email: Optional[bool] = None

# ─── Profit Calculation Engine ───
REPAIR_COST_MAP = {
    "LEFT REAR": [1800, 3500],
    "RIGHT REAR": [1800, 3500],
    "FRONT": [2500, 6000],
    "RIGHT FRONT": [2000, 4500],
    "LEFT FRONT": [2000, 4500],
    "FRONT END": [3000, 7000],
    "RIGHT DOORS": [1500, 3200],
    "LEFT DOORS": [1500, 3200],
    "ROLLOVER": [5000, 15000],
    "FIRE": [4000, 12000],
    "FLOOD": [3000, 10000],
    "UNKNOWN": [2000, 8000],
    "": [2000, 8000],
}

SEASONAL_PEAKS = {
    "suv": {"peak_months": [10, 11], "multiplier": 1.12, "label": "October-November"},
    "truck": {"peak_months": [10, 11], "multiplier": 1.12, "label": "October-November"},
    "awd": {"peak_months": [10, 11], "multiplier": 1.12, "label": "October-November"},
    "convertible": {"peak_months": [4, 5], "multiplier": 1.15, "label": "April-May"},
    "sports": {"peak_months": [4, 5], "multiplier": 1.15, "label": "April-May"},
    "sedan": {"peak_months": [3, 4], "multiplier": 1.08, "label": "March-April"},
    "hatchback": {"peak_months": [3, 4], "multiplier": 1.08, "label": "March-April"},
    "coupe": {"peak_months": [4, 5], "multiplier": 1.10, "label": "April-May"},
    "van": {"peak_months": [5, 6], "multiplier": 1.06, "label": "May-June"},
    "wagon": {"peak_months": [3, 4], "multiplier": 1.08, "label": "March-April"},
}

def detect_vehicle_type(title: str) -> str:
    title_lower = title.lower()
    for vtype in ["suv", "truck", "convertible", "sports", "hatchback", "coupe", "van", "wagon", "sedan"]:
        if vtype in title_lower:
            return vtype
    awd_keywords = ["awd", "4wd", "4x4", "forester", "outback", "rav4", "crv", "cr-v", "cx-5", "tucson", "santa fe", "rogue", "equinox", "escape"]
    for kw in awd_keywords:
        if kw in title_lower:
            return "awd"
    suv_keywords = ["explorer", "highlander", "pathfinder", "pilot", "tahoe", "suburban", "4runner", "wrangler"]
    for kw in suv_keywords:
        if kw in title_lower:
            return "suv"
    truck_keywords = ["f-150", "f150", "silverado", "ram", "sierra", "tundra", "tacoma", "frontier", "ranger", "colorado"]
    for kw in truck_keywords:
        if kw in title_lower:
            return "truck"
    return "sedan"

def get_repair_costs(damage_text: str, ai_analysis: dict = None, diy_mode: bool = False) -> tuple:
    damage_upper = damage_text.upper().strip()
    best, worst = REPAIR_COST_MAP.get(damage_upper, REPAIR_COST_MAP["UNKNOWN"])
    if ai_analysis:
        if ai_analysis.get("airbag_status") == "deployed":
            best += 2000; worst += 4500
        if ai_analysis.get("frame_damage_suspected"):
            best += 3000; worst += 8000
        if ai_analysis.get("rust_detected"):
            best += 500; worst += 3000
        adj = ai_analysis.get("ai_repair_cost_adjustment", 0)
        best += adj; worst += adj
    if diy_mode:
        best = int(best * 0.4)
        worst = int(worst * 0.4)
    best += 100; worst += 100
    return best, worst

def calculate_ontario_fees(purchase_price: float) -> float:
    hst = purchase_price * 0.13
    return hst + 22 + 32 + 100 + 90

def get_brand_discount(brand_text: str) -> float:
    brand_upper = brand_text.upper()
    if "SALVAGE" in brand_upper:
        return 0.625
    elif "CLEAN" in brand_upper or "NONE" in brand_upper or "BRAND NONE" in brand_upper:
        return 0.775
    return 0.70

def calculate_profit(listing: dict, market_value: float = None, ai_analysis: dict = None, diy_mode: bool = False) -> dict:
    price = listing.get("price", 0)
    if not market_value:
        market_value = price * 2.2
    brand_factor = get_brand_discount(listing.get("brand_text", ""))
    flip_price = market_value * brand_factor
    mileage = listing.get("mileage", 0)
    if mileage > 100000:
        penalty = ((mileage - 100000) / 10000) * 150
        flip_price -= penalty
    title = listing.get("title", "")
    trim_premiums = {"TYPE-R": 3000, "TYPE R": 3000, "SI": 1500, "SPORT": 800, "TOURING": 1200, "LIMITED": 1500, "GT": 1000, "SE": 500, "EX": 600, "EX-L": 900}
    for trim, premium in trim_premiums.items():
        if trim in title.upper():
            flip_price += premium
            break
    repair_best, repair_worst = get_repair_costs(listing.get("damage_text", ""), ai_analysis, diy_mode)
    total_fees = calculate_ontario_fees(price)
    net_profit_best = flip_price - price - repair_best - total_fees
    net_profit_worst = flip_price - price - repair_worst - total_fees
    roi_best = (net_profit_best / price * 100) if price > 0 else 0
    roi_worst = (net_profit_worst / price * 100) if price > 0 else 0
    profit_per_day = net_profit_best / 30 if net_profit_best > 0 else 0
    vehicle_type = detect_vehicle_type(title)
    seasonal_info = SEASONAL_PEAKS.get(vehicle_type, SEASONAL_PEAKS["sedan"])
    current_month = datetime.now(timezone.utc).month
    seasonal_hold_advice = None
    seasonal_hold_extra = 0
    if current_month not in seasonal_info["peak_months"]:
        seasonal_flip = flip_price * seasonal_info["multiplier"]
        seasonal_hold_extra = seasonal_flip - flip_price
        seasonal_hold_advice = f"Hold until {seasonal_info['label']} for +${seasonal_hold_extra:,.0f} extra profit"
    return {
        "market_value": round(market_value, 2),
        "comparable_count": 12,
        "flip_price": round(flip_price, 2),
        "repair_best": repair_best,
        "repair_worst": repair_worst,
        "total_fees": round(total_fees, 2),
        "net_profit_best": round(net_profit_best, 2),
        "net_profit_worst": round(net_profit_worst, 2),
        "roi_best": round(roi_best, 1),
        "roi_worst": round(roi_worst, 1),
        "profit_per_day": round(profit_per_day, 2),
        "seasonal_hold_advice": seasonal_hold_advice,
        "seasonal_hold_extra_profit": round(seasonal_hold_extra, 2),
        "vehicle_type": vehicle_type,
    }

# ─── Deal Scoring Algorithm ───
def calculate_deal_score(listing: dict, profit_calc: dict, ai_analysis: dict = None) -> dict:
    profit_score = 0
    npb = profit_calc.get("net_profit_best", 0)
    if npb >= 5000: profit_score = 35
    elif npb >= 3500: profit_score = 28
    elif npb >= 2500: profit_score = 22
    elif npb >= 1500: profit_score = 14
    elif npb >= 500: profit_score = 7

    comp_count = profit_calc.get("comparable_count", 20)
    if comp_count <= 5: demand_score = 25
    elif comp_count <= 15: demand_score = 20
    elif comp_count <= 30: demand_score = 14
    elif comp_count <= 50: demand_score = 8
    else: demand_score = 4

    repair_score = 14
    if ai_analysis:
        sev = ai_analysis.get("damage_severity", "moderate")
        if sev == "minor": repair_score = 20
        elif sev == "moderate": repair_score = 14
        elif sev == "severe": repair_score = 7
        elif sev == "structural": repair_score = 0
        if ai_analysis.get("frame_damage_suspected"): repair_score = max(0, repair_score - 8)
        if ai_analysis.get("airbag_status") == "deployed": repair_score = max(0, repair_score - 5)
        if ai_analysis.get("rust_detected"): repair_score = max(0, repair_score - 3)
    else:
        damage = listing.get("damage_text", "").upper()
        if damage in ["LEFT REAR", "RIGHT REAR"]: repair_score = 18
        elif damage in ["RIGHT DOORS", "LEFT DOORS"]: repair_score = 16
        elif damage in ["FRONT", "RIGHT FRONT", "LEFT FRONT"]: repair_score = 12
        elif damage in ["FRONT END"]: repair_score = 8
        elif damage in ["ROLLOVER", "FIRE", "FLOOD"]: repair_score = 4

    current_month = datetime.now(timezone.utc).month
    vehicle_type = detect_vehicle_type(listing.get("title", ""))
    seasonal = SEASONAL_PEAKS.get(vehicle_type, SEASONAL_PEAKS["sedan"])
    peak = seasonal["peak_months"]
    if current_month in peak: timing_score = 20
    elif any(abs(current_month - p) == 1 or abs(current_month - p) == 11 for p in peak): timing_score = 16
    elif any(abs(current_month - p) == 2 or abs(current_month - p) == 10 for p in peak): timing_score = 12
    else: timing_score = 8

    total = profit_score + demand_score + repair_score + timing_score

    recommendation = "SKIP"
    if total >= 70: recommendation = "BUY NOW"
    elif total >= 45: recommendation = "WATCH"

    npw = profit_calc.get("net_profit_worst", 0)
    red_flags = []
    if ai_analysis and ai_analysis.get("frame_damage_suspected") and ai_analysis.get("damage_severity") == "structural":
        recommendation = "SKIP"
        red_flags.append("Structural frame damage detected")
    if npw < 0:
        recommendation = "SKIP"
        red_flags.append("Negative profit in worst case scenario")
    if listing.get("price", 0) > 20000 and "SALVAGE" in listing.get("brand_text", "").upper():
        recommendation = "SKIP"
        red_flags.append("High capital risk on salvage title")

    return {
        "deal_score": total,
        "recommendation": recommendation,
        "score_breakdown": {
            "profit_margin": profit_score,
            "market_demand": demand_score,
            "repair_risk": repair_score,
            "timing": timing_score,
        },
        "red_flags": red_flags,
    }

# ─── Seed Data ───
SEED_LISTINGS = [
    {"source": "cathcart_rebuilders", "external_id": "cr-001", "url": "https://cathcartauto.com/vehicles/inventory/2017-honda-civic-hatchback/", "title": "2017 HONDA CIVIC HATCHBACK", "price": 5995, "price_raw_text": "$5,995.00 AS IS PLUS HST", "status": "for_sale", "colour": "WHITE", "mileage": 87000, "damage_text": "LEFT REAR", "brand_text": "CLEAN - NONE", "description": "Clean title, minor rear quarter panel damage. Runs and drives.", "photos": ["https://images.unsplash.com/photo-1679353472026-3433cd13e820?w=600", "https://images.unsplash.com/photo-1619767886558-efdc259cde1a?w=600"]},
    {"source": "cathcart_rebuilders", "external_id": "cr-002", "url": "https://cathcartauto.com/vehicles/inventory/2019-toyota-corolla-se/", "title": "2019 TOYOTA COROLLA SE", "price": 8500, "price_raw_text": "$8,500.00 AS IS PLUS HST", "status": "for_sale", "colour": "SILVER", "mileage": 62000, "damage_text": "FRONT", "brand_text": "SALVAGE", "description": "Front end collision. Airbags intact. Engine runs.", "photos": ["https://images.unsplash.com/photo-1621007690695-0e49ab94bf9e?w=600"]},
    {"source": "cathcart_rebuilders", "external_id": "cr-003", "url": "https://cathcartauto.com/vehicles/inventory/2020-mazda-cx5-gt/", "title": "2020 MAZDA CX-5 GT AWD", "price": 12995, "price_raw_text": "$12,995.00 AS IS PLUS HST", "status": "for_sale", "colour": "RED", "mileage": 45000, "damage_text": "RIGHT FRONT", "brand_text": "CLEAN - NONE", "description": "GT trim with leather, sunroof. Minor right front damage.", "photos": ["https://images.unsplash.com/photo-1606611013016-969c19ba16eb?w=600"]},
    {"source": "cathcart_rebuilders", "external_id": "cr-004", "url": "https://cathcartauto.com/vehicles/inventory/2018-subaru-wrx/", "title": "2018 SUBARU WRX SPORT", "price": 9500, "price_raw_text": "$9,500.00 AS IS PLUS HST", "status": "coming_soon", "colour": "BLUE", "mileage": 95000, "damage_text": "LEFT FRONT", "brand_text": "CLEAN - NONE", "description": "Sport package. Left front damage to fender and bumper.", "photos": ["https://images.unsplash.com/photo-1580273916550-e323be2ae537?w=600"]},
    {"source": "cathcart_used", "external_id": "cu-001", "url": "https://cathcartauto.com/vehicles/inventory/2021-hyundai-elantra/", "title": "2021 HYUNDAI ELANTRA PREFERRED", "price": 15900, "price_raw_text": "$15,900.00 PLUS HST", "status": "for_sale", "colour": "BLACK", "mileage": 38000, "damage_text": "", "brand_text": "CLEAN - NONE", "description": "One owner, clean carfax. Preferred trim with safety features.", "photos": ["https://images.unsplash.com/photo-1617469767053-d3b523a0b982?w=600"]},
    {"source": "cathcart_used", "external_id": "cu-002", "url": "https://cathcartauto.com/vehicles/inventory/2020-kia-forte-ex/", "title": "2020 KIA FORTE EX", "price": 13500, "price_raw_text": "$13,500.00 PLUS HST", "status": "for_sale", "colour": "GREY", "mileage": 52000, "damage_text": "", "brand_text": "CLEAN - NONE", "description": "EX trim with heated seats, apple carplay.", "photos": ["https://images.unsplash.com/photo-1605559424843-9e4c228bf1c2?w=600"]},
    {"source": "picnsave", "external_id": "ps-001", "url": "https://picnsave.ca/product/2019-subaru-forester-2-5i/", "title": "2019 SUBARU FORESTER 2.5i", "price": 11900, "price_raw_text": "$11,900.00", "status": "for_sale", "colour": "GREEN", "mileage": 81457, "damage_text": "FRONT END", "brand_text": "BRAND NONE", "description": "AWD, front end collision damage. Runs and drives.", "photos": ["https://images.unsplash.com/photo-1609521263047-f8f205293f24?w=600"]},
    {"source": "picnsave", "external_id": "ps-002", "url": "https://picnsave.ca/product/2020-honda-cr-v-ex/", "title": "2020 HONDA CR-V EX AWD", "price": 14500, "price_raw_text": "$14,500.00", "status": "for_sale", "colour": "WHITE", "mileage": 55000, "damage_text": "RIGHT REAR", "brand_text": "CLEAN TITLE", "description": "EX trim AWD. Minor right rear quarter damage.", "photos": ["https://images.unsplash.com/photo-1568844293986-8d0400f8318a?w=600"]},
    {"source": "picnsave", "external_id": "ps-003", "url": "https://picnsave.ca/product/2017-ford-escape-se/", "title": "2017 FORD ESCAPE SE AWD", "price": 6500, "price_raw_text": "$6,500.00", "status": "for_sale", "colour": "BLUE", "mileage": 120000, "damage_text": "LEFT DOORS", "brand_text": "BRAND NONE", "description": "SE AWD. Left side door damage. High mileage but runs well.", "photos": ["https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=600"]},
    {"source": "picnsave", "external_id": "ps-004", "url": "https://picnsave.ca/product/2021-toyota-rav4-le/", "title": "2021 TOYOTA RAV4 LE AWD", "price": 16500, "price_raw_text": "$16,500.00", "status": "for_sale", "colour": "BLACK", "mileage": 42000, "damage_text": "FRONT", "brand_text": "CLEAN TITLE", "description": "LE AWD. Front collision damage. Low mileage.", "photos": ["https://images.unsplash.com/photo-1581235720704-06d3acfcb36f?w=600"]},
    {"source": "cathcart_rebuilders", "external_id": "cr-005", "url": "https://cathcartauto.com/vehicles/inventory/2016-bmw-328i/", "title": "2016 BMW 328i SPORT", "price": 7995, "price_raw_text": "$7,995.00 AS IS PLUS HST", "status": "for_sale", "colour": "BLACK", "mileage": 110000, "damage_text": "RIGHT DOORS", "brand_text": "SALVAGE", "description": "Sport line, right side door impact. Interior good condition.", "photos": ["https://images.unsplash.com/photo-1555215695-3004980ad54e?w=600"]},
    {"source": "picnsave", "external_id": "ps-005", "url": "https://picnsave.ca/product/2018-chevrolet-equinox-lt/", "title": "2018 CHEVROLET EQUINOX LT AWD", "price": 8900, "price_raw_text": "$8,900.00", "status": "for_sale", "colour": "SILVER", "mileage": 78000, "damage_text": "FRONT", "brand_text": "BRAND NONE", "description": "LT AWD. Front impact, bumper and hood. Runs and drives.", "photos": ["https://images.unsplash.com/photo-1549317661-bd32c8ce0afa?w=600"]},
]

SEED_AI_ANALYSES = {
    "cr-001": {"damage_severity": "minor", "damage_zones": ["left rear quarter panel", "rear bumper"], "hidden_damage_flags": [], "airbag_status": "intact", "interior_condition": "good", "rust_detected": False, "rust_locations": [], "frame_damage_suspected": False, "missing_parts": [], "photo_count_analyzed": 2, "confidence_level": "high", "ai_repair_cost_adjustment": 0, "summary": "Minor left rear damage. Quarter panel dent and bumper scuff. Clean buy.", "red_flags": []},
    "cr-002": {"damage_severity": "moderate", "damage_zones": ["front bumper", "hood", "right fender"], "hidden_damage_flags": ["radiator support may be bent"], "airbag_status": "intact", "interior_condition": "good", "rust_detected": False, "rust_locations": [], "frame_damage_suspected": False, "missing_parts": ["front bumper cover"], "photo_count_analyzed": 1, "confidence_level": "medium", "ai_repair_cost_adjustment": 500, "summary": "Moderate front damage. Bumper, hood, fender affected. Airbags intact. Radiator support check recommended.", "red_flags": ["Radiator support may need replacement"]},
    "cr-003": {"damage_severity": "minor", "damage_zones": ["right front fender", "right headlight"], "hidden_damage_flags": [], "airbag_status": "intact", "interior_condition": "excellent", "rust_detected": False, "rust_locations": [], "frame_damage_suspected": False, "missing_parts": [], "photo_count_analyzed": 1, "confidence_level": "high", "ai_repair_cost_adjustment": 0, "summary": "Minor right front damage. Fender and headlight only. GT trim with excellent interior. Strong buy.", "red_flags": []},
    "ps-001": {"damage_severity": "severe", "damage_zones": ["front bumper", "hood", "both fenders", "radiator"], "hidden_damage_flags": ["possible subframe damage"], "airbag_status": "intact", "interior_condition": "good", "rust_detected": False, "rust_locations": [], "frame_damage_suspected": True, "missing_parts": ["front bumper", "hood insulation"], "photo_count_analyzed": 1, "confidence_level": "medium", "ai_repair_cost_adjustment": 1500, "summary": "Severe front end damage. Multiple panels, possible subframe involvement. In-person inspection recommended.", "red_flags": ["Possible subframe damage", "Multiple panels need replacement"]},
    "ps-002": {"damage_severity": "minor", "damage_zones": ["right rear quarter panel"], "hidden_damage_flags": [], "airbag_status": "intact", "interior_condition": "excellent", "rust_detected": False, "rust_locations": [], "frame_damage_suspected": False, "missing_parts": [], "photo_count_analyzed": 1, "confidence_level": "high", "ai_repair_cost_adjustment": 0, "summary": "Minor right rear quarter panel dent. Excellent interior. EX AWD - strong resale.", "red_flags": []},
}

async def seed_database():
    existing = await db.listings.count_documents({})
    if existing > 0:
        return
    logger.info("Seeding database with demo listings...")
    now = datetime.now(timezone.utc)
    for i, seed in enumerate(SEED_LISTINGS):
        listing_id = str(uuid.uuid4())
        first_seen = now - timedelta(days=i % 7, hours=i * 3)
        doc = {
            "id": listing_id,
            "source": seed["source"],
            "external_id": seed["external_id"],
            "url": seed["url"],
            "title": seed["title"],
            "price": seed["price"],
            "price_raw_text": seed["price_raw_text"],
            "status": seed["status"],
            "colour": seed["colour"],
            "mileage": seed["mileage"],
            "damage_text": seed["damage_text"],
            "brand_text": seed["brand_text"],
            "description": seed["description"],
            "photos": seed["photos"],
            "first_seen_at": first_seen.isoformat(),
            "last_checked_at": now.isoformat(),
            "is_active": True,
            "price_history": [{"price": seed["price"], "timestamp": first_seen.isoformat()}],
        }
        await db.listings.insert_one(doc)

        # Calculate profit
        ai = SEED_AI_ANALYSES.get(seed["external_id"])
        profit = calculate_profit(doc, ai_analysis=ai)
        score_data = calculate_deal_score(doc, profit, ai)
        profit_doc = {
            "id": str(uuid.uuid4()),
            "listing_id": listing_id,
            **profit,
            **score_data,
            "calculated_at": now.isoformat(),
        }
        await db.profit_calculations.insert_one(profit_doc)

        # Seed AI analysis
        if ai:
            ai_doc = {
                "id": str(uuid.uuid4()),
                "listing_id": listing_id,
                **ai,
                "analyzed_at": now.isoformat(),
            }
            await db.ai_analyses.insert_one(ai_doc)

        # Seed photos
        for photo_url in seed["photos"]:
            photo_doc = {
                "id": str(uuid.uuid4()),
                "listing_id": listing_id,
                "url": photo_url,
                "local_path": "",
                "download_status": "pending",
                "downloaded_at": None,
            }
            await db.listing_photos.insert_one(photo_doc)

    # Seed user settings
    settings_doc = {
        "id": str(uuid.uuid4()),
        "user_id": "default",
        "alert_filters": {"max_price": 20000, "max_mileage": 150000, "min_deal_score": 40, "target_makes": [], "target_damage_types": [], "exclude_sources": [], "min_profit_threshold": 500},
        "telegram_chat_id": "", "telegram_bot_token": "",
        "twilio_sid": "", "twilio_token": "", "twilio_from": "", "twilio_to": "",
        "sendgrid_key": "", "sendgrid_to_email": "",
        "diy_mode": False, "shop_rate": 110.0, "available_capital": 50000.0,
        "notifications_telegram": True, "notifications_sms": False, "notifications_email": True,
    }
    await db.user_settings.insert_one(settings_doc)

    # Seed portfolio
    portfolio_items = [
        {"id": str(uuid.uuid4()), "user_id": "default", "listing_id": None, "vehicle_description": "2016 Honda Civic LX", "buy_date": "2025-09-15", "buy_price": 4200, "repair_items": [{"description": "Front bumper replacement", "cost": 850, "date": "2025-09-20"}, {"description": "Hood repaint", "cost": 600, "date": "2025-09-22"}, {"description": "Safety inspection", "cost": 100, "date": "2025-09-28"}], "sale_date": "2025-10-10", "sale_price": 9800, "notes": "Quick flip. Sold in 25 days."},
        {"id": str(uuid.uuid4()), "user_id": "default", "listing_id": None, "vehicle_description": "2018 Toyota RAV4 XLE AWD", "buy_date": "2025-07-01", "buy_price": 11500, "repair_items": [{"description": "Right rear quarter panel", "cost": 1800, "date": "2025-07-10"}, {"description": "Tail light assembly", "cost": 350, "date": "2025-07-12"}, {"description": "Paint match & blend", "cost": 900, "date": "2025-07-15"}, {"description": "Safety inspection", "cost": 100, "date": "2025-07-20"}], "sale_date": "2025-10-15", "sale_price": 21500, "notes": "Seasonal hold. Bought summer, sold fall for AWD premium."},
        {"id": str(uuid.uuid4()), "user_id": "default", "listing_id": None, "vehicle_description": "2019 Mazda3 GS", "buy_date": "2025-11-01", "buy_price": 6800, "repair_items": [{"description": "Front end repair", "cost": 2200, "date": "2025-11-10"}, {"description": "Radiator", "cost": 450, "date": "2025-11-12"}], "sale_date": None, "sale_price": None, "notes": "In repair. Estimated flip: $13,500"},
    ]
    for item in portfolio_items:
        await db.portfolio.insert_one(item)

    logger.info("Database seeded successfully")

@app.on_event("startup")
async def startup():
    await seed_database()

# ─── API Endpoints ───

@api_router.get("/")
async def root():
    return {"message": "AutoFlip Intelligence API", "version": "1.0.0"}

@api_router.get("/listings")
async def get_listings(
    source: Optional[str] = None,
    status: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_score: Optional[int] = None,
    damage_type: Optional[str] = None,
    make: Optional[str] = None,
    sort_by: str = "deal_score",
    sort_order: str = "desc",
):
    query = {"is_active": True}
    if source: query["source"] = source
    if status: query["status"] = status
    if min_price is not None or max_price is not None:
        query["price"] = {}
        if min_price is not None: query["price"]["$gte"] = min_price
        if max_price is not None: query["price"]["$lte"] = max_price
        if not query["price"]: del query["price"]
    if damage_type: query["damage_text"] = {"$regex": damage_type, "$options": "i"}
    if make: query["title"] = {"$regex": make, "$options": "i"}

    listings = await db.listings.find(query, {"_id": 0}).to_list(200)

    results = []
    for listing in listings:
        lid = listing["id"]
        profit = await db.profit_calculations.find_one({"listing_id": lid}, {"_id": 0})
        ai = await db.ai_analyses.find_one({"listing_id": lid}, {"_id": 0})
        combined = {**listing}
        if profit:
            combined["profit_calc"] = profit
            combined["deal_score"] = profit.get("deal_score", 0)
            combined["recommendation"] = profit.get("recommendation", "WATCH")
        else:
            combined["deal_score"] = 0
            combined["recommendation"] = "WATCH"
        if ai:
            combined["ai_analysis"] = ai
        results.append(combined)

    if min_score is not None:
        results = [r for r in results if r.get("deal_score", 0) >= min_score]

    reverse = sort_order == "desc"
    if sort_by == "deal_score":
        results.sort(key=lambda x: x.get("deal_score", 0), reverse=reverse)
    elif sort_by == "price":
        results.sort(key=lambda x: x.get("price", 0), reverse=reverse)
    elif sort_by == "first_seen_at":
        results.sort(key=lambda x: x.get("first_seen_at", ""), reverse=reverse)
    elif sort_by == "profit":
        results.sort(key=lambda x: (x.get("profit_calc") or {}).get("net_profit_best", 0), reverse=reverse)

    return results

@api_router.get("/listings/{listing_id}")
async def get_listing(listing_id: str):
    listing = await db.listings.find_one({"id": listing_id}, {"_id": 0})
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    profit = await db.profit_calculations.find_one({"listing_id": listing_id}, {"_id": 0})
    ai = await db.ai_analyses.find_one({"listing_id": listing_id}, {"_id": 0})
    photos = await db.listing_photos.find({"listing_id": listing_id}, {"_id": 0}).to_list(20)
    result = {**listing}
    if profit: result["profit_calc"] = profit
    if ai: result["ai_analysis"] = ai
    result["photos_detail"] = photos
    return result

@api_router.get("/listings/{listing_id}/photos")
async def get_listing_photos(listing_id: str):
    photos = await db.listing_photos.find({"listing_id": listing_id}, {"_id": 0}).to_list(20)
    return photos

@api_router.get("/listings/{listing_id}/analysis")
async def get_listing_analysis(listing_id: str):
    ai = await db.ai_analyses.find_one({"listing_id": listing_id}, {"_id": 0})
    if not ai:
        return {"status": "not_analyzed", "message": "AI analysis not yet available for this listing"}
    return ai

@api_router.post("/listings")
async def create_listing(data: ListingCreate):
    listing_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "id": listing_id,
        **data.model_dump(),
        "first_seen_at": now.isoformat(),
        "last_checked_at": now.isoformat(),
        "is_active": True,
        "price_history": [{"price": data.price, "timestamp": now.isoformat()}],
    }
    await db.listings.insert_one(doc)
    profit = calculate_profit(doc)
    score_data = calculate_deal_score(doc, profit)
    profit_doc = {"id": str(uuid.uuid4()), "listing_id": listing_id, **profit, **score_data, "calculated_at": now.isoformat()}
    await db.profit_calculations.insert_one(profit_doc)
    result = {k: v for k, v in doc.items() if k != "_id"}
    result["profit_calc"] = {k: v for k, v in profit_doc.items() if k != "_id"}
    await manager.broadcast({"type": "new_listing", "data": result})
    return result

# ─── Watchlist ───
@api_router.get("/watchlist")
async def get_watchlist():
    items = await db.watchlist.find({"user_id": "default"}, {"_id": 0}).to_list(100)
    results = []
    for item in items:
        listing = await db.listings.find_one({"id": item["listing_id"]}, {"_id": 0})
        profit = await db.profit_calculations.find_one({"listing_id": item["listing_id"]}, {"_id": 0})
        entry = {**item}
        if listing: entry["listing"] = listing
        if profit: entry["profit_calc"] = profit
        results.append(entry)
    return results

@api_router.post("/watchlist")
async def add_to_watchlist(data: WatchlistAdd):
    existing = await db.watchlist.find_one({"user_id": "default", "listing_id": data.listing_id})
    if existing:
        raise HTTPException(status_code=400, detail="Already in watchlist")
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": "default",
        "listing_id": data.listing_id,
        "notes": data.notes,
        "tags": data.tags,
        "added_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.watchlist.insert_one(doc)
    return {k: v for k, v in doc.items() if k != "_id"}

@api_router.put("/watchlist/{watchlist_id}")
async def update_watchlist(watchlist_id: str, data: WatchlistUpdate):
    update_data = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    if update_data:
        await db.watchlist.update_one({"id": watchlist_id}, {"$set": update_data})
    item = await db.watchlist.find_one({"id": watchlist_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    return item

@api_router.delete("/watchlist/{watchlist_id}")
async def remove_from_watchlist(watchlist_id: str):
    result = await db.watchlist.delete_one({"id": watchlist_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    return {"status": "removed"}

# ─── Portfolio ───
@api_router.get("/portfolio")
async def get_portfolio():
    items = await db.portfolio.find({"user_id": "default"}, {"_id": 0}).to_list(100)
    return items

@api_router.post("/portfolio")
async def create_portfolio_entry(data: PortfolioCreate):
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": "default",
        **data.model_dump(),
    }
    await db.portfolio.insert_one(doc)
    return {k: v for k, v in doc.items() if k != "_id"}

@api_router.put("/portfolio/{portfolio_id}")
async def update_portfolio(portfolio_id: str, data: PortfolioUpdate):
    update_data = {}
    dump = data.model_dump(exclude_none=True)
    if "repair_items" in dump:
        update_data["repair_items"] = dump["repair_items"]
    if "sale_date" in dump:
        update_data["sale_date"] = dump["sale_date"]
    if "sale_price" in dump:
        update_data["sale_price"] = dump["sale_price"]
    if "notes" in dump:
        update_data["notes"] = dump["notes"]
    if update_data:
        await db.portfolio.update_one({"id": portfolio_id}, {"$set": update_data})
    item = await db.portfolio.find_one({"id": portfolio_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Portfolio entry not found")
    return item

@api_router.delete("/portfolio/{portfolio_id}")
async def delete_portfolio(portfolio_id: str):
    result = await db.portfolio.delete_one({"id": portfolio_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Portfolio entry not found")
    return {"status": "deleted"}

# ─── Stats ───
@api_router.get("/stats")
async def get_stats():
    total_listings = await db.listings.count_documents({"is_active": True})
    buy_now_count = 0
    watch_count = 0
    skip_count = 0
    total_profit_potential = 0

    profits = await db.profit_calculations.find({}, {"_id": 0}).to_list(500)
    listing_ids = [p["listing_id"] for p in profits]
    active_listings = await db.listings.find({"is_active": True}, {"_id": 0, "id": 1}).to_list(500)
    active_ids = {l["id"] for l in active_listings}

    for p in profits:
        if p["listing_id"] not in active_ids:
            continue
        rec = p.get("recommendation", "")
        if rec == "BUY NOW": buy_now_count += 1
        elif rec == "WATCH": watch_count += 1
        else: skip_count += 1
        npb = p.get("net_profit_best", 0)
        if npb > 0: total_profit_potential += npb

    source_counts = {}
    for src in ["cathcart_rebuilders", "cathcart_used", "picnsave"]:
        source_counts[src] = await db.listings.count_documents({"is_active": True, "source": src})

    portfolio_items = await db.portfolio.find({"user_id": "default"}, {"_id": 0}).to_list(100)
    total_invested = sum(p.get("buy_price", 0) for p in portfolio_items)
    total_repair = sum(sum(r.get("cost", 0) for r in p.get("repair_items", [])) for p in portfolio_items)
    total_sold = sum(p.get("sale_price", 0) for p in portfolio_items if p.get("sale_price"))
    total_portfolio_profit = total_sold - total_invested - total_repair
    completed = [p for p in portfolio_items if p.get("sale_price")]
    avg_roi = 0
    if completed:
        rois = []
        for p in completed:
            cost = p["buy_price"] + sum(r.get("cost", 0) for r in p.get("repair_items", []))
            if cost > 0:
                rois.append(((p["sale_price"] - cost) / cost) * 100)
        avg_roi = sum(rois) / len(rois) if rois else 0

    watchlist_count = await db.watchlist.count_documents({"user_id": "default"})

    return {
        "total_listings": total_listings,
        "buy_now_count": buy_now_count,
        "watch_count": watch_count,
        "skip_count": skip_count,
        "total_profit_potential": round(total_profit_potential, 2),
        "source_counts": source_counts,
        "portfolio": {
            "total_invested": total_invested,
            "total_repair_cost": total_repair,
            "total_sold": total_sold,
            "total_profit": round(total_portfolio_profit, 2),
            "avg_roi": round(avg_roi, 1),
            "active_deals": len(portfolio_items) - len(completed),
            "completed_deals": len(completed),
        },
        "watchlist_count": watchlist_count,
    }

# ─── Market Data ───
@api_router.get("/market/{make}/{model}")
async def get_market_data(make: str, model: str):
    cache = await db.market_comparables.find_one(
        {"make": make.upper(), "model": model.upper()},
        {"_id": 0}
    )
    if cache:
        scraped = cache.get("scraped_at", "")
        if scraped:
            scraped_dt = datetime.fromisoformat(scraped)
            if datetime.now(timezone.utc) - scraped_dt < timedelta(hours=4):
                return cache

    # Mock market data
    import random
    base_price = random.randint(8000, 25000)
    comparables = []
    for i in range(random.randint(5, 25)):
        comparables.append({
            "source": random.choice(["autotrader", "kijiji", "cargurus"]),
            "price": base_price + random.randint(-3000, 5000),
            "mileage": random.randint(30000, 150000),
            "year": random.randint(2017, 2024),
            "days_listed": random.randint(1, 60),
        })
    avg_price = sum(c["price"] for c in comparables) / len(comparables)
    market_doc = {
        "id": str(uuid.uuid4()),
        "make": make.upper(),
        "model": model.upper(),
        "avg_price": round(avg_price, 2),
        "median_price": sorted(comparables, key=lambda x: x["price"])[len(comparables)//2]["price"],
        "comparables": comparables,
        "comparable_count": len(comparables),
        "price_trend": random.choice(["rising", "stable", "falling"]),
        "demand_level": random.choice(["high", "medium", "low"]),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.market_comparables.update_one(
        {"make": make.upper(), "model": model.upper()},
        {"$set": market_doc},
        upsert=True
    )
    return market_doc

# ─── Settings ───
@api_router.get("/settings")
async def get_settings():
    settings = await db.user_settings.find_one({"user_id": "default"}, {"_id": 0})
    if not settings:
        return {"user_id": "default", "alert_filters": {}, "diy_mode": False, "shop_rate": 110.0, "available_capital": 50000.0}
    return settings

@api_router.put("/settings")
async def update_settings(data: SettingsUpdate):
    update_data = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    if update_data:
        await db.user_settings.update_one(
            {"user_id": "default"},
            {"$set": update_data},
            upsert=True
        )
    settings = await db.user_settings.find_one({"user_id": "default"}, {"_id": 0})
    return settings

@api_router.post("/settings/test-notify")
async def test_notification():
    results = {"telegram": "not_configured", "sms": "not_configured", "email": "not_configured"}
    settings = await db.user_settings.find_one({"user_id": "default"}, {"_id": 0})
    if not settings:
        return results

    if settings.get("telegram_bot_token") and settings.get("telegram_chat_id"):
        try:
            from telegram import Bot
            bot = Bot(token=settings["telegram_bot_token"])
            await bot.send_message(chat_id=settings["telegram_chat_id"], text="AutoFlip Intelligence - Test notification working!")
            results["telegram"] = "sent"
        except Exception as e:
            results["telegram"] = f"error: {str(e)}"

    if settings.get("twilio_sid") and settings.get("twilio_token"):
        try:
            from twilio.rest import Client as TwilioClient
            twilio_client = TwilioClient(settings["twilio_sid"], settings["twilio_token"])
            twilio_client.messages.create(body="AutoFlip Intelligence - Test", from_=settings["twilio_from"], to=settings["twilio_to"])
            results["sms"] = "sent"
        except Exception as e:
            results["sms"] = f"error: {str(e)}"

    if settings.get("sendgrid_key") and settings.get("sendgrid_to_email"):
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            sg = SendGridAPIClient(settings["sendgrid_key"])
            message = Mail(from_email="alerts@autoflip.io", to_emails=settings["sendgrid_to_email"], subject="AutoFlip Intelligence - Test", plain_text_content="Test notification working!")
            sg.send(message)
            results["email"] = "sent"
        except Exception as e:
            results["email"] = f"error: {str(e)}"

    return results

# ─── AI Analysis Endpoint ───
@api_router.post("/listings/{listing_id}/analyze")
async def analyze_listing_photos(listing_id: str):
    listing = await db.listings.find_one({"id": listing_id}, {"_id": 0})
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    photos = listing.get("photos", [])
    if not photos:
        return {"status": "no_photos", "message": "No photos available for analysis"}

    api_key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not api_key:
        return {"status": "no_api_key", "message": "AI analysis API key not configured"}

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        import httpx
        import base64

        chat = LlmChat(
            api_key=api_key,
            session_id=f"analysis-{listing_id}",
            system_message="You are an expert Ontario automotive damage assessor helping a car investor evaluate rebuild potential. Analyze ALL provided photos of this vehicle. Return ONLY a valid JSON object with these exact fields: damage_severity (minor|moderate|severe|structural), damage_zones (list), hidden_damage_flags (list), airbag_status (deployed|intact|unknown), interior_condition (excellent|good|fair|poor), rust_detected (bool), rust_locations (list), frame_damage_suspected (bool), missing_parts (list), photo_count_analyzed (number), confidence_level (high|medium|low), ai_repair_cost_adjustment (number), summary (string), red_flags (list)"
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")

        image_contents = []
        async with httpx.AsyncClient(timeout=30) as http_client:
            for photo_url in photos[:5]:
                try:
                    resp = await http_client.get(photo_url)
                    if resp.status_code == 200:
                        b64 = base64.b64encode(resp.content).decode()
                        image_contents.append(ImageContent(image_base64=b64))
                except Exception:
                    pass

        if not image_contents:
            return {"status": "download_failed", "message": "Could not download any photos"}

        user_msg = UserMessage(
            text=f"Analyze these photos of: {listing['title']}. Listed damage: {listing.get('damage_text', 'Not specified')}. Brand: {listing.get('brand_text', 'Unknown')}. Return JSON only.",
            file_contents=image_contents
        )
        response = await chat.send_message(user_msg)

        try:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            analysis = json.loads(cleaned)
        except json.JSONDecodeError:
            analysis = {
                "damage_severity": "moderate",
                "damage_zones": [listing.get("damage_text", "unknown")],
                "hidden_damage_flags": [],
                "airbag_status": "unknown",
                "interior_condition": "good",
                "rust_detected": False,
                "rust_locations": [],
                "frame_damage_suspected": False,
                "missing_parts": [],
                "photo_count_analyzed": len(image_contents),
                "confidence_level": "low",
                "ai_repair_cost_adjustment": 0,
                "summary": response[:200],
                "red_flags": [],
            }

        ai_doc = {
            "id": str(uuid.uuid4()),
            "listing_id": listing_id,
            **analysis,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.ai_analyses.update_one(
            {"listing_id": listing_id},
            {"$set": ai_doc},
            upsert=True
        )

        # Recalculate profit with AI data
        profit = calculate_profit(listing, ai_analysis=analysis)
        score_data = calculate_deal_score(listing, profit, analysis)
        await db.profit_calculations.update_one(
            {"listing_id": listing_id},
            {"$set": {**profit, **score_data, "calculated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True
        )

        return {**ai_doc, "_id": None}

    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        return {"status": "error", "message": str(e)}

# ─── Recalculate endpoint ───
@api_router.post("/listings/{listing_id}/recalculate")
async def recalculate_listing(listing_id: str):
    listing = await db.listings.find_one({"id": listing_id}, {"_id": 0})
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    settings = await db.user_settings.find_one({"user_id": "default"}, {"_id": 0})
    diy_mode = settings.get("diy_mode", False) if settings else False
    ai = await db.ai_analyses.find_one({"listing_id": listing_id}, {"_id": 0})
    profit = calculate_profit(listing, ai_analysis=ai, diy_mode=diy_mode)
    score_data = calculate_deal_score(listing, profit, ai)
    now = datetime.now(timezone.utc).isoformat()
    profit_doc = {"id": str(uuid.uuid4()), "listing_id": listing_id, **profit, **score_data, "calculated_at": now}
    await db.profit_calculations.update_one({"listing_id": listing_id}, {"$set": profit_doc}, upsert=True)
    return profit_doc

# ─── Market Intelligence ───
@api_router.get("/market-intelligence")
async def get_market_intelligence():
    listings = await db.listings.find({"is_active": True}, {"_id": 0}).to_list(500)
    make_model_counts = {}
    make_counts = {}
    for l in listings:
        title_parts = l.get("title", "").split()
        if len(title_parts) >= 3:
            make = title_parts[1]
            model = title_parts[2]
            key = f"{make} {model}"
            make_model_counts[key] = make_model_counts.get(key, 0) + 1
            make_counts[make] = make_counts.get(make, 0) + 1

    profits = await db.profit_calculations.find({}, {"_id": 0}).to_list(500)
    active_ids = {l["id"] for l in listings}
    avg_scores_by_make = {}
    for p in profits:
        if p["listing_id"] in active_ids:
            lid = p["listing_id"]
            listing = next((l for l in listings if l["id"] == lid), None)
            if listing:
                parts = listing.get("title", "").split()
                if len(parts) >= 2:
                    make = parts[1]
                    if make not in avg_scores_by_make:
                        avg_scores_by_make[make] = []
                    avg_scores_by_make[make].append(p.get("deal_score", 0))

    demand_heatmap = []
    for make, scores in avg_scores_by_make.items():
        demand_heatmap.append({
            "make": make,
            "count": make_counts.get(make, 0),
            "avg_score": round(sum(scores) / len(scores), 1),
            "demand": "high" if sum(scores) / len(scores) > 55 else "medium" if sum(scores) / len(scores) > 35 else "low",
        })

    oversupply = [{"make_model": k, "count": v} for k, v in make_model_counts.items() if v >= 3]

    seasonal_data = []
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for vtype, info in SEASONAL_PEAKS.items():
        monthly = []
        for i, m in enumerate(months):
            mult = 1.0
            if (i + 1) in info["peak_months"]:
                mult = info["multiplier"]
            elif any(abs((i + 1) - p) <= 1 for p in info["peak_months"]):
                mult = 1.0 + (info["multiplier"] - 1.0) * 0.5
            monthly.append({"month": m, "multiplier": round(mult, 3)})
        seasonal_data.append({"vehicle_type": vtype, "monthly": monthly, "peak": info["label"]})

    return {
        "demand_heatmap": sorted(demand_heatmap, key=lambda x: x["avg_score"], reverse=True),
        "oversupply_alerts": oversupply,
        "seasonal_trends": seasonal_data[:6],
        "total_active": len(listings),
    }

# ─── WebSocket ───
@app.websocket("/ws/listings")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

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
    client.close()
