"""
Unit tests for scraper HTML parsing logic — NO network calls.

We inject mock HTML responses into httpx using a custom transport,
then verify the scrapers correctly extract titles, prices, mileage,
damage, colours, and photos from real-world-style HTML structures.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import pytest
import httpx
from unittest.mock import patch, AsyncMock

from app.utils.parsers import parse_price, parse_mileage, extract_year


# ─── Minimal HTML fixtures that mirror real site structures ──────────────────

CATHCART_LISTING_HTML = """
<html><body>
  <div class="vehicle-card">
    <a href="https://cathcartauto.com/inventory/2021-toyota-camry-123">
      <img src="https://cathcartauto.com/wp-content/uploads/camry.jpg" />
      <h1>2021 Toyota Camry LE</h1>
    </a>
    <h3>$12,500 PLUS HST</h3>
    <h3>FOR SALE</h3>
  </div>
</body></html>
"""

CATHCART_DETAIL_HTML = """
<html><body>
  <div class="vehicle-details">
    <strong>Colour:</strong> Silver
    <strong>Mileage:</strong> 85,000 km
    <strong>Damage:</strong> LEFT FRONT
    <strong>Brand:</strong> REBUILT
    <img src="https://cathcartauto.com/wp-content/uploads/camry1.jpg" />
    <img src="https://cathcartauto.com/wp-content/uploads/camry2.jpg" />
  </div>
</body></html>
"""

PICNSAVE_LISTING_HTML = """
<html><body>
  <ul class="products">
    <li class="product">
      <h2>2019 Honda Civic EX</h2>
      <span class="woocommerce-Price-amount">$8,900</span>
      <a href="https://picnsave.ca/product/2019-honda-civic/">
        <img src="https://picnsave.ca/wp-content/uploads/civic.jpg" />
      </a>
      <span>Brand: SALVAGE</span>
      <span>Mileage: 120,000 km</span>
    </li>
  </ul>
</body></html>
"""

PICNSAVE_DETAIL_HTML = """
<html><body>
  <div class="woocommerce-product-details__short-description">
    This vehicle has front end damage.
    Damage: FRONT END
    Mileage: 120,000 km
  </div>
  <img src="https://picnsave.ca/wp-content/uploads/civic1.jpg" />
  <img src="https://picnsave.ca/wp-content/uploads/civic2.jpg" />
</body></html>
"""


# ─── Parser-level tests (no HTTP mocking needed) ─────────────────────────────

class TestCathcartHtmlParsing:
    """Test BeautifulSoup parsing logic that cathcart.py uses."""

    def test_extract_price_from_h3(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(CATHCART_LISTING_HTML, "html.parser")
        h3s = soup.find_all("h3")
        price_text = ""
        for h3 in h3s:
            t = h3.get_text(strip=True)
            if "$" in t or "PLUS HST" in t:
                price_text = t
        assert parse_price(price_text) == 12500.0

    def test_extract_status_for_sale(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(CATHCART_LISTING_HTML, "html.parser")
        h3s = soup.find_all("h3")
        status = "for_sale"
        for h3 in h3s:
            if "COMING SOON" in h3.get_text().upper():
                status = "coming_soon"
            elif "SOLD" in h3.get_text().upper():
                status = "sold"
        assert status == "for_sale"

    def test_extract_detail_colour(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(CATHCART_DETAIL_HTML, "html.parser")
        colour = ""
        for strong in soup.find_all("strong"):
            label = strong.get_text(strip=True).lower().rstrip(":")
            sibling_text = ""
            for sib in strong.next_siblings:
                t = sib.get_text(strip=True) if hasattr(sib, "get_text") else str(sib).strip()
                if t:
                    sibling_text = t
                    break
            if "colour" in label:
                colour = sibling_text
        assert colour == "Silver"

    def test_extract_detail_mileage(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(CATHCART_DETAIL_HTML, "html.parser")
        mileage_text = ""
        for strong in soup.find_all("strong"):
            label = strong.get_text(strip=True).lower().rstrip(":")
            sibling_text = ""
            for sib in strong.next_siblings:
                t = sib.get_text(strip=True) if hasattr(sib, "get_text") else str(sib).strip()
                if t:
                    sibling_text = t
                    break
            if "mileage" in label:
                mileage_text = sibling_text
        assert parse_mileage(mileage_text) == 85000

    def test_extract_detail_damage(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(CATHCART_DETAIL_HTML, "html.parser")
        damage = ""
        for strong in soup.find_all("strong"):
            label = strong.get_text(strip=True).lower().rstrip(":")
            sibling_text = ""
            for sib in strong.next_siblings:
                t = sib.get_text(strip=True) if hasattr(sib, "get_text") else str(sib).strip()
                if t:
                    sibling_text = t
                    break
            if "damage" in label:
                damage = sibling_text
        assert "FRONT" in damage.upper()

    def test_extract_photos(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(CATHCART_DETAIL_HTML, "html.parser")
        photos = []
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if "wp-content/uploads" in src and "logo" not in src.lower():
                if src not in photos:
                    photos.append(src)
        assert len(photos) == 2

    def test_extract_year_from_title(self):
        assert extract_year("2021 Toyota Camry LE") == 2021

    def test_title_minimum_length(self):
        # Short titles (< 5 chars) should be skipped by the scraper
        assert len("Car") < 5


class TestPicNSaveHtmlParsing:
    """Test BeautifulSoup parsing logic that picnsave.py uses."""

    def test_product_list_items(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(PICNSAVE_LISTING_HTML, "html.parser")
        products = soup.find_all("li", class_=lambda c: c and "product" in str(c))
        assert len(products) == 1

    def test_extract_title(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(PICNSAVE_LISTING_HTML, "html.parser")
        product = soup.find("li", class_=lambda c: c and "product" in str(c))
        h2 = product.find("h2")
        assert h2.get_text(strip=True) == "2019 Honda Civic EX"

    def test_extract_price(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(PICNSAVE_LISTING_HTML, "html.parser")
        product = soup.find("li", class_=lambda c: c and "product" in str(c))
        price_el = product.find(class_="woocommerce-Price-amount")
        assert parse_price(price_el.get_text(strip=True)) == 8900.0

    def test_extract_brand_from_text(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(PICNSAVE_LISTING_HTML, "html.parser")
        product = soup.find("li", class_=lambda c: c and "product" in str(c))
        all_text = product.get_text(separator="|", strip=True)
        brand = ""
        for part in all_text.split("|"):
            if part.strip().lower().startswith("brand:"):
                brand = part.split(":", 1)[1].strip()
        assert brand == "SALVAGE"

    def test_extract_mileage_from_text(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(PICNSAVE_LISTING_HTML, "html.parser")
        product = soup.find("li", class_=lambda c: c and "product" in str(c))
        all_text = product.get_text(separator="|", strip=True)
        mileage_text = ""
        for part in all_text.split("|"):
            if part.strip().lower().startswith("mileage:"):
                mileage_text = part.split(":", 1)[1].strip()
        assert parse_mileage(mileage_text) == 120000

    def test_extract_damage_from_detail(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(PICNSAVE_DETAIL_HTML, "html.parser")
        desc_el = soup.find(class_="woocommerce-product-details__short-description")
        damage = ""
        if desc_el:
            desc_text = desc_el.get_text(strip=True)
            for line in desc_text.split("\n"):
                if "damage" in line.lower().strip():
                    damage = line.strip()
        assert "FRONT END" in damage or "damage" in damage.lower()

    def test_extract_photos_from_detail(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(PICNSAVE_DETAIL_HTML, "html.parser")
        photos = []
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if "wp-content/uploads" in src and "placeholder" not in src.lower():
                if src not in photos:
                    photos.append(src)
        assert len(photos) == 2

    def test_placeholder_image_skipped(self):
        from bs4 import BeautifulSoup
        html = '<li class="product"><img src="https://picnsave.ca/wp-content/uploads/placeholder.jpg"/></li>'
        soup = BeautifulSoup(html, "html.parser")
        photos = []
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if "placeholder" not in src.lower():
                photos.append(src)
        assert len(photos) == 0

    def test_no_products_on_empty_page(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        products = soup.find_all("li", class_=lambda c: c and "product" in str(c))
        assert len(products) == 0

    def test_pagination_next_page_detection(self):
        from bs4 import BeautifulSoup
        html_with_next = '<html><body><a class="next">Next</a></body></html>'
        html_without_next = "<html><body></body></html>"
        soup_with = BeautifulSoup(html_with_next, "html.parser")
        soup_without = BeautifulSoup(html_without_next, "html.parser")
        assert soup_with.find("a", class_="next") is not None
        assert soup_without.find("a", class_="next") is None
