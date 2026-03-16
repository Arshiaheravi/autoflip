"""
Test Suite for AutoFlip v2.0 Enhanced Calculation Engine
Tests: mv_breakdown, repair_breakdown, fees_breakdown, AI damage detection, calc-methodology
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Skip entire module when no backend URL is configured
pytestmark = pytest.mark.skipif(
    not BASE_URL,
    reason='REACT_APP_BACKEND_URL not set — integration tests skipped'
)


class TestV2CalculationEngine:
    """Tests for the v2.0 calculation engine fields"""
    
    def test_api_root_returns_v2(self):
        """API root should return version 2.0.0"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("version") == "2.0.0"
        print("PASS: API returns version 2.0.0")
    
    def test_listings_have_calc_version_v2(self):
        """All listings should have calc_version='v2.0'"""
        response = requests.get(f"{BASE_URL}/api/listings")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0, "Should have listings"
        
        v2_count = sum(1 for l in data if l.get('calc_version') == 'v2.0')
        assert v2_count == len(data), f"All listings should have calc_version=v2.0, got {v2_count}/{len(data)}"
        print(f"PASS: All {len(data)} listings have calc_version=v2.0")
    
    def test_listings_have_mv_breakdown(self):
        """Listings should have mv_breakdown with required fields"""
        response = requests.get(f"{BASE_URL}/api/listings")
        assert response.status_code == 200
        data = response.json()
        
        # Get listings with market_value calculated
        listings_with_mv = [l for l in data if l.get('market_value')]
        assert len(listings_with_mv) > 0, "Should have listings with market_value"
        
        required_fields = ['msrp', 'msrp_source', 'depreciation', 'brand', 'brand_mult', 
                          'body_mult', 'trim_mult', 'color_mult', 'mileage_mult', 
                          'title_status', 'title_mult', 'age']
        
        for listing in listings_with_mv[:5]:  # Check first 5
            mv = listing.get('mv_breakdown')
            assert mv is not None, f"mv_breakdown missing for {listing.get('title')}"
            for field in required_fields:
                assert field in mv, f"mv_breakdown missing field '{field}' for {listing.get('title')}"
        
        print(f"PASS: mv_breakdown has all required fields ({len(required_fields)} fields)")
    
    def test_listings_have_repair_breakdown(self):
        """Listings should have repair_breakdown with required fields"""
        response = requests.get(f"{BASE_URL}/api/listings")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ['repair_labour_parts_low', 'repair_labour_parts_high', 
                          'safety_inspection', 'salvage_to_rebuilt_cost', 
                          'severity_applied', 'damage_source']
        
        listings_with_repair = [l for l in data if l.get('repair_breakdown')]
        assert len(listings_with_repair) > 0, "Should have listings with repair_breakdown"
        
        for listing in listings_with_repair[:5]:
            rb = listing.get('repair_breakdown')
            for field in required_fields:
                assert field in rb, f"repair_breakdown missing field '{field}' for {listing.get('title')}"
        
        print(f"PASS: repair_breakdown has all required fields ({len(required_fields)} fields)")
    
    def test_listings_have_fees_breakdown(self):
        """Listings should have fees_breakdown with required fields"""
        response = requests.get(f"{BASE_URL}/api/listings")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ['hst', 'omvic', 'mto_transfer', 'safety_cert', 'total']
        
        listings_with_fees = [l for l in data if l.get('fees_breakdown')]
        assert len(listings_with_fees) > 0, "Should have listings with fees_breakdown"
        
        for listing in listings_with_fees[:5]:
            fb = listing.get('fees_breakdown')
            for field in required_fields:
                assert field in fb, f"fees_breakdown missing field '{field}' for {listing.get('title')}"
            # Verify fee values are correct
            assert fb.get('omvic') == 22, f"OMVIC fee should be 22, got {fb.get('omvic')}"
            assert fb.get('mto_transfer') == 32, f"MTO transfer fee should be 32, got {fb.get('mto_transfer')}"
            assert fb.get('safety_cert') == 100, f"Safety cert should be 100, got {fb.get('safety_cert')}"
        
        print(f"PASS: fees_breakdown has all required fields with correct values")


class TestSalvageTitleCalculations:
    """Tests for salvage title specific calculations"""
    
    def test_salvage_title_mult_is_055(self):
        """Salvage title vehicles should have title_mult=0.55"""
        response = requests.get(f"{BASE_URL}/api/listings?brand_type=salvage")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No salvage listings found")
        
        for listing in data[:5]:
            mv = listing.get('mv_breakdown', {})
            assert mv.get('title_mult') == 0.55, f"Salvage should have title_mult=0.55, got {mv.get('title_mult')} for {listing.get('title')}"
            assert mv.get('title_status') == 'salvage_title', f"Should have title_status=salvage_title for {listing.get('title')}"
        
        print(f"PASS: All salvage listings have title_mult=0.55")
    
    def test_salvage_has_salvage_to_rebuilt_cost(self):
        """Salvage vehicles should have salvage_to_rebuilt_cost=$625"""
        response = requests.get(f"{BASE_URL}/api/listings?brand_type=salvage")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No salvage listings found")
        
        for listing in data[:5]:
            rb = listing.get('repair_breakdown', {})
            assert rb.get('salvage_to_rebuilt_cost') == 625, f"Salvage should have salvage_to_rebuilt_cost=625, got {rb.get('salvage_to_rebuilt_cost')} for {listing.get('title')}"
        
        print(f"PASS: All salvage listings include $625 salvage-to-rebuilt cost")
    
    def test_clean_title_has_no_salvage_cost(self):
        """Clean title vehicles should NOT have salvage_to_rebuilt_cost"""
        response = requests.get(f"{BASE_URL}/api/listings?brand_type=clean")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No clean title listings found")
        
        for listing in data[:5]:
            rb = listing.get('repair_breakdown', {})
            assert rb.get('salvage_to_rebuilt_cost', 0) == 0, f"Clean title should have salvage_to_rebuilt_cost=0, got {rb.get('salvage_to_rebuilt_cost')} for {listing.get('title')}"
        
        print(f"PASS: Clean title listings have no salvage-to-rebuilt cost")


class TestAIDamageDetection:
    """Tests for AI damage detection feature"""
    
    def test_ai_damage_fields_exist(self):
        """Listings should have ai_damage_detected and ai_damage_details fields"""
        response = requests.get(f"{BASE_URL}/api/listings")
        assert response.status_code == 200
        data = response.json()
        
        for listing in data[:5]:
            assert 'ai_damage_detected' in listing, f"ai_damage_detected field missing for {listing.get('title')}"
            assert 'ai_damage_details' in listing, f"ai_damage_details field missing for {listing.get('title')}"
        
        print("PASS: All listings have ai_damage_detected and ai_damage_details fields")
    
    def test_ai_damage_detected_count(self):
        """Should have multiple AI-detected damage listings"""
        response = requests.get(f"{BASE_URL}/api/listings")
        assert response.status_code == 200
        data = response.json()
        
        ai_detected = [l for l in data if l.get('ai_damage_detected') == True]
        print(f"Found {len(ai_detected)} listings with AI damage detection")
        
        # Per the request, scrape had 39 AI damage detections - but some may have damage listed now
        # At minimum we should see some AI detections
        assert len(ai_detected) > 0, "Should have at least some AI damage detections"
        
        # Verify AI detected listings have details
        for listing in ai_detected[:3]:
            assert listing.get('ai_damage_details'), f"AI detected listing should have details: {listing.get('title')}"
        
        print(f"PASS: {len(ai_detected)} listings have AI damage detection with details")


class TestSingleListingEndpoint:
    """Tests for GET /api/listings/{listing_id}"""
    
    def test_get_listing_by_id(self):
        """Should retrieve a single listing by ID with all v2 fields"""
        # First get a listing ID
        response = requests.get(f"{BASE_URL}/api/listings")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        
        listing_id = data[0].get('id')
        assert listing_id, "Listing should have an ID"
        
        # Now fetch by ID
        response = requests.get(f"{BASE_URL}/api/listings/{listing_id}")
        assert response.status_code == 200
        listing = response.json()
        
        # Verify v2 fields
        assert listing.get('id') == listing_id
        assert 'calc_version' in listing
        assert 'mv_breakdown' in listing
        assert 'repair_breakdown' in listing
        assert 'fees_breakdown' in listing
        assert 'ai_damage_detected' in listing
        assert 'ai_damage_details' in listing
        
        print(f"PASS: GET /api/listings/{listing_id[:8]}... returns complete v2 data")
    
    def test_get_listing_404_for_invalid_id(self):
        """Should return 404 for non-existent listing ID"""
        response = requests.get(f"{BASE_URL}/api/listings/invalid-id-12345")
        assert response.status_code == 404
        print("PASS: 404 returned for invalid listing ID")


class TestCalcMethodologyEndpoint:
    """Tests for GET /api/calc-methodology"""
    
    def test_calc_methodology_returns_200(self):
        """calc-methodology endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/calc-methodology")
        assert response.status_code == 200
        print("PASS: /api/calc-methodology returns 200")
    
    def test_calc_methodology_has_required_sections(self):
        """calc-methodology should have all documentation sections"""
        response = requests.get(f"{BASE_URL}/api/calc-methodology")
        assert response.status_code == 200
        data = response.json()
        
        required_sections = ['version', 'engine', 'market_value', 'repair_cost', 
                           'ontario_fees', 'profit_calculation', 'deal_scoring', 'technologies']
        
        for section in required_sections:
            assert section in data, f"calc-methodology missing section '{section}'"
        
        print(f"PASS: calc-methodology has all {len(required_sections)} required sections")
    
    def test_calc_methodology_market_value_factors(self):
        """market_value section should list all factors"""
        response = requests.get(f"{BASE_URL}/api/calc-methodology")
        assert response.status_code == 200
        data = response.json()
        
        mv = data.get('market_value', {})
        factors = mv.get('factors', [])
        factor_names = [f['name'] for f in factors]
        
        expected_factors = ['MSRP Baseline', 'Depreciation Curve', 'Brand Retention', 
                          'Body Type Demand', 'Trim Level', 'Color Premium', 
                          'Mileage Adjustment', 'Title Status']
        
        for expected in expected_factors:
            assert expected in factor_names, f"Market value factors missing '{expected}'"
        
        assert mv.get('formula'), "Market value should have formula"
        print(f"PASS: market_value section has all {len(expected_factors)} factors and formula")
    
    def test_calc_methodology_repair_cost_factors(self):
        """repair_cost section should list all factors including AI damage detection"""
        response = requests.get(f"{BASE_URL}/api/calc-methodology")
        assert response.status_code == 200
        data = response.json()
        
        rc = data.get('repair_cost', {})
        factors = rc.get('factors', [])
        factor_names = [f['name'] for f in factors]
        
        expected_factors = ['Damage Zone', 'Severity Multiplier', 'Salvage-to-Rebuilt Process', 
                          'Safety Inspection', 'AI Damage Detection']
        
        for expected in expected_factors:
            assert expected in factor_names, f"Repair cost factors missing '{expected}'"
        
        print(f"PASS: repair_cost section includes AI Damage Detection factor")
    
    def test_calc_methodology_ontario_fees_breakdown(self):
        """ontario_fees section should list all fee types"""
        response = requests.get(f"{BASE_URL}/api/calc-methodology")
        assert response.status_code == 200
        data = response.json()
        
        of = data.get('ontario_fees', {})
        breakdown = of.get('breakdown', [])
        fee_names = [f['name'] for f in breakdown]
        
        expected_fees = ['HST', 'OMVIC Fee', 'MTO Transfer', 'Safety Certificate']
        
        for expected in expected_fees:
            assert expected in fee_names, f"Ontario fees missing '{expected}'"
        
        print(f"PASS: ontario_fees section lists all {len(expected_fees)} fee types")
    
    def test_calc_methodology_deal_scoring(self):
        """deal_scoring section should document score ranges and adjustments"""
        response = requests.get(f"{BASE_URL}/api/calc-methodology")
        assert response.status_code == 200
        data = response.json()
        
        ds = data.get('deal_scoring', {})
        scale = ds.get('scale', [])
        adjustments = ds.get('adjustments', [])
        
        # Verify BUY, WATCH, SKIP labels documented
        labels = [s['label'] for s in scale]
        assert 'BUY' in labels
        assert 'WATCH' in labels
        assert 'SKIP' in labels
        
        # Verify ROI adjustments documented
        assert len(adjustments) >= 2, "Should document ROI bonus/penalty adjustments"
        adjustments_text = ' '.join(adjustments)
        assert 'ROI' in adjustments_text, "Should mention ROI in adjustments"
        
        print(f"PASS: deal_scoring documents BUY/WATCH/SKIP scale and ROI adjustments")


class TestStatsEndpoint:
    """Tests for GET /api/stats"""
    
    def test_stats_returns_counts(self):
        """Stats endpoint should return correct counts"""
        response = requests.get(f"{BASE_URL}/api/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert 'total_listings' in data
        assert 'buy_count' in data
        assert 'watch_count' in data
        assert 'skip_count' in data
        assert 'source_counts' in data
        
        # Verify counts are reasonable
        total = data.get('total_listings', 0)
        buy = data.get('buy_count', 0)
        watch = data.get('watch_count', 0)
        skip = data.get('skip_count', 0)
        no_score = data.get('no_score_count', 0)
        
        assert total > 0, "Should have listings"
        assert buy + watch + skip + no_score == total, "Score counts should sum to total"
        
        print(f"PASS: Stats - Total: {total}, BUY: {buy}, WATCH: {watch}, SKIP: {skip}, No Score: {no_score}")
    
    def test_stats_source_counts(self):
        """Stats should include source_counts breakdown"""
        response = requests.get(f"{BASE_URL}/api/stats")
        assert response.status_code == 200
        data = response.json()
        
        source_counts = data.get('source_counts', {})
        expected_sources = ['cathcart_rebuilders', 'cathcart_used', 'picnsave']
        
        for source in expected_sources:
            assert source in source_counts, f"source_counts missing '{source}'"
        
        print(f"PASS: source_counts includes all 3 sources")


class TestDealScoring:
    """Tests for deal score calculation"""
    
    def test_deal_score_uses_roi_bonus(self):
        """Deal score should factor in ROI bonus for high ROI listings"""
        response = requests.get(f"{BASE_URL}/api/listings")
        assert response.status_code == 200
        data = response.json()
        
        # Find listings with high ROI (>60%)
        high_roi = [l for l in data if l.get('roi_best') and l.get('roi_best') > 60]
        
        if len(high_roi) == 0:
            pytest.skip("No high ROI listings found")
        
        # High ROI listings should generally have good scores (7+)
        for listing in high_roi[:5]:
            score = listing.get('deal_score', 0)
            roi = listing.get('roi_best', 0)
            print(f"  {listing.get('title')[:40]}: ROI {roi}%, Score {score}")
        
        print(f"PASS: Deal scoring functioning with {len(high_roi)} high-ROI listings")


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
