from fastapi import APIRouter, HTTPException
from typing import Optional
from ..database import db

router = APIRouter()


@router.get("/listings")
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
    price_drop_only: Optional[bool] = None,
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
    if price_drop_only:
        query["has_price_drop"] = True

    listings = await db.listings.find(query, {"_id": 0}).to_list(500)

    if min_profit is not None:
        listings = [l for l in listings if (l.get("profit_best") or 0) >= min_profit]
    if min_score is not None:
        listings = [l for l in listings if (l.get("deal_score") or 0) >= min_score]

    reverse = sort_order == "desc"
    sort_key = {
        "deal_score": lambda x: x.get("deal_score") or 0,
        "profit": lambda x: x.get("profit_best") or -999999,
        "price": lambda x: x.get("price") or 999999,
        "mileage": lambda x: x.get("mileage") or 999999,
        "date": lambda x: x.get("first_seen") or "",
        "price_drop": lambda x: x.get("price_drop_amount") or 0,
    }.get(sort_by, lambda x: x.get("deal_score") or 0)

    listings.sort(key=sort_key, reverse=reverse)
    return listings


@router.get("/listings/{listing_id}")
async def get_listing(listing_id: str):
    listing = await db.listings.find_one({"id": listing_id}, {"_id": 0})
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.get("/listings/{listing_id}/price-history")
async def get_price_history(listing_id: str):
    """Return price history timeline for a specific listing."""
    listing = await db.listings.find_one({"id": listing_id}, {"_id": 0, "price_history": 1, "price": 1, "first_seen": 1, "title": 1})
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    history = listing.get("price_history", [])
    current_price = listing.get("price")
    first_seen = listing.get("first_seen")

    # Build a full timeline: original → changes → current
    timeline = []
    if history:
        # First entry represents original price
        timeline.append({
            "price": history[0]["price"],
            "date": first_seen,
            "label": "Listed",
            "is_current": False,
        })
        for i, entry in enumerate(history):
            drop = entry.get("drop_amount", 0)
            pct = entry.get("drop_pct", 0)
            label = f"↓ ${abs(drop):,.0f} ({abs(pct):.1f}%)" if drop > 0 else f"↑ ${abs(drop):,.0f} ({abs(pct):.1f}%)"
            timeline.append({
                "price": entry["price"],
                "date": entry["date"],
                "label": label,
                "drop_amount": drop,
                "drop_pct": pct,
                "is_current": False,
            })
    else:
        timeline.append({
            "price": current_price,
            "date": first_seen,
            "label": "Listed",
            "is_current": True,
        })

    if current_price and (not history or history[-1]["price"] != current_price):
        if history:
            last_price = history[-1]["price"]
            drop = round(last_price - current_price, 0)
            pct = round((drop / last_price) * 100, 1) if last_price else 0
            label = f"↓ ${abs(drop):,.0f} ({abs(pct):.1f}%)" if drop > 0 else ("Current" if drop == 0 else f"↑ ${abs(drop):,.0f}")
        else:
            label = "Current"
            drop = 0
            pct = 0
        timeline.append({
            "price": current_price,
            "date": listing.get("last_scraped", first_seen),
            "label": label,
            "drop_amount": drop if history else 0,
            "drop_pct": pct if history else 0,
            "is_current": True,
        })

    return {
        "listing_id": listing_id,
        "title": listing.get("title"),
        "timeline": timeline,
        "total_drop": round((timeline[0]["price"] - current_price), 0) if timeline and current_price and timeline[0]["price"] else 0,
        "total_drop_pct": round(((timeline[0]["price"] - current_price) / timeline[0]["price"]) * 100, 1) if timeline and current_price and timeline[0]["price"] else 0,
    }


@router.get("/stats")
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

    # Price drop count
    price_drop_count = sum(1 for l in listings if l.get("has_price_drop"))

    source_counts = {
        src: sum(1 for l in listings if l.get("source") == src)
        for src in ["cathcart_rebuilders", "cathcart_used", "picnsave"]
    }

    best_deal = None
    scored = [l for l in listings if l.get("deal_score")]
    if scored:
        bd = max(scored, key=lambda x: x["deal_score"])
        best_deal = {"title": bd["title"], "score": bd["deal_score"], "profit_best": bd.get("profit_best")}

    scrape_status = await db.scrape_status.find_one({"id": "global"}, {"_id": 0})

    return {
        "total_listings": total,
        "buy_count": buy_count,
        "watch_count": watch_count,
        "skip_count": skip_count,
        "no_score_count": no_score,
        "avg_profit_best": round(avg_profit, 0),
        "top_profit": round(top_profit, 0),
        "price_drop_count": price_drop_count,
        "source_counts": source_counts,
        "best_deal": best_deal,
        "last_scrape": scrape_status,
    }
