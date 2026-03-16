import uuid
import logging
import asyncio
from datetime import datetime, timezone

from ..database import db
from ..scrapers.cathcart import scrape_cathcart
from ..scrapers.picnsave import scrape_picnsave
from ..services.ai_damage import detect_damage_from_photo
from ..services.autotrader import estimate_market_value_blended
from ..services.calculations import get_repair_range, calculate_ontario_fees, calc_deal_score
from ..services.email_alerts import send_deal_alert, ALERT_MIN_SCORE

logger = logging.getLogger(__name__)

scrape_lock = asyncio.Lock()
current_interval = 600


async def get_scan_interval():
    settings = await db.user_settings.find_one({"id": "global"}, {"_id": 0})
    if settings:
        return settings.get("scan_interval", 600)
    return 600


async def dispatch_buy_deal_alerts(new_buy_listings: list[dict]) -> int:
    """
    Send BUY deal alert emails to all subscribed Pro users.

    Returns the number of emails dispatched (not necessarily delivered).
    Runs in background — never raises exceptions.
    """
    if not new_buy_listings:
        return 0

    try:
        # Find all active Pro subscribers with email alerts enabled
        subscribers = await db.users.find(
            {
                "plan": "pro",
                "subscription_status": "active",
                "email_alerts": {"$ne": False},  # default ON for pro users
            },
            {"_id": 0, "email": 1, "name": 1},
        ).to_list(1000)

        if not subscribers:
            logger.info("No Pro subscribers to notify — skipping email alerts")
            return 0

        sent_count = 0
        for listing in new_buy_listings:
            for subscriber in subscribers:
                try:
                    ok = await send_deal_alert(subscriber["email"], listing)
                    if ok:
                        sent_count += 1
                except Exception as e:
                    logger.warning(
                        "Alert dispatch error for %s / listing %s: %s",
                        subscriber.get("email"), listing.get("title"), e
                    )

        if sent_count:
            logger.info(
                "Dispatched %d deal alert emails (%d deals × %d subscribers)",
                sent_count, len(new_buy_listings), len(subscribers),
            )
        return sent_count
    except Exception as e:
        logger.error("dispatch_buy_deal_alerts error: %s", e)
        return 0


async def run_full_scrape():
    """Run scraper for all sources and store results."""
    logger.info("=== Starting full scrape ===")
    now = datetime.now(timezone.utc).isoformat()

    await db.scrape_status.update_one(
        {"id": "global"},
        {"$set": {"status": "running", "started_at": now}},
        upsert=True
    )

    all_listings = []
    try:
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

    new_count = 0
    updated_count = 0
    ai_detected_count = 0
    price_drop_count = 0
    new_buy_listings: list[dict] = []  # track new BUY deals for email alerts

    for raw in all_listings:
        url = raw.get("url", "")
        if not url:
            continue

        year = raw.get("year")
        mileage = raw.get("mileage")
        price = raw.get("price")
        damage = raw.get("damage", "")
        brand = raw.get("brand", "")
        colour = raw.get("colour", "")
        is_salvage = brand and "SALVAGE" in brand.upper()

        ai_damage_result = None
        severity = ""
        if (not damage or damage.strip() == "") and (raw.get("photos") or raw.get("photo")):
            try:
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

        market_value = None
        mv_breakdown = None
        if year and raw.get("title"):
            mv_result = await estimate_market_value_blended(
                raw["title"], year, mileage,
                colour=colour, brand_status=brand
            )
            market_value = mv_result["market_value"]
            mv_breakdown = mv_result

        repair_low, repair_high, repair_breakdown = get_repair_range(
            damage, severity=severity, is_salvage=is_salvage
        )

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
            "calc_version": "v2.1",
            "mv_breakdown": mv_breakdown,
            "repair_breakdown": repair_breakdown,
            "fees_breakdown": fees_breakdown,
            "ai_damage_detected": ai_hit,
            "ai_damage_details": ai_damage_result.get("details", "") if ai_hit else "",
        }

        existing = await db.listings.find_one({"url": url}, {"_id": 0})
        if existing:
            listing_doc["first_seen"] = existing.get("first_seen", now)
            listing_doc["id"] = existing.get("id", str(uuid.uuid4()))
            old_price = existing.get("price")

            # ── Price-change tracking ──────────────────────────────────────
            price_history = existing.get("price_history", [])
            if old_price and price and old_price != price:
                drop_amount = round(old_price - price, 0)   # positive = price dropped
                drop_pct = round((drop_amount / old_price) * 100, 1)
                price_history.append({
                    "price": old_price,
                    "date": existing.get("last_scraped", now),
                    "drop_amount": drop_amount,
                    "drop_pct": drop_pct,
                })
                if drop_amount > 0:
                    price_drop_count += 1
                    logger.info(f"  Price drop: {raw.get('title','')} ${old_price}→${price} (↓${drop_amount})")
            listing_doc["price_history"] = price_history

            # ── Compute cumulative price-drop fields ──────────────────────
            original_price = price_history[0]["price"] if price_history else price
            if original_price and price and original_price > price:
                listing_doc["price_drop_amount"] = round(original_price - price, 0)
                listing_doc["price_drop_pct"] = round(((original_price - price) / original_price) * 100, 1)
                listing_doc["has_price_drop"] = True
            else:
                listing_doc["price_drop_amount"] = 0
                listing_doc["price_drop_pct"] = 0.0
                listing_doc["has_price_drop"] = existing.get("has_price_drop", False)

            await db.listings.update_one({"url": url}, {"$set": listing_doc})
            updated_count += 1
        else:
            listing_doc["id"] = str(uuid.uuid4())
            listing_doc["first_seen"] = now
            listing_doc["price_history"] = []
            listing_doc["price_drop_amount"] = 0
            listing_doc["price_drop_pct"] = 0.0
            listing_doc["has_price_drop"] = False
            await db.listings.insert_one(listing_doc)
            new_count += 1

            # ── Track new BUY deals for email alerts ─────────────────────
            if score and score >= ALERT_MIN_SCORE and score_label == "BUY":
                new_buy_listings.append(listing_doc)
                logger.info(
                    "  New BUY deal queued for alert: %s (score %d)",
                    listing_doc["title"], score
                )

    source_urls = {}
    for l in all_listings:
        src = l.get("source", "")
        u = l.get("url", "")
        if src and u:
            source_urls.setdefault(src, set()).add(u)

    for src, urls in source_urls.items():
        if urls:
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
            "price_drop_count": price_drop_count,
            "sources": {
                "cathcart_rebuilders": len([l for l in all_listings if l["source"] == "cathcart_rebuilders"]),
                "cathcart_used": len([l for l in all_listings if l["source"] == "cathcart_used"]),
                "picnsave": len([l for l in all_listings if l["source"] == "picnsave"]),
            }
        }},
        upsert=True
    )
    logger.info(
        "=== Scrape complete: %d new, %d updated, %d AI damage, %d price drops, %d total ===",
        new_count, updated_count, ai_detected_count, price_drop_count, len(all_listings)
    )

    # ── Dispatch email alerts for new BUY deals (fire-and-forget) ──────────
    if new_buy_listings:
        asyncio.create_task(dispatch_buy_deal_alerts(new_buy_listings))

    return {
        "new": new_count,
        "updated": updated_count,
        "total": len(all_listings),
        "ai_detections": ai_detected_count,
        "price_drops": price_drop_count,
        "buy_alerts_queued": len(new_buy_listings),
    }


async def scheduled_scrape():
    """Run scrape on user-configured interval."""
    global current_interval
    while True:
        current_interval = await get_scan_interval()
        async with scrape_lock:
            try:
                await run_full_scrape()
            except Exception as e:
                logger.error(f"Scheduled scrape error: {e}")
        await db.scan_history.insert_one({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "interval": current_interval,
            "status": "completed",
        })
        count = await db.scan_history.count_documents({})
        if count > 50:
            oldest = await db.scan_history.find().sort("timestamp", 1).limit(count - 50).to_list(count - 50)
            if oldest:
                ids = [o["id"] for o in oldest]
                await db.scan_history.delete_many({"id": {"$in": ids}})
        await asyncio.sleep(current_interval)
