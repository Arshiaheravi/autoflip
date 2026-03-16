import asyncio
import logging
import os
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

from .database import db, client as mongo_client
from .scrapers.runner import scheduled_scrape, run_full_scrape
from .services.autotrader import load_at_cache_from_db
from .routes.listings import router as listings_router
from .routes.scrape import router as scrape_router
from .routes.settings import router as settings_router
from .routes.auth import router as auth_router
from .routes.stripe_routes import router as stripe_router

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = FastAPI(title="AutoFlip Intelligence API", version="2.1.0")

api_router = APIRouter(prefix="/api")
api_router.include_router(listings_router)
api_router.include_router(scrape_router)
api_router.include_router(settings_router)
api_router.include_router(auth_router)
api_router.include_router(stripe_router)


@api_router.get("/")
async def root():
    return {"message": "AutoFlip Intelligence API", "version": "2.1.0"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

_scrape_task_handle = None


@app.on_event("startup")
async def startup():
    global _scrape_task_handle
    await load_at_cache_from_db()
    existing_settings = await db.user_settings.find_one({"id": "global"})
    if not existing_settings:
        await db.user_settings.insert_one({"id": "global", "scan_interval": 600})
    count = await db.listings.count_documents({})
    if count == 0:
        logging.getLogger(__name__).info("No listings in DB, triggering initial scrape...")
        asyncio.create_task(run_full_scrape())
    _scrape_task_handle = asyncio.create_task(scheduled_scrape())

    # Ensure indexes on users collection
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)


@app.on_event("shutdown")
async def shutdown():
    global _scrape_task_handle
    if _scrape_task_handle:
        _scrape_task_handle.cancel()
    mongo_client.close()
