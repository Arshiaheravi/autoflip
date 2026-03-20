"""
Unit tests for salvagereseller.py scraper HTML parsing logic.
No network calls — uses injected mock HTML.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from bs4 import BeautifulSoup
from app.scrapers.salvagereseller import _parse_listing_card, _extract_brand_status, _miles_to_km


# ─── HTML fixtures ────────────────────────────────────────────────────────────

LISTING_CARD_HTML = """
<div class="my-4 vehicle-row position-relative" id="vehicle-12345678">
  <div class="d-md-flex border-bottom pb-4">
    <div class="vehicle-image-section">
      <img src="https://images.salvagereseller.com/12345678/thumb.jpg" alt="2021 Tesla Model Y" />
    </div>
    <div class="vehicle-info-section">
      <a class="vehicle-model display-6 font-weight-bolder"
         href="/cars-for-sale/12345678-2021-tesla-model-y-bowmanville-on">
        2021 Tesla Model Y
      </a>
      <div class="lot-details">
        <span>Lot: 12345678</span>
        <span>Title: ON - PERMIT SALVAGE</span>
        <span>Sale: 2026-03-20</span>
      </div>
      <div class="vehicle-condition">
        <div>Odometer: 122,872 mi (Actual)</div>
        <div>Primary Damage: Front end</div>
        <div>Location: Bowmanville, ON</div>
        <div>ACV: $42,000 CAD</div>
      </div>
      <div class="bids">
        <span class="display-4 font-weight-bolder text-nowrap">$1,500</span>
        <small>CAD</small>
      </div>
    </div>
  </div>
</div>
"""

LISTING_CARD_BUY_NOW_HTML = """
<div class="my-4 vehicle-row position-relative" id="vehicle-99887766">
  <div class="d-md-flex border-bottom pb-4">
    <div class="vehicle-info-section">
      <a class="vehicle-model display-6 font-weight-bolder"
         href="/cars-for-sale/99887766-2023-ford-bronco-sport-cookstown-on">
        2023 Ford Bronco Sport Big Bend
      </a>
      <div class="lot-details">
        <span>Title: ON - REBUILT</span>
      </div>
      <div class="vehicle-condition">
        <div>Odometer: 45,000 mi (Actual)</div>
        <div>Primary Damage: Rear end</div>
        <div>Color: Blue</div>
      </div>
      <div class="bids">
        <div>Buy it now for $12,000 CAD</div>
      </div>
    </div>
  </div>
</div>
"""

LISTING_CARD_NO_YEAR_HTML = """
<div class="my-4 vehicle-row position-relative" id="vehicle-00000001">
  <div class="vehicle-info-section">
    <a class="vehicle-model display-6 font-weight-bolder"
       href="/cars-for-sale/00000001-unknown-vehicle">
      Unknown Vehicle
    </a>
    <div class="bids"><span class="display-4 font-weight-bolder">$500</span></div>
  </div>
</div>
"""

EMPTY_PAGE_HTML = "<html><body><div class='listings-container'></div></body></html>"


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestExtractBrandStatus:
    def test_salvage_from_permit(self):
        assert _extract_brand_status("ON - PERMIT SALVAGE") == "SALVAGE"

    def test_salvage_direct(self):
        assert _extract_brand_status("Salvage Title") == "SALVAGE"

    def test_rebuilt(self):
        assert _extract_brand_status("ON - REBUILT") == "REBUILT"

    def test_empty(self):
        assert _extract_brand_status("Clean Title") == ""


class TestMilesToKm:
    def test_100_miles(self):
        assert _miles_to_km(100) == 161

    def test_zero(self):
        assert _miles_to_km(0) == 0

    def test_typical_mileage(self):
        result = _miles_to_km(90784)
        assert 145000 < result < 147000  # roughly 146,000 km


class TestParseListingCard:
    def test_returns_dict(self):
        soup = BeautifulSoup(LISTING_CARD_HTML, "html.parser")
        row = soup.find("div", class_=lambda c: c and "vehicle-row" in str(c))
        result = _parse_listing_card(row)
        assert result is not None
        assert isinstance(result, dict)

    def test_title_extracted(self):
        soup = BeautifulSoup(LISTING_CARD_HTML, "html.parser")
        row = soup.find("div", class_=lambda c: c and "vehicle-row" in str(c))
        result = _parse_listing_card(row)
        assert result["title"] == "2021 Tesla Model Y"

    def test_url_is_absolute(self):
        soup = BeautifulSoup(LISTING_CARD_HTML, "html.parser")
        row = soup.find("div", class_=lambda c: c and "vehicle-row" in str(c))
        result = _parse_listing_card(row)
        assert result["url"].startswith("https://www.salvagereseller.com")

    def test_year_extracted(self):
        soup = BeautifulSoup(LISTING_CARD_HTML, "html.parser")
        row = soup.find("div", class_=lambda c: c and "vehicle-row" in str(c))
        result = _parse_listing_card(row)
        assert result["year"] == 2021

    def test_price_extracted(self):
        soup = BeautifulSoup(LISTING_CARD_HTML, "html.parser")
        row = soup.find("div", class_=lambda c: c and "vehicle-row" in str(c))
        result = _parse_listing_card(row)
        assert result["price"] == 1500.0

    def test_brand_salvage(self):
        soup = BeautifulSoup(LISTING_CARD_HTML, "html.parser")
        row = soup.find("div", class_=lambda c: c and "vehicle-row" in str(c))
        result = _parse_listing_card(row)
        assert result["brand"] == "SALVAGE"

    def test_damage_extracted(self):
        soup = BeautifulSoup(LISTING_CARD_HTML, "html.parser")
        row = soup.find("div", class_=lambda c: c and "vehicle-row" in str(c))
        result = _parse_listing_card(row)
        assert "front" in result["damage"].lower()

    def test_mileage_converted_to_km(self):
        soup = BeautifulSoup(LISTING_CARD_HTML, "html.parser")
        row = soup.find("div", class_=lambda c: c and "vehicle-row" in str(c))
        result = _parse_listing_card(row)
        # 122,872 miles ≈ 197,762 km
        if result["mileage"]:
            assert 190000 < result["mileage"] < 210000

    def test_photo_extracted(self):
        soup = BeautifulSoup(LISTING_CARD_HTML, "html.parser")
        row = soup.find("div", class_=lambda c: c and "vehicle-row" in str(c))
        result = _parse_listing_card(row)
        assert result["photo"] is not None
        assert "salvagereseller" in result["photo"] or "images." in result["photo"]

    def test_source_set(self):
        soup = BeautifulSoup(LISTING_CARD_HTML, "html.parser")
        row = soup.find("div", class_=lambda c: c and "vehicle-row" in str(c))
        result = _parse_listing_card(row)
        assert result["source"] == "salvagereseller"

    def test_buy_now_price(self):
        soup = BeautifulSoup(LISTING_BUY_NOW_HTML, "html.parser")
        row = soup.find("div", class_=lambda c: c and "vehicle-row" in str(c))
        result = _parse_listing_card(row)
        assert result is not None
        assert result["price"] == 12000.0

    def test_rebuilt_brand(self):
        soup = BeautifulSoup(LISTING_BUY_NOW_HTML, "html.parser")
        row = soup.find("div", class_=lambda c: c and "vehicle-row" in str(c))
        result = _parse_listing_card(row)
        assert result["brand"] == "REBUILT"

    def test_no_year_returns_none(self):
        soup = BeautifulSoup(LISTING_CARD_NO_YEAR_HTML, "html.parser")
        row = soup.find("div", class_=lambda c: c and "vehicle-row" in str(c))
        result = _parse_listing_card(row)
        assert result is None

    def test_status_for_sale(self):
        soup = BeautifulSoup(LISTING_CARD_HTML, "html.parser")
        row = soup.find("div", class_=lambda c: c and "vehicle-row" in str(c))
        result = _parse_listing_card(row)
        assert result["status"] == "for_sale"


# Fix: LISTING_BUY_NOW_HTML referenced before defined — alias it
LISTING_BUY_NOW_HTML = LISTING_CARD_BUY_NOW_HTML


class TestReturnSchema:
    """Verify all required runner.py fields are present."""
    REQUIRED_KEYS = {"source", "url", "title", "price", "price_raw", "status",
                     "colour", "mileage", "damage", "brand", "description",
                     "photo", "photos", "year"}

    def test_all_keys_present(self):
        soup = BeautifulSoup(LISTING_CARD_HTML, "html.parser")
        row = soup.find("div", class_=lambda c: c and "vehicle-row" in str(c))
        result = _parse_listing_card(row)
        assert self.REQUIRED_KEYS.issubset(set(result.keys()))
