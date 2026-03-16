"""
Unit tests for the email_alerts service.
Tests HTML/text generation, graceful fallback when keys are missing.
No real emails are sent — all SMTP/SendGrid calls are mocked.
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.email_alerts import (
    _format_currency,
    _build_deal_alert_html,
    _build_deal_alert_text,
    send_deal_alert,
    ALERT_MIN_SCORE,
)

# ── Sample listing fixture ───────────────────────────────────────────────────
SAMPLE_LISTING = {
    "id": "test-listing-uuid-001",
    "title": "2019 Honda Civic LX",
    "price": 8500,
    "market_value": 14000,
    "profit_best": 3200,
    "profit_worst": 1800,
    "roi_best": 37.6,
    "roi_worst": 21.2,
    "deal_score": 9,
    "deal_label": "BUY",
    "damage": "FRONT END",
    "brand": "SALVAGE TITLE",
    "colour": "Silver",
    "mileage": 112000,
    "source": "cathcart_rebuilders",
    "url": "https://cathcartauto.com/vehicles/1234",
    "photo": "https://example.com/photo.jpg",
}


# ── _format_currency ─────────────────────────────────────────────────────────
class TestFormatCurrency:
    def test_formats_positive_number(self):
        assert _format_currency(8500) == "$8,500"

    def test_formats_large_number(self):
        assert _format_currency(14000) == "$14,000"

    def test_formats_zero(self):
        assert _format_currency(0) == "$0"

    def test_handles_none(self):
        assert _format_currency(None) == "N/A"

    def test_formats_float(self):
        result = _format_currency(3200.75)
        assert "$3,201" in result or "$3,200" in result  # rounded


# ── HTML email builder ───────────────────────────────────────────────────────
class TestBuildDealAlertHtml:
    def test_contains_title(self):
        html = _build_deal_alert_html(SAMPLE_LISTING)
        assert "2019 Honda Civic LX" in html

    def test_contains_price(self):
        html = _build_deal_alert_html(SAMPLE_LISTING)
        assert "$8,500" in html

    def test_contains_profit(self):
        html = _build_deal_alert_html(SAMPLE_LISTING)
        assert "$3,200" in html

    def test_contains_score_badge(self):
        html = _build_deal_alert_html(SAMPLE_LISTING)
        assert "Score 9/10" in html
        assert "BUY" in html

    def test_contains_photo_img_tag(self):
        html = _build_deal_alert_html(SAMPLE_LISTING)
        assert "<img" in html
        assert "example.com/photo.jpg" in html

    def test_contains_auction_url(self):
        html = _build_deal_alert_html(SAMPLE_LISTING)
        assert "cathcartauto.com" in html

    def test_contains_unsubscribe_link(self):
        html = _build_deal_alert_html(SAMPLE_LISTING)
        assert "unsubscribe" in html.lower()

    def test_valid_html_structure(self):
        html = _build_deal_alert_html(SAMPLE_LISTING)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_no_photo_listing(self):
        """Should not crash when listing has no photo."""
        listing = {**SAMPLE_LISTING, "photo": None}
        html = _build_deal_alert_html(listing)
        assert "2019 Honda Civic LX" in html
        assert "<img" not in html


# ── Plain text builder ───────────────────────────────────────────────────────
class TestBuildDealAlertText:
    def test_contains_title(self):
        text = _build_deal_alert_text(SAMPLE_LISTING)
        assert "2019 Honda Civic LX" in text

    def test_contains_buy_label(self):
        text = _build_deal_alert_text(SAMPLE_LISTING)
        assert "BUY" in text

    def test_contains_score(self):
        text = _build_deal_alert_text(SAMPLE_LISTING)
        assert "9/10" in text

    def test_contains_listing_url(self):
        text = _build_deal_alert_text(SAMPLE_LISTING)
        assert "cathcartauto.com" in text

    def test_contains_unsubscribe(self):
        text = _build_deal_alert_text(SAMPLE_LISTING)
        assert "unsubscribe" in text.lower()


# ── send_deal_alert graceful fallback ────────────────────────────────────────
class TestSendDealAlertFallback:
    @pytest.mark.asyncio
    async def test_returns_false_when_no_keys_configured(self):
        """When SENDGRID_API_KEY and SMTP_USER are both absent, return False silently."""
        with (
            patch("app.services.email_alerts.SENDGRID_API_KEY", None),
            patch("app.services.email_alerts.SMTP_USER", None),
            patch("app.services.email_alerts.SMTP_PASSWORD", None),
        ):
            result = await send_deal_alert("test@example.com", SAMPLE_LISTING)
        assert result is False

    @pytest.mark.asyncio
    async def test_uses_sendgrid_when_key_set(self):
        """When SENDGRID_API_KEY is set, it calls the SendGrid path."""
        with (
            patch("app.services.email_alerts.SENDGRID_API_KEY", "SG.test-key"),
            patch("app.services.email_alerts.send_deal_alert_sendgrid", new_callable=AsyncMock, return_value=True),
        ):
            result = await send_deal_alert("test@example.com", SAMPLE_LISTING)
        assert result is True

    @pytest.mark.asyncio
    async def test_uses_smtp_fallback_when_no_sendgrid(self):
        """When only SMTP is configured, use SMTP path."""
        with (
            patch("app.services.email_alerts.SENDGRID_API_KEY", None),
            patch("app.services.email_alerts.SMTP_USER", "user@gmail.com"),
            patch("app.services.email_alerts.SMTP_PASSWORD", "password123"),
            patch("app.services.email_alerts.send_deal_alert_smtp", new_callable=AsyncMock, return_value=True),
        ):
            result = await send_deal_alert("test@example.com", SAMPLE_LISTING)
        assert result is True


# ── ALERT_MIN_SCORE constant ─────────────────────────────────────────────────
class TestAlertMinScore:
    def test_min_score_is_8(self):
        """BUY deal alerts should fire at score >= 8."""
        assert ALERT_MIN_SCORE == 8

    def test_score_9_would_trigger(self):
        assert SAMPLE_LISTING["deal_score"] >= ALERT_MIN_SCORE
