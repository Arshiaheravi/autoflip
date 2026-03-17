"""
Unit tests for copart_ontario.py scraper HTML parsing logic.
No network calls — uses injected mock HTML that mirrors the state/ontario page layout.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from bs4 import BeautifulSoup
from app.scrapers.copart_ontario import _parse_listing_block, _extract_brand_status, _miles_to_km


# ─── HTML fixtures ────────────────────────────────────────────────────────────

# Simulates the div-based structure on the state/ontario page (no vehicle-row class)
LISTING_BLOCK_HTML = """
<div>
  <div>
    <img src="https://images.salvagereseller.com/45601234/thumb.jpg" alt="2022 Honda HR-V" />
  </div>
  <div>
    <a href="/cars-for-sale/45601234-2022-honda-hr-v-bowmanville-on">
      2022 Honda HR-V LX
    </a>
    <div>
      Title: ON ST
      Lot: 45601234
    </div>
    <div>
      Odometer: 48,200 mi (Actual)
      Damage: Front end
      Location: Bowmanville, ON
    </div>
    <div>
      Current Bid: $200 CAD
    </div>
  </div>
</div>
"""

LISTING_BLOCK_BUY_NOW_HTML = """
<div>
  <div>
    <a href="/cars-for-sale/78901234-2020-toyota-rav4-ottawa-on">
      2020 Toyota RAV4 XLE
    </a>
    <div>
      Title: ON SALVAGE
    </div>
    <div>
      Odometer: 95,000 mi (Actual)
      Damage: Rear end
      Color: Silver
    </div>
    <div>
      Buy it now for $8,500 CAD
    </div>
  </div>
</div>
"""

LISTING_BLOCK_NO_PRICE_HTML = """
<div>
  <a href="/cars-for-sale/11112222-2018-ford-escape-oshawa-on">
    2018 Ford Escape SE
  </a>
  <div>Odometer: 155,000 mi</div>
  <div>Damage: Minor Dents / Scratches</div>
</div>
"""

LISTING_BLOCK_NO_YEAR_HTML = """
<div>
  <a href="/cars-for-sale/99990000-honda-civic-bowmanville-on">
    Honda Civic (no year)
  </a>
  <div>Current Bid: $500</div>
</div>
"""


# ─── Unit tests ───────────────────────────────────────────────────────────────

class TestMilesConversion:
    def test_miles_to_km_standard(self):
        assert _miles_to_km(1000) == 1609

    def test_miles_to_km_zero(self):
        assert _miles_to_km(0) == 0

    def test_miles_to_km_high(self):
        km = _miles_to_km(95000)
        assert 152_000 < km < 154_000


class TestExtractBrandStatus:
    def test_salvage_detected(self):
        assert _extract_brand_status("ON SALVAGE") == "SALVAGE"

    def test_permit_detected(self):
        assert _extract_brand_status("ON - PERMIT SALVAGE") == "SALVAGE"

    def test_rebuilt_detected(self):
        assert _extract_brand_status("ON REBUILT") == "REBUILT"

    def test_unknown_returns_empty(self):
        assert _extract_brand_status("Clean title") == ""


class TestParseListingBlock:
    def test_basic_listing_title_and_url(self):
        soup = BeautifulSoup(LISTING_BLOCK_HTML, "html.parser")
        result = _parse_listing_block(soup.find("div"))
        assert result is not None
        assert "2022 Honda HR-V" in result["title"]
        assert "/cars-for-sale/45601234" in result["url"]
        assert result["source"] == "copart_on"

    def test_basic_listing_year_extracted(self):
        soup = BeautifulSoup(LISTING_BLOCK_HTML, "html.parser")
        result = _parse_listing_block(soup.find("div"))
        assert result["year"] == 2022

    def test_basic_listing_mileage_converted_to_km(self):
        soup = BeautifulSoup(LISTING_BLOCK_HTML, "html.parser")
        result = _parse_listing_block(soup.find("div"))
        # 48,200 miles ≈ 77,570 km
        assert result["mileage"] is not None
        assert 77_000 < result["mileage"] < 78_500

    def test_basic_listing_damage_extracted(self):
        soup = BeautifulSoup(LISTING_BLOCK_HTML, "html.parser")
        result = _parse_listing_block(soup.find("div"))
        assert "front" in result["damage"].lower()

    def test_basic_listing_photo_extracted(self):
        soup = BeautifulSoup(LISTING_BLOCK_HTML, "html.parser")
        result = _parse_listing_block(soup.find("div"))
        assert result["photo"] is not None
        assert "images.salvagereseller.com" in result["photo"]

    def test_buy_now_price_preferred(self):
        soup = BeautifulSoup(LISTING_BLOCK_BUY_NOW_HTML, "html.parser")
        result = _parse_listing_block(soup.find("div"))
        assert result is not None
        assert result["price"] == 8500.0
        assert "Buy it now" in result["price_raw"]

    def test_buy_now_colour_extracted(self):
        soup = BeautifulSoup(LISTING_BLOCK_BUY_NOW_HTML, "html.parser")
        result = _parse_listing_block(soup.find("div"))
        assert result["colour"] == "Silver"

    def test_buy_now_brand_salvage(self):
        soup = BeautifulSoup(LISTING_BLOCK_BUY_NOW_HTML, "html.parser")
        result = _parse_listing_block(soup.find("div"))
        assert result["brand"] == "SALVAGE"

    def test_no_price_returns_zero(self):
        soup = BeautifulSoup(LISTING_BLOCK_NO_PRICE_HTML, "html.parser")
        result = _parse_listing_block(soup.find("div"))
        assert result is not None
        assert result["price"] == 0.0

    def test_no_year_returns_none(self):
        soup = BeautifulSoup(LISTING_BLOCK_NO_YEAR_HTML, "html.parser")
        # Should return None because no year found
        result = _parse_listing_block(soup.find("div"))
        assert result is None

    def test_url_uses_base_url_for_relative_href(self):
        soup = BeautifulSoup(LISTING_BLOCK_HTML, "html.parser")
        result = _parse_listing_block(soup.find("div"))
        assert result["url"].startswith("https://www.salvagereseller.com")

    def test_photos_list_populated(self):
        soup = BeautifulSoup(LISTING_BLOCK_HTML, "html.parser")
        result = _parse_listing_block(soup.find("div"))
        assert isinstance(result["photos"], list)
        assert len(result["photos"]) >= 1

    def test_mileage_high_conversion(self):
        soup = BeautifulSoup(LISTING_BLOCK_BUY_NOW_HTML, "html.parser")
        result = _parse_listing_block(soup.find("div"))
        # 95,000 miles ≈ 152,887 km
        assert result["mileage"] is not None
        assert 152_000 < result["mileage"] < 154_000
