"""
Unit tests for backend/app/utils/parsers.py

Every edge case for price, mileage, and year parsing.
These are critical — bad parsing = wrong deal scores.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from app.utils.parsers import parse_price, parse_mileage, extract_year


class TestParsePrice:
    # ── Happy path ─────────────────────────────────────────────────────────
    def test_simple_dollar_amount(self):
        assert parse_price("$5,000") == 5000.0

    def test_price_with_hst_suffix(self):
        assert parse_price("$8,500 PLUS HST") == 8500.0

    def test_price_as_is_suffix(self):
        assert parse_price("$3,200 AS IS") == 3200.0

    def test_price_with_plus_lowercase(self):
        assert parse_price("$12,000 plus HST") == 12000.0

    def test_price_with_decimals(self):
        assert parse_price("$6,999.99") == 6999.99

    def test_no_comma(self):
        assert parse_price("$15000") == 15000.0

    # ── Edge cases ─────────────────────────────────────────────────────────
    def test_none_input_returns_none(self):
        assert parse_price(None) is None

    def test_empty_string_returns_none(self):
        assert parse_price("") is None

    def test_call_for_price_returns_none(self):
        assert parse_price("Call for price") is None

    def test_hash_placeholder_returns_none(self):
        assert parse_price("$####") is None

    def test_on_sale_returns_none(self):
        assert parse_price("On Sale") is None

    def test_very_low_price_returns_none(self):
        # Prices under $100 are probably not vehicle prices
        assert parse_price("$50") is None

    def test_price_without_dollar_sign_returns_none(self):
        assert parse_price("5000") is None

    def test_large_price(self):
        assert parse_price("$125,000") == 125000.0


class TestParseMileage:
    # ── Happy path ─────────────────────────────────────────────────────────
    def test_simple_km(self):
        assert parse_mileage("185,000 km") == 185000

    def test_km_uppercase(self):
        assert parse_mileage("92000 KM") == 92000

    def test_no_unit(self):
        assert parse_mileage("75000") == 75000

    def test_with_commas(self):
        assert parse_mileage("210,500") == 210500

    # ── Edge cases ─────────────────────────────────────────────────────────
    def test_none_returns_none(self):
        assert parse_mileage(None) is None

    def test_empty_returns_none(self):
        assert parse_mileage("") is None

    def test_no_numbers_returns_none(self):
        assert parse_mileage("unknown km") is None

    def test_spaces_stripped(self):
        assert parse_mileage("  120 000  km  ") == 120000


class TestExtractYear:
    # ── Happy path ─────────────────────────────────────────────────────────
    def test_modern_year(self):
        assert extract_year("2021 Toyota Camry") == 2021

    def test_year_in_middle(self):
        assert extract_year("Toyota Camry 2019 LE") == 2019

    def test_old_car_year(self):
        assert extract_year("1998 Honda Civic") == 1998

    def test_two_thousand_prefix(self):
        assert extract_year("2005 Ford F-150") == 2005

    # ── Edge cases ─────────────────────────────────────────────────────────
    def test_no_year_returns_none(self):
        assert extract_year("Honda Civic LE") is None

    def test_none_input_returns_none(self):
        assert extract_year(None) is None

    def test_year_before_1900_not_matched(self):
        # "1850" shouldn't be matched since it doesn't start with 19 or 20
        assert extract_year("1850 Vintage Car") is None

    def test_first_year_wins(self):
        # Should return the first year found in the string
        result = extract_year("2020 Toyota Camry 2019 model year comparison")
        assert result == 2020

    def test_2000_boundary(self):
        assert extract_year("2000 Honda Accord") == 2000

    def test_1999_boundary(self):
        assert extract_year("1999 Ford Mustang") == 1999
