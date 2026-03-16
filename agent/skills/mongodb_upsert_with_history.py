"""
Upsert a listing document and track price history atomically.
Use for: any scraper that re-scrapes existing listings and needs to detect price drops.

Saved by agent on 2026-03-16.
"""

from datetime import datetime


async def upsert_listing_with_history(db, listing: dict) -> dict:
    """
    Upsert a listing, tracking price changes in a price_history array.
    Returns {"inserted": bool, "price_changed": bool, "price_drop": float}.

    listing must have: url, price (float or None), and other fields.
    """
    url = listing["url"]
    now = datetime.utcnow()
    new_price = listing.get("price")

    existing = await db.listings.find_one({"url": url}, {"price": 1, "price_history": 1})

    update_doc = {"$set": {**listing, "updated_at": now}, "$setOnInsert": {"created_at": now}}
    price_changed = False
    price_drop = 0.0

    if existing and new_price and existing.get("price") != new_price:
        old_price = existing.get("price", 0) or 0
        price_drop = old_price - new_price  # positive = dropped
        price_changed = True
        update_doc["$push"] = {
            "price_history": {"price": old_price, "recorded_at": now}
        }
        update_doc["$set"]["has_price_drop"] = price_drop > 0
        update_doc["$set"]["price_drop_amount"] = price_drop
        update_doc["$set"]["price_drop_pct"] = round(price_drop / old_price * 100, 1) if old_price else 0

    result = await db.listings.update_one({"url": url}, update_doc, upsert=True)
    inserted = result.upserted_id is not None
    return {"inserted": inserted, "price_changed": price_changed, "price_drop": price_drop}
