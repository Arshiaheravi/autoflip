"""
Unit tests for the email notification service.

These tests do NOT send real emails and do NOT require SENDGRID_API_KEY.
They verify:
  - HTML/plain-text email content is generated correctly
  - Missing API key causes graceful no-op (no crash)
  - send_deal_alert_email returns False when key is absent
"""
import asyncio
import os
import sys

import pytest

# Make backend importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.email import (
    _build_html_email,
    _build_plain_text,
    _format_currency,
    send_deal_alert_email,
    ALERT_MIN_SCORE,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────
SAMPLE_LISTING = {
    "id": "test-listing-001",
    "title": "2019 Honda Civic EX",
    "price": 8500,
    "market_value": 14000,
    "profit_best": 3200,
    "profit_worst": 1800,
    "deal_score": 9,
    "deal_label": "BUY",
    "damage": "FRONT END",
    "mileage": 95000,
    "colour": "Blue",
    "brand": "SALVAGE TITLE",
    "year": 2019,
    "source": "cathcart_rebuilders",
    "url": "https://cathcartauto.com/vehicles/2019-honda-civic-test",
    "photo": "https://cathcartauto.com/wp-content/uploads/test-photo.jpg",
}


# ──────────────────────────────────────────────────────────────────────────────
# Currency formatter
# ──────────────────────────────────────────────────────────────────────────────
class TestFormatCurrency:
    def test_integer_value(self):
        assert _format_currency(5000) == "$5,000"

    def test_float_value(self):
        assert _format_currency(1234.56) == "$1,235"

    def test_zero(self):
        assert _format_currency(0) == "$0"

    def test_none_returns_na(self):
        assert _format_currency(None) == "N/A"

    def test_large_value(self):
        assert _format_currency(100000) == "$100,000"


# ──────────────────────────────────────────────────────────────────────────────
# HTML email generation
# ──────────────────────────────────────────────────────────────────────────────
class TestBuildHtmlEmail:
    def test_contains_title(self):
        html = _build_html_email(SAMPLE_LISTING)
        assert "2019 Honda Civic EX" in html

    def test_contains_buy_label(self):
        html = _build_html_email(SAMPLE_LISTING)
        assert "BUY Deal Alert" in html

    def test_contains_deal_score(self):
        html = _build_html_email(SAMPLE_LISTING)
        assert "9" in html  # deal score

    def test_contains_profit(self):
        html = _build_html_email(SAMPLE_LISTING)
        assert "$3,200" in html  # profit_best

    def test_contains_auction_price(self):
        html = _build_html_email(SAMPLE_LISTING)
        assert "$8,500" in html  # price

    def test_contains_cta_link(self):
        html = _build_html_email(SAMPLE_LISTING)
        assert "cathcartauto.com" in html

    def test_contains_photo(self):
        html = _build_html_email(SAMPLE_LISTING)
        assert "test-photo.jpg" in html

    def test_no_photo_when_empty(self):
        listing_no_photo = {**SAMPLE_LISTING, "photo": ""}
        html = _build_html_email(listing_no_photo)
        # Should not crash, and should still have title
        assert "2019 Honda Civic EX" in html

    def test_valid_html_structure(self):
        html = _build_html_email(SAMPLE_LISTING)
        assert html.strip().startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_handles_missing_optional_fields(self):
        """Should not crash when optional fields are absent."""
        minimal = {
            "title": "2020 Toyota Camry",
            "deal_score": 8,
            "url": "https://example.com",
        }
        html = _build_html_email(minimal)
        assert "2020 Toyota Camry" in html
        assert "N/A" in html  # price shown as N/A


# ──────────────────────────────────────────────────────────────────────────────
# Plain-text email generation
# ──────────────────────────────────────────────────────────────────────────────
class TestBuildPlainText:
    def test_contains_title(self):
        text = _build_plain_text(SAMPLE_LISTING)
        assert "2019 Honda Civic EX" in text

    def test_contains_score(self):
        text = _build_plain_text(SAMPLE_LISTING)
        assert "9" in text

    def test_contains_price(self):
        text = _build_plain_text(SAMPLE_LISTING)
        assert "$8,500" in text

    def test_contains_url(self):
        text = _build_plain_text(SAMPLE_LISTING)
        assert "cathcartauto.com" in text

    def test_contains_mileage(self):
        text = _build_plain_text(SAMPLE_LISTING)
        assert "95,000 km" in text


# ──────────────────────────────────────────────────────────────────────────────
# Graceful no-op when SENDGRID_API_KEY is missing
# ──────────────────────────────────────────────────────────────────────────────
class TestSendDealAlertEmailNoKey:
    def test_returns_false_when_no_key(self, monkeypatch):
        """send_deal_alert_email must return False (not crash) when API key is absent."""
        monkeypatch.delenv("SENDGRID_API_KEY", raising=False)

        result = asyncio.run(
            send_deal_alert_email(
                to_email="test@example.com",
                to_name="Test User",
                listing=SAMPLE_LISTING,
            )
        )
        assert result is False

    def test_does_not_raise_when_no_key(self, monkeypatch):
        """send_deal_alert_email must never raise an exception, even without a key."""
        monkeypatch.delenv("SENDGRID_API_KEY", raising=False)

        try:
            asyncio.run(
                send_deal_alert_email(
                    to_email="test@example.com",
                    to_name="",
                    listing={},
                )
            )
        except Exception as exc:
            pytest.fail(f"send_deal_alert_email raised unexpectedly: {exc}")


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
class TestConstants:
    def test_alert_min_score_is_8(self):
        """BUY deal alert threshold must be 8 (as documented)."""
        assert ALERT_MIN_SCORE == 8
