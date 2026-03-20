"""
Shared pytest fixtures for all backend tests.
Provides mock DB, authenticated test client, and common test users.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.services.auth import hash_password, create_access_token


# ─── Reusable mock user ──────────────────────────────────────────────────────

FREE_USER = {
    "id": "test-user-id-001",
    "email": "test@autoflip.ca",
    "name": "Test User",
    "password_hash": hash_password("password123"),
    "plan": "free",
    "subscription_status": "inactive",
    "billing_period": "monthly",
    "alerted_listings": [],
}

PRO_USER = {
    "id": "pro-user-id-002",
    "email": "pro@autoflip.ca",
    "name": "Pro User",
    "password_hash": hash_password("propass123"),
    "plan": "pro",
    "subscription_status": "active",
    "billing_period": "monthly",
    "alerted_listings": [],
}


def make_token(user: dict) -> str:
    return create_access_token(user["id"], user["email"])


# ─── Mock database fixture ───────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """
    Returns a MagicMock that mirrors the Motor db interface.
    Each collection has AsyncMock for all common Motor operations.
    """
    db = MagicMock()

    def make_collection():
        col = MagicMock()
        col.find_one = AsyncMock(return_value=None)
        col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake-id"))
        col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
        col.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
        col.count_documents = AsyncMock(return_value=0)
        col.create_index = AsyncMock(return_value="index-name")
        cursor = MagicMock()
        cursor.sort = MagicMock(return_value=cursor)
        cursor.skip = MagicMock(return_value=cursor)
        cursor.limit = MagicMock(return_value=cursor)
        cursor.__aiter__ = MagicMock(return_value=iter([]))
        col.find = MagicMock(return_value=cursor)
        return col

    db.users = make_collection()
    db.listings = make_collection()
    db.scan_history = make_collection()
    db.user_settings = make_collection()
    db.autotrader_cache = make_collection()
    db.price_history = make_collection()
    return db


# ─── Patched app test client ─────────────────────────────────────────────────

@pytest.fixture
def client(mock_db):
    """
    TestClient with MongoDB patched out.
    Startup events (which need real MongoDB) are disabled via lifespan override.
    """
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    with patch('app.database.db', mock_db), \
         patch('app.routes.auth.db', mock_db), \
         patch('app.routes.listings.db', mock_db), \
         patch('app.routes.settings.db', mock_db), \
         patch('app.routes.scrape.db', mock_db), \
         patch('app.main.db', mock_db):

        from app.main import app
        # Disable startup/shutdown so no real MongoDB calls happen
        app.router.on_startup.clear()
        app.router.on_shutdown.clear()

        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


@pytest.fixture
def auth_headers(mock_db):
    """Headers for an authenticated FREE user."""
    mock_db.users.find_one = AsyncMock(return_value=FREE_USER)
    token = make_token(FREE_USER)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def pro_auth_headers(mock_db):
    """Headers for an authenticated PRO user."""
    mock_db.users.find_one = AsyncMock(return_value=PRO_USER)
    token = make_token(PRO_USER)
    return {"Authorization": f"Bearer {token}"}
