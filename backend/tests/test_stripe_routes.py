"""
Unit tests for /api/stripe/* routes.
MongoDB and stripe are fully mocked — no real network calls.

Covers:
  - POST /api/stripe/create-checkout-session (auth, monthly, yearly, no-key 402)
  - POST /api/stripe/webhook (no-config ignored, checkout.session.completed,
    customer.subscription.deleted, invoice.payment_failed)
"""
import sys
import os
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
def mock_stripe():
    """Mock stripe module with a fake checkout session and webhook helpers."""
    fake_session = MagicMock()
    fake_session.url = "https://checkout.stripe.com/pay/test123"
    fake_session.id = "cs_test_abc123"

    stripe_mod = MagicMock()
    stripe_mod.checkout.Session.create.return_value = fake_session
    # Make error classes real exception types so except clauses work
    stripe_mod.error.StripeError = Exception
    stripe_mod.error.SignatureVerificationError = Exception
    return stripe_mod


STRIPE_ENV = {
    "STRIPE_SECRET_KEY": "sk_test_dummy",
    "STRIPE_PRICE_MONTHLY_ID": "price_monthly_test",
    "STRIPE_PRICE_YEARLY_ID": "price_yearly_test",
    "STRIPE_WEBHOOK_SECRET": "whsec_test",
}


def _make_client(mock_db, extra_patches=()):
    """Build a TestClient with all standard patches applied."""
    patches = [
        patch("app.database.db", mock_db),
        patch("app.routes.auth.db", mock_db),
        patch("app.routes.stripe_routes.db", mock_db),
        patch("app.routes.listings.db", mock_db),
        patch("app.routes.settings.db", mock_db),
        patch("app.routes.scrape.db", mock_db),
        patch("app.main.db", mock_db),
        patch("app.scrapers.runner.run_full_scrape", new_callable=AsyncMock),
        patch("app.scrapers.runner.scheduled_scrape", new_callable=AsyncMock),
        patch("app.services.autotrader.load_at_cache_from_db", new_callable=AsyncMock),
        patch.dict(os.environ, STRIPE_ENV),
        *extra_patches,
    ]
    return patches


@pytest.fixture
def client(mock_db, mock_stripe):
    extra = [patch("app.routes.stripe_routes._get_stripe", return_value=mock_stripe)]
    ctx_managers = _make_client(mock_db, extra)
    with ctx_managers[0]:
        with ctx_managers[1]:
            with ctx_managers[2]:
                with ctx_managers[3]:
                    with ctx_managers[4]:
                        with ctx_managers[5]:
                            with ctx_managers[6]:
                                with ctx_managers[7]:
                                    with ctx_managers[8]:
                                        with ctx_managers[9]:
                                            with ctx_managers[10]:
                                                with ctx_managers[11]:
                                                    from fastapi.testclient import TestClient
                                                    from app.main import app
                                                    app.router.on_startup.clear()
                                                    app.router.on_shutdown.clear()
                                                    with TestClient(app, raise_server_exceptions=True) as c:
                                                        yield c, mock_db, mock_stripe


# ─── POST /api/stripe/create-checkout-session ────────────────────────────────

class TestCreateCheckoutSession:
    def test_requires_authentication(self, client):
        c, db, _ = client
        resp = c.post("/api/stripe/create-checkout-session", json={"billing_period": "monthly"})
        assert resp.status_code == 401

    def test_monthly_checkout_returns_url(self, client):
        c, db, stripe = client
        user = make_user()
        db.users.find_one = AsyncMock(return_value=user)
        resp = c.post(
            "/api/stripe/create-checkout-session",
            headers={"Authorization": bearer(user)},
            json={"billing_period": "monthly"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "url" in data
        assert data["url"] == "https://checkout.stripe.com/pay/test123"
        assert "session_id" in data

    def test_yearly_checkout_returns_url(self, client):
        c, db, stripe = client
        user = make_user()
        db.users.find_one = AsyncMock(return_value=user)
        resp = c.post(
            "/api/stripe/create-checkout-session",
            headers={"Authorization": bearer(user)},
            json={"billing_period": "yearly"},
        )
        assert resp.status_code == 200
        assert resp.json()["url"] == "https://checkout.stripe.com/pay/test123"

    def test_uses_monthly_price_id(self, client):
        c, db, stripe = client
        user = make_user()
        db.users.find_one = AsyncMock(return_value=user)
        c.post(
            "/api/stripe/create-checkout-session",
            headers={"Authorization": bearer(user)},
            json={"billing_period": "monthly"},
        )
        call_kwargs = stripe.checkout.Session.create.call_args[1]
        line_items = call_kwargs["line_items"]
        assert line_items[0]["price"] == "price_monthly_test"

    def test_uses_yearly_price_id(self, client):
        c, db, stripe = client
        user = make_user()
        db.users.find_one = AsyncMock(return_value=user)
        c.post(
            "/api/stripe/create-checkout-session",
            headers={"Authorization": bearer(user)},
            json={"billing_period": "yearly"},
        )
        call_kwargs = stripe.checkout.Session.create.call_args[1]
        assert call_kwargs["line_items"][0]["price"] == "price_yearly_test"

    def test_sets_client_reference_id_to_user_id(self, client):
        c, db, stripe = client
        user = make_user()
        db.users.find_one = AsyncMock(return_value=user)
        c.post(
            "/api/stripe/create-checkout-session",
            headers={"Authorization": bearer(user)},
            json={"billing_period": "monthly"},
        )
        kwargs = stripe.checkout.Session.create.call_args[1]
        assert kwargs["client_reference_id"] == user["id"]

    def test_no_stripe_key_returns_402(self, client):
        c, db, _ = client
        user = make_user()
        db.users.find_one = AsyncMock(return_value=user)
        with patch("app.routes.stripe_routes._get_stripe", return_value=None):
            resp = c.post(
                "/api/stripe/create-checkout-session",
                headers={"Authorization": bearer(user)},
                json={"billing_period": "monthly"},
            )
        assert resp.status_code == 402

    def test_invalid_billing_period_returns_422(self, client):
        c, db, _ = client
        user = make_user()
        db.users.find_one = AsyncMock(return_value=user)
        resp = c.post(
            "/api/stripe/create-checkout-session",
            headers={"Authorization": bearer(user)},
            json={"billing_period": "weekly"},
        )
        assert resp.status_code == 422


# ─── POST /api/stripe/webhook ────────────────────────────────────────────────

class TestStripeWebhook:
    def _event(self, event_type, obj):
        return {"id": "evt_test_123", "type": event_type, "data": {"object": obj}}

    def test_no_stripe_config_returns_ignored(self, client):
        c, db, _ = client
        with patch("app.routes.stripe_routes._get_stripe", return_value=None):
            resp = c.post(
                "/api/stripe/webhook",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=abc"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_checkout_completed_upgrades_user(self, client):
        c, db, stripe = client
        event = self._event("checkout.session.completed", {
            "client_reference_id": "test-uid-001",
            "customer": "cus_test123",
            "subscription": "sub_test123",
            "metadata": {"billing_period": "monthly", "user_id": "test-uid-001"},
        })
        stripe.Webhook.construct_event.return_value = event
        resp = c.post(
            "/api/stripe/webhook",
            content=b'{"type":"checkout.session.completed"}',
            headers={"stripe-signature": "t=1,v1=abc"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        db.users.update_one.assert_called_once()
        update_doc = db.users.update_one.call_args[0][1]["$set"]
        assert update_doc["plan"] == "pro"
        assert update_doc["subscription_status"] == "active"

    def test_subscription_deleted_cancels_user(self, client):
        c, db, stripe = client
        event = self._event("customer.subscription.deleted", {
            "customer": "cus_test123",
        })
        stripe.Webhook.construct_event.return_value = event
        resp = c.post(
            "/api/stripe/webhook",
            content=b'{"type":"customer.subscription.deleted"}',
            headers={"stripe-signature": "t=1,v1=abc"},
        )
        assert resp.status_code == 200
        db.users.update_one.assert_called_once()
        update_doc = db.users.update_one.call_args[0][1]["$set"]
        assert update_doc["plan"] == "free"
        assert update_doc["subscription_status"] == "cancelled"

    def test_payment_failed_marks_past_due(self, client):
        c, db, stripe = client
        event = self._event("invoice.payment_failed", {
            "customer": "cus_test123",
        })
        stripe.Webhook.construct_event.return_value = event
        resp = c.post(
            "/api/stripe/webhook",
            content=b'{"type":"invoice.payment_failed"}',
            headers={"stripe-signature": "t=1,v1=abc"},
        )
        assert resp.status_code == 200
        db.users.update_one.assert_called_once()
        update_doc = db.users.update_one.call_args[0][1]["$set"]
        assert update_doc["subscription_status"] == "past_due"

    def test_subscription_updated_syncs_status(self, client):
        c, db, stripe = client
        event = self._event("customer.subscription.updated", {
            "customer": "cus_test123",
            "status": "past_due",
        })
        stripe.Webhook.construct_event.return_value = event
        resp = c.post(
            "/api/stripe/webhook",
            content=b'{"type":"customer.subscription.updated"}',
            headers={"stripe-signature": "t=1,v1=abc"},
        )
        assert resp.status_code == 200
        update_doc = db.users.update_one.call_args[0][1]["$set"]
        assert update_doc["subscription_status"] == "past_due"

    def test_unknown_event_type_returns_ok(self, client):
        c, db, stripe = client
        event = self._event("customer.created", {"id": "cus_test"})
        stripe.Webhook.construct_event.return_value = event
        resp = c.post(
            "/api/stripe/webhook",
            content=b'{"type":"customer.created"}',
            headers={"stripe-signature": "t=1,v1=abc"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        db.users.update_one.assert_not_called()
