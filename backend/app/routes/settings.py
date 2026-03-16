from fastapi import APIRouter
from ..database import db

router = APIRouter()


@router.get("/settings")
async def get_settings():
    settings = await db.user_settings.find_one({"id": "global"}, {"_id": 0})
    return settings or {"id": "global", "scan_interval": 600}


@router.put("/settings")
async def update_settings(data: dict):
    allowed = {"scan_interval"}
    update = {k: v for k, v in data.items() if k in allowed}
    if "scan_interval" in update:
        val = int(update["scan_interval"])
        update["scan_interval"] = max(60, min(3600, val))
    if update:
        await db.user_settings.update_one({"id": "global"}, {"$set": update}, upsert=True)
    return await db.user_settings.find_one({"id": "global"}, {"_id": 0})
