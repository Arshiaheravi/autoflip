"""
Unit tests for backend/app/services/calculations.py

Tests every function in the core business logic — no database, no network.
If these break, the deal scoring / profit estimates are wrong.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from app.services.calculations import (
    _find_msrp, _get_brand, _get_body_type_mult, _get_trim_mult,
    _get_color_mult, _get_depreciation, _get_mileage_adjustment,
    estimate_market_value, get_repair_range, calculate_ontario_fees,
    calc_deal_score, SAFETY_INSPECTION_COST, OMVIC_FEE, MTO_TRANSFER_FEE,
    REBUILT_TITLE_PROCESS,
)


# ─── _find_msrp ──────────────────────────────────────────────────────────────

class TestFindMsrp:
    def test_known_model_returns_msrp(self):
        assert _find_msrp("2019 toyota camry") == 35000

    def test_known_model_civic(self):
        assert _find_msrp("2020 honda civic lx") == 30000

    def test_known_model_rav4(self):
        assert _find_msrp("2021 toyota rav4") == 38000

    def test_unknown_model_returns_none(self):
        assert _find_msrp("2018 pontiac aztek") is None

    def test_longest_match_wins(self):
        # "ram 1500" should beat "ram" alone
        result = _find_msrp("2022 dodge ram 1500 big horn")
        assert result == 52000

    def test_case_insensitive(self):
        # _find_msrp expects a pre-lowercased string (caller's responsibility)
        assert _find_msrp("2020 toyota camry") == 35000

    def test_f150_variant(self):
        assert _find_msrp("2021 ford f-150 xlt") == 52000


# ─── _get_brand ──────────────────────────────────────────────────────────────

class TestGetBrand:
    def test_toyota_high_retention(self):
        brand, mult = _get_brand("2020 toyota rav4")
        assert brand == "toyota"
        assert mult == 1.18

    def test_unknown_brand_default(self):
        brand, mult = _get_brand("2018 generic brand car")
        assert brand == "unknown"
        assert mult == 0.90

    def test_honda_retention(self):
        _, mult = _get_brand("2021 honda civic")
        assert mult == 1.14

    def test_chrysler_low_retention(self):
        _, mult = _get_brand("2015 chrysler 200")
        assert mult == 0.82


# ─── _get_body_type_mult ─────────────────────────────────────────────────────

class TestGetBodyTypeMult:
    def test_truck_high_mult(self):
        assert _get_body_type_mult("2021 ford f150 crew cab") == 1.30

    def test_wrangler_mult(self):
        assert _get_body_type_mult("2020 jeep wrangler") == 1.20

    def test_rav4_suv_mult(self):
        assert _get_body_type_mult("2022 toyota rav4") == 1.15

    def test_civic_sedan_low_mult(self):
        assert _get_body_type_mult("2019 honda civic sedan") == 0.95

    def test_unknown_body_default(self):
        assert _get_body_type_mult("2018 generic vehicle") == 1.0


# ─── _get_trim_mult ──────────────────────────────────────────────────────────

class TestGetTrimMult:
    def test_limited_trim_high(self):
        assert _get_trim_mult("2022 toyota camry limited") == 1.25

    def test_sport_trim(self):
        assert _get_trim_mult("2021 honda civic sport") == 1.15

    def test_base_trim(self):
        assert _get_trim_mult("2020 toyota camry le") == 1.05

    def test_no_trim_default(self):
        assert _get_trim_mult("2019 honda civic") == 1.0

    def test_awd_trim(self):
        assert _get_trim_mult("2021 toyota rav4 awd") == 1.10


# ─── _get_color_mult ─────────────────────────────────────────────────────────

class TestGetColorMult:
    def test_white_premium(self):
        assert _get_color_mult("white") == 1.04

    def test_black_premium(self):
        assert _get_color_mult("black") == 1.03

    def test_purple_discount(self):
        assert _get_color_mult("purple") == 0.90

    def test_empty_color_neutral(self):
        assert _get_color_mult("") == 1.0

    def test_none_color_neutral(self):
        assert _get_color_mult(None) == 1.0

    def test_unknown_color_slight_discount(self):
        assert _get_color_mult("teal") == 0.97

    def test_case_insensitive(self):
        assert _get_color_mult("WHITE") == 1.04


# ─── _get_depreciation ───────────────────────────────────────────────────────

class TestGetDepreciation:
    def test_new_car_no_depreciation(self):
        assert _get_depreciation(0) == 1.0

    def test_one_year_old(self):
        assert _get_depreciation(1) == 0.82

    def test_five_years(self):
        assert _get_depreciation(5) == 0.48

    def test_ten_years(self):
        assert _get_depreciation(10) == 0.25

    def test_twenty_years(self):
        assert _get_depreciation(20) == 0.07

    def test_very_old_car_floor(self):
        result = _get_depreciation(30)
        assert result >= 0.04
        assert result < 0.07

    def test_negative_age_treated_as_zero(self):
        assert _get_depreciation(-1) == 1.0


# ─── _get_mileage_adjustment ─────────────────────────────────────────────────

class TestGetMileageAdjustment:
    def test_zero_mileage_neutral(self):
        assert _get_mileage_adjustment(0, 5) == 1.0

    def test_none_mileage_neutral(self):
        assert _get_mileage_adjustment(None, 5) == 1.0

    def test_low_mileage_bonus(self):
        # 50k km on 10yr old car (expected ~180k) → ratio ~0.28 → +8%
        result = _get_mileage_adjustment(50000, 10)
        assert result == 1.08

    def test_average_mileage_neutral(self):
        # 90k km on 5yr old car (expected 90k) → ratio ~1.0 → neutral
        result = _get_mileage_adjustment(90000, 5)
        assert result == 1.00

    def test_high_mileage_penalty(self):
        # 350k km on 5yr old car → ratio > 2.0 → big penalty
        result = _get_mileage_adjustment(350000, 5)
        assert result <= 0.82

    def test_very_high_mileage_floor(self):
        result = _get_mileage_adjustment(1000000, 5)
        assert result >= 0.70


# ─── estimate_market_value ───────────────────────────────────────────────────

class TestEstimateMarketValue:
    def test_returns_required_keys(self):
        result = estimate_market_value("2020 Toyota Camry", 2020)
        required = ["market_value", "formula_value", "msrp", "brand", "age",
                    "depreciation", "title_status", "blend_method"]
        for key in required:
            assert key in result, f"Missing key: {key}"

    def test_known_car_reasonable_value(self):
        result = estimate_market_value("2020 Toyota Camry", 2020, mileage=80000)
        assert 8000 < result["market_value"] < 40000

    def test_salvage_title_reduces_value(self):
        clean = estimate_market_value("2020 Toyota Camry", 2020, brand_status="CLEAN TITLE")
        salvage = estimate_market_value("2020 Toyota Camry", 2020, brand_status="SALVAGE")
        assert salvage["market_value"] < clean["market_value"]
        assert salvage["title_status"] == "salvage_title"
        assert salvage["title_mult"] == 0.55

    def test_rebuilt_title_between_clean_and_salvage(self):
        clean = estimate_market_value("2020 Toyota Camry", 2020)
        rebuilt = estimate_market_value("2020 Toyota Camry", 2020, brand_status="REBUILT")
        salvage = estimate_market_value("2020 Toyota Camry", 2020, brand_status="SALVAGE")
        assert salvage["market_value"] < rebuilt["market_value"] < clean["market_value"]

    def test_minimum_value_floor(self):
        # Very old, unknown car should still return at least $800
        result = estimate_market_value("1998 Generic Oldsmobile", 1998)
        assert result["market_value"] >= 800

    def test_white_vs_purple_colour(self):
        white = estimate_market_value("2020 Toyota Camry", 2020, colour="white")
        purple = estimate_market_value("2020 Toyota Camry", 2020, colour="purple")
        assert white["market_value"] > purple["market_value"]

    def test_msrp_source_model_match(self):
        result = estimate_market_value("2020 Toyota Camry", 2020)
        assert result["msrp_source"] == "model_match"

    def test_msrp_source_estimated_for_unknown(self):
        result = estimate_market_value("2020 Generic Brand Car", 2020)
        assert result["msrp_source"] == "estimated"


# ─── get_repair_range ────────────────────────────────────────────────────────

class TestGetRepairRange:
    def test_front_damage_returns_range(self):
        low, high, breakdown = get_repair_range("FRONT END")
        assert low > 0
        assert high > low
        assert "repair_labour_parts_low" in breakdown

    def test_no_damage_uses_default(self):
        low, high, _ = get_repair_range("")
        assert low > 0
        assert "damage_source" in get_repair_range("")[2]

    def test_none_damage_uses_default(self):
        low, high, breakdown = get_repair_range(None)
        assert breakdown["damage_source"] == "none"

    def test_rollover_is_expensive(self):
        front_low, front_high, _ = get_repair_range("FRONT")
        roll_low, roll_high, _ = get_repair_range("ROLLOVER")
        assert roll_low > front_low
        assert roll_high > front_high

    def test_severe_multiplies_cost(self):
        mod_low, mod_high, _ = get_repair_range("FRONT", severity="moderate")
        sev_low, sev_high, _ = get_repair_range("FRONT", severity="severe")
        assert sev_low > mod_low
        assert sev_high > mod_high

    def test_minor_reduces_cost(self):
        mod_low, mod_high, _ = get_repair_range("FRONT", severity="moderate")
        min_low, min_high, _ = get_repair_range("FRONT", severity="minor")
        assert min_low < mod_low

    def test_salvage_adds_rebuilt_title_cost(self):
        no_salvage_low, _, _ = get_repair_range("FRONT", is_salvage=False)
        salvage_low, _, _ = get_repair_range("FRONT", is_salvage=True)
        assert salvage_low == no_salvage_low + REBUILT_TITLE_PROCESS

    def test_safety_always_included(self):
        _, _, breakdown = get_repair_range("FRONT")
        assert breakdown["safety_inspection"] == SAFETY_INSPECTION_COST

    def test_fire_damage(self):
        low, high, _ = get_repair_range("FIRE DAMAGE")
        assert low >= 4000

    def test_flood_damage(self):
        low, high, _ = get_repair_range("FLOOD")
        assert low >= 4000


# ─── calculate_ontario_fees ──────────────────────────────────────────────────

class TestCalculateOntarioFees:
    def test_returns_required_keys(self):
        fees = calculate_ontario_fees(10000)
        assert "hst" in fees
        assert "omvic" in fees
        assert "mto_transfer" in fees
        assert "safety_cert" in fees
        assert "total" in fees

    def test_hst_is_13_percent(self):
        fees = calculate_ontario_fees(10000)
        assert fees["hst"] == pytest.approx(1300.0, abs=0.01)

    def test_fixed_fees_correct(self):
        fees = calculate_ontario_fees(10000)
        assert fees["omvic"] == OMVIC_FEE       # $22
        assert fees["mto_transfer"] == MTO_TRANSFER_FEE  # $32
        assert fees["safety_cert"] == SAFETY_INSPECTION_COST  # $100

    def test_total_is_sum(self):
        fees = calculate_ontario_fees(10000)
        expected = fees["hst"] + OMVIC_FEE + MTO_TRANSFER_FEE + SAFETY_INSPECTION_COST
        assert fees["total"] == pytest.approx(expected, abs=1.0)

    def test_zero_purchase_price(self):
        fees = calculate_ontario_fees(0)
        assert fees["hst"] == 0.0

    def test_higher_price_more_hst(self):
        fees_5k = calculate_ontario_fees(5000)
        fees_20k = calculate_ontario_fees(20000)
        assert fees_20k["hst"] > fees_5k["hst"]


# ─── calc_deal_score ─────────────────────────────────────────────────────────

class TestCalcDealScore:
    def test_high_profit_buy_signal(self):
        score, label = calc_deal_score(6000, 4000)
        assert score >= 8
        assert label == "BUY"

    def test_moderate_profit_watch(self):
        score, label = calc_deal_score(1500, 500)
        assert 5 <= score <= 7
        assert label == "WATCH"

    def test_negative_profit_skip(self):
        score, label = calc_deal_score(-500, -2000)
        assert score <= 4
        assert label == "SKIP"

    def test_score_range_1_to_10(self):
        for profit in [-5000, -1000, 0, 500, 1500, 3000, 5000, 10000]:
            score, _ = calc_deal_score(profit, profit - 500)
            assert 1 <= score <= 10

    def test_high_roi_bonus(self):
        score_no_roi, _ = calc_deal_score(3000, 2000, roi_best=0)
        score_high_roi, _ = calc_deal_score(3000, 2000, roi_best=80)
        assert score_high_roi >= score_no_roi

    def test_negative_roi_penalty(self):
        score_neutral, _ = calc_deal_score(3000, 2000, roi_best=0)
        score_neg, _ = calc_deal_score(3000, 2000, roi_best=-20)
        assert score_neg <= score_neutral

    def test_bad_worst_case_caps_score(self):
        # Even with good best case, terrible worst case drops the score
        # avg=(5000+-3000)/2=1000 → score=5, then worst<-2000 → score=max(3,5-1)=4
        score, _ = calc_deal_score(5000, -3000)
        assert score <= 4

    def test_boundary_5000_is_10(self):
        score, label = calc_deal_score(5500, 5000)
        assert score == 10
        assert label == "BUY"

    def test_boundary_negative_large_loss(self):
        score, label = calc_deal_score(-2000, -3000)
        assert score == 1
        assert label == "SKIP"

    def test_exceptional_roi_double_bonus(self):
        # roi=80 → +1, roi=110 → +2: double capital return should score higher
        score_high, _ = calc_deal_score(3000, 2000, roi_best=80)
        score_exceptional, _ = calc_deal_score(3000, 2000, roi_best=110)
        assert score_exceptional > score_high

    def test_terrible_roi_double_penalty(self):
        # roi=-20 → -1, roi=-50 → -2: catastrophic ROI should tank the score further
        score_bad, _ = calc_deal_score(3000, 2000, roi_best=-20)
        score_terrible, _ = calc_deal_score(3000, 2000, roi_best=-50)
        assert score_terrible < score_bad
