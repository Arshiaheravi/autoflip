import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter
from ..database import db
from ..scrapers.runner import scrape_lock, run_full_scrape
from ..services import autotrader as at_mod
from ..services.autotrader import (
    fetch_autotrader_comps, extract_make_model,
    estimate_market_value_blended,
)
from ..services.calculations import calculate_ontario_fees, calc_deal_score

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/scrape")
async def trigger_scrape():
    """Manually trigger a scrape."""
    if scrape_lock.locked():
        return {"status": "already_running"}
    asyncio.create_task(run_full_scrape())
    return {"status": "started"}


@router.post("/fetch-comps")
async def fetch_comps_for_all():
    """Slowly fetch AutoTrader comps for all unique vehicles. Runs in background."""
    at_mod._autotrader_request_count = 0
    at_mod._autotrader_last_reset = datetime.now()

    listings = await db.listings.find(
        {}, {"_id": 0, "title": 1, "year": 1, "url": 1, "mileage": 1, "brand": 1, "colour": 1, "mv_breakdown": 1}
    ).to_list(500)

    seen = set()
    unique = []
    for l in listings:
        title = l.get("title", "")
        year = l.get("year")
        if not title or not year:
            continue
        make_slug, model_slug = extract_make_model(title.lower())
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
                make_slug, model_slug = extract_make_model(l["title"].lower())
                for listing in listings:
                    lt = listing.get("title", "").lower()
                    ly = listing.get("year")
                    ms, mds = extract_make_model(lt)
                    if ms == make_slug and mds == model_slug and ly == l["year"]:
                        brand = listing.get("brand", "")
                        colour = listing.get("colour", "")
                        mv_result = await estimate_market_value_blended(
                            listing["title"], listing["year"], listing.get("mileage"),
                            colour=colour, brand_status=brand
                        )
                        market_value = mv_result["market_value"]
                        existing = await db.listings.find_one(
                            {"url": listing["url"]}, {"_id": 0, "price": 1, "repair_low": 1, "repair_high": 1}
                        )
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


@router.get("/scrape-status")
async def get_scrape_status():
    status = await db.scrape_status.find_one({"id": "global"}, {"_id": 0})
    settings = await db.user_settings.find_one({"id": "global"}, {"_id": 0})
    interval = settings.get("scan_interval", 600) if settings else 600
    result = status or {"status": "never_run"}
    result["scan_interval"] = interval
    result["is_scanning"] = scrape_lock.locked()
    return result


@router.get("/scan-history")
async def get_scan_history():
    history = await db.scan_history.find({}, {"_id": 0}).sort("timestamp", -1).to_list(20)
    return history


@router.post("/recalculate")
async def recalculate_all():
    """Recalculate market value, repair cost, and profit for ALL listings using v2 engine."""
    from ..services.ai_damage import detect_damage_from_photo
    from ..services.calculations import get_repair_range

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

        ai_hit = bool(ai_damage_result and ai_damage_result.get("confidence", 0) >= 0.4 and ai_damage_result.get("damage", "") not in ["", "NONE"])

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
            "ai_damage_detected": ai_hit,
            "ai_damage_details": ai_damage_result.get("details", "") if ai_hit else "",
        }
        await db.listings.update_one({"url": l["url"]}, {"$set": update_doc})
        updated += 1

    return {"updated": updated, "ai_damage_detections": ai_count}


@router.get("/calc-methodology")
async def get_calc_methodology():
    return {
        "version": "2.1",
        "engine": "AutoFlip Enhanced Calculation Engine v2.1 (Blended)",
        "market_value": {
            "description": "Blended market value: AutoTrader.ca real comparables + multi-factor formula",
            "blending": {
                "description": "When AutoTrader comps available: 60% AutoTrader median + 40% formula. With few comps (1-2): 40% AT + 60% formula. No comps: 100% formula.",
                "autotrader": "Scrapes AutoTrader.ca Ontario listings for same make/model/year (±1 year).",
                "formula": "MSRP × Depreciation × Brand × BodyType × Trim × Color × Mileage × TitleStatus",
                "cache": "AutoTrader results cached for 24 hours.",
            },
            "formula": "Market Value = MSRP × Depreciation × Brand × BodyType × Trim × Color × Mileage × TitleStatus",
        },
        "repair_cost": {
            "description": "Damage-specific repair cost estimation using Ontario body shop rates ($110-130/hr)",
            "formula": "Total Repair = (Base Repair × Severity) + Safety ($100) + Salvage Process ($625 if salvage)",
        },
        "ontario_fees": {
            "formula": "Fees = (Price × 0.13) + $22 + $32 + $100",
        },
        "profit_calculation": {
            "formula": "Profit = Market Value - Purchase Price - Repair Cost - Ontario Fees",
        },
        "deal_scoring": {
            "scale": [
                {"range": "8-10", "label": "BUY"},
                {"range": "5-7", "label": "WATCH"},
                {"range": "1-4", "label": "SKIP"},
            ],
        },
    }
