"""
Integration tests for /api/auth/* routes using FastAPI TestClient.
MongoDB is fully mocked — no real database required.

Covers: register, login, /me, /subscribe, /logout
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.auth import hash_password, create_access_token


# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_user(email="user@test.com", plan="free", status="inactive"):
    return {
        "id": "test-uid-001",
        "email": email,
        "name": "Test User",
        "password_hash": hash_password("securepass"),
        "plan": plan,
        "subscription_status": status,
        "billing_period": "monthly",
        "alerted_listings": [],
    }


def bearer(user: dict) -> str:
    return f"Bearer {create_access_token(user['id'], user['email'])}"


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.users = MagicMock()
    db.users.find_one = AsyncMock(return_value=None)
    db.users.insert_one = AsyncMock(return_value=MagicMock(inserted_id="ok"))
    db.users.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    db.users.create_index = AsyncMock()
    db.listings = MagicMock()
    db.listings.count_documents = AsyncMock(return_value=1)
    db.user_settings = MagicMock()
    db.user_settings.find_one = AsyncMock(return_value={"id": "global", "scan_interval": 600})
    db.autotrader_cache = MagicMock()
    db.autotrader_cache.find = MagicMock(return_value=MagicMock(
        __aiter__=MagicMock(return_value=iter([]))
    ))
    return db


@pytest.fixture
def client(mock_db):
    with patch("app.database.db", mock_db), \
         patch("app.routes.auth.db", mock_db), \
         patch("app.routes.listings.db", mock_db), \
         patch("app.routes.settings.db", mock_db), \
         patch("app.routes.scrape.db", mock_db), \
         patch("app.main.db", mock_db), \
         patch("app.scrapers.runner.run_full_scrape", new_callable=AsyncMock), \
         patch("app.scrapers.runner.scheduled_scrape", new_callable=AsyncMock), \
         patch("app.services.autotrader.load_at_cache_from_db", new_callable=AsyncMock):
        from fastapi.testclient import TestClient
        from app.main import app
        app.router.on_startup.clear()
        app.router.on_shutdown.clear()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c, mock_db


# ─── POST /api/auth/register ─────────────────────────────────────────────────

class TestRegister:
    def test_register_new_user_returns_201(self, client):
        c, db = client
        db.users.find_one = AsyncMock(return_value=None)
        resp = c.post("/api/auth/register", json={
            "email": "new@autoflip.ca",
            "password": "securepass",
            "name": "New User",
        })
        assert resp.status_code == 201

    def test_register_returns_token(self, client):
        c, db = client
        db.users.find_one = AsyncMock(return_value=None)
        resp = c.post("/api/auth/register", json={
            "email": "new@autoflip.ca",
            "password": "securepass",
            "name": "New User",
        })
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data

    def test_register_user_field_includes_email(self, client):
        c, db = client
        db.users.find_one = AsyncMock(return_value=None)
        resp = c.post("/api/auth/register", json={
            "email": "NEW@AUTOFLIP.CA",
            "password": "securepass",
            "name": "Test",
        })
        assert resp.status_code == 201
        assert resp.json()["user"]["email"] == "new@autoflip.ca"  # lowercased

    def test_register_duplicate_email_returns_409(self, client):
        c, db = client
        existing = make_user(email="taken@autoflip.ca")
        db.users.find_one = AsyncMock(return_value=existing)
        resp = c.post("/api/auth/register", json={
            "email": "taken@autoflip.ca",
            "password": "securepass",
            "name": "User",
        })
        assert resp.status_code == 409

    def test_register_short_password_returns_422(self, client):
        c, db = client
        db.users.find_one = AsyncMock(return_value=None)
        resp = c.post("/api/auth/register", json={
            "email": "user@test.com",
            "password": "abc",  # too short
            "name": "User",
        })
        assert resp.status_code == 422

    def test_register_missing_email_returns_422(self, client):
        c, db = client
        resp = c.post("/api/auth/register", json={
            "password": "securepass",
            "name": "User",
        })
        assert resp.status_code == 422


# ─── POST /api/auth/login ────────────────────────────────────────────────────

class TestLogin:
    def test_login_valid_credentials(self, client):
        c, db = client
        user = make_user()
        db.users.find_one = AsyncMock(return_value=user)
        resp = c.post("/api/auth/login", json={
            "email": "user@test.com",
            "password": "securepass",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password_returns_401(self, client):
        c, db = client
        user = make_user()
        db.users.find_one = AsyncMock(return_value=user)
        resp = c.post("/api/auth/login", json={
            "email": "user@test.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_unknown_email_returns_401(self, client):
        c, db = client
        db.users.find_one = AsyncMock(return_value=None)
        resp = c.post("/api/auth/login", json={
            "email": "ghost@test.com",
            "password": "securepass",
        })
        assert resp.status_code == 401

    def test_login_email_case_insensitive(self, client):
        c, db = client
        user = make_user()
        db.users.find_one = AsyncMock(return_value=user)
        resp = c.post("/api/auth/login", json={
            "email": "USER@TEST.COM",
            "password": "securepass",
        })
        assert resp.status_code == 200


# ─── GET /api/auth/me ─────────────────────────────────────────────────────────

class TestMe:
    def test_me_with_valid_token(self, client):
        c, db = client
        user = make_user()
        db.users.find_one = AsyncMock(return_value=user)
        token = bearer(user)
        resp = c.get("/api/auth/me", headers={"Authorization": token})
        assert resp.status_code == 200
        assert resp.json()["email"] == "user@test.com"

    def test_me_without_token_returns_401(self, client):
        c, _ = client
        resp = c.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token_returns_401(self, client):
        c, _ = client
        resp = c.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401

    def test_me_does_not_return_password_hash(self, client):
        c, db = client
        user = make_user()
        db.users.find_one = AsyncMock(return_value=user)
        resp = c.get("/api/auth/me", headers={"Authorization": bearer(user)})
        assert "password_hash" in user  # confirm field exists on raw user
        assert "password_hash" not in resp.json()  # confirm it's stripped from response


# ─── POST /api/auth/subscribe ─────────────────────────────────────────────────

class TestSubscribe:
    def test_subscribe_pro_monthly(self, client):
        c, db = client
        user = make_user()
        updated_user = {**user, "plan": "pro", "subscription_status": "active"}
        db.users.find_one = AsyncMock(side_effect=[user, updated_user])
        resp = c.post("/api/auth/subscribe",
            headers={"Authorization": bearer(user)},
            json={"plan": "pro", "billing_period": "monthly", "subscription_status": "active"},
        )
        assert resp.status_code == 200

    def test_subscribe_invalid_plan_returns_422(self, client):
        c, db = client
        user = make_user()
        db.users.find_one = AsyncMock(return_value=user)
        resp = c.post("/api/auth/subscribe",
            headers={"Authorization": bearer(user)},
            json={"plan": "enterprise", "billing_period": "monthly", "subscription_status": "active"},
        )
        assert resp.status_code == 422

    def test_subscribe_invalid_billing_period_returns_422(self, client):
        c, db = client
        user = make_user()
        db.users.find_one = AsyncMock(return_value=user)
        resp = c.post("/api/auth/subscribe",
            headers={"Authorization": bearer(user)},
            json={"plan": "pro", "billing_period": "weekly", "subscription_status": "active"},
        )
        assert resp.status_code == 422

    def test_subscribe_without_auth_returns_401(self, client):
        c, _ = client
        resp = c.post("/api/auth/subscribe",
            json={"plan": "pro", "billing_period": "monthly", "subscription_status": "active"},
        )
        assert resp.status_code == 401


# ─── POST /api/auth/logout ────────────────────────────────────────────────────

class TestLogout:
    def test_logout_returns_200(self, client):
        c, _ = client
        resp = c.post("/api/auth/logout")
        assert resp.status_code == 200
        assert "message" in resp.json()
