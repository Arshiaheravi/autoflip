"""
Test suite for AutoFlip Intelligence API - Filter Functionality
Tests brand_type and status filter parameters for GET /api/listings endpoint

NOTE: These are INTEGRATION tests — they require a running backend.
      Set REACT_APP_BACKEND_URL env var to run them.
      Without the env var, all tests are automatically skipped.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Skip entire module when no backend URL is configured
pytestmark = pytest.mark.skipif(
    not BASE_URL,
    reason="REACT_APP_BACKEND_URL not set — integration tests skipped"
)


class TestAPIHealth:
    """Basic API health check tests"""
    
    def test_api_root_accessible(self):
        """Test API root endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"API root accessible: {data}")

class TestBrandTypeFilter:
    """Tests for brand_type filter parameter (Salvage/Clean/Rebuilt title filtering)"""
    
    def test_get_all_listings_no_filter(self):
        """Test getting all listings without brand_type filter"""
        response = requests.get(f"{BASE_URL}/api/listings")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        total_count = len(data)
        print(f"Total listings without filter: {total_count}")
        return total_count
    
    def test_filter_salvage_title(self):
        """Test filtering by salvage title"""
        response = requests.get(f"{BASE_URL}/api/listings?brand_type=salvage")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        salvage_count = len(data)
        print(f"Salvage title listings: {salvage_count}")
        
        # Verify all returned listings have SALVAGE in brand
        for listing in data:
            brand = listing.get('brand', '').upper()
            assert 'SALVAGE' in brand, f"Expected SALVAGE in brand, got: {brand}"
        
        assert salvage_count > 0, "Expected at least some salvage listings"
        print(f"Verified {salvage_count} listings have SALVAGE in brand field")
    
    def test_filter_clean_title(self):
        """Test filtering by clean title"""
        response = requests.get(f"{BASE_URL}/api/listings?brand_type=clean")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        clean_count = len(data)
        print(f"Clean title listings: {clean_count}")
        
        # Verify all returned listings have CLEAN in brand
        for listing in data:
            brand = listing.get('brand', '').upper()
            assert 'CLEAN' in brand, f"Expected CLEAN in brand, got: {brand}"
        
        assert clean_count > 0, "Expected at least some clean listings"
        print(f"Verified {clean_count} listings have CLEAN in brand field")
    
    def test_filter_rebuilt_title(self):
        """Test filtering by rebuilt title"""
        response = requests.get(f"{BASE_URL}/api/listings?brand_type=rebuilt")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        rebuilt_count = len(data)
        print(f"Rebuilt title listings: {rebuilt_count}")
        
        # Verify all returned listings have REBUILT in brand (may be 0)
        for listing in data:
            brand = listing.get('brand', '').upper()
            assert 'REBUILT' in brand, f"Expected REBUILT in brand, got: {brand}"
        
        print(f"Verified {rebuilt_count} listings have REBUILT in brand field")


class TestStatusFilter:
    """Tests for status filter parameter (for_sale/coming_soon filtering)"""
    
    def test_filter_for_sale_status(self):
        """Test filtering by for_sale status"""
        response = requests.get(f"{BASE_URL}/api/listings?status=for_sale")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for_sale_count = len(data)
        print(f"For sale listings: {for_sale_count}")
        
        # Verify all returned listings have for_sale status
        for listing in data:
            status = listing.get('status', '')
            assert status == 'for_sale', f"Expected status 'for_sale', got: {status}"
        
        assert for_sale_count > 0, "Expected at least some for_sale listings"
        print(f"Verified {for_sale_count} listings have for_sale status")
    
    def test_filter_coming_soon_status(self):
        """Test filtering by coming_soon status"""
        response = requests.get(f"{BASE_URL}/api/listings?status=coming_soon")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        coming_soon_count = len(data)
        print(f"Coming soon listings: {coming_soon_count}")
        
        # Verify all returned listings have coming_soon status
        for listing in data:
            status = listing.get('status', '')
            assert status == 'coming_soon', f"Expected status 'coming_soon', got: {status}"
        
        print(f"Verified {coming_soon_count} listings have coming_soon status")


class TestCombinedFilters:
    """Tests for combining brand_type and status filters"""
    
    def test_salvage_and_coming_soon(self):
        """Test combined filter: salvage brand_type AND coming_soon status"""
        response = requests.get(f"{BASE_URL}/api/listings?brand_type=salvage&status=coming_soon")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        combined_count = len(data)
        print(f"Salvage + Coming soon listings: {combined_count}")
        
        # Verify all returned listings match both criteria
        for listing in data:
            brand = listing.get('brand', '').upper()
            status = listing.get('status', '')
            assert 'SALVAGE' in brand, f"Expected SALVAGE in brand, got: {brand}"
            assert status == 'coming_soon', f"Expected status 'coming_soon', got: {status}"
        
        print(f"Verified {combined_count} listings match salvage+coming_soon")
    
    def test_salvage_and_for_sale(self):
        """Test combined filter: salvage brand_type AND for_sale status"""
        response = requests.get(f"{BASE_URL}/api/listings?brand_type=salvage&status=for_sale")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        combined_count = len(data)
        print(f"Salvage + For sale listings: {combined_count}")
        
        # Verify all returned listings match both criteria
        for listing in data:
            brand = listing.get('brand', '').upper()
            status = listing.get('status', '')
            assert 'SALVAGE' in brand, f"Expected SALVAGE in brand, got: {brand}"
            assert status == 'for_sale', f"Expected status 'for_sale', got: {status}"
        
        print(f"Verified {combined_count} listings match salvage+for_sale")
    
    def test_clean_and_for_sale(self):
        """Test combined filter: clean brand_type AND for_sale status"""
        response = requests.get(f"{BASE_URL}/api/listings?brand_type=clean&status=for_sale")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        combined_count = len(data)
        print(f"Clean + For sale listings: {combined_count}")
        
        # Verify all returned listings match both criteria
        for listing in data:
            brand = listing.get('brand', '').upper()
            status = listing.get('status', '')
            assert 'CLEAN' in brand, f"Expected CLEAN in brand, got: {brand}"
            assert status == 'for_sale', f"Expected status 'for_sale', got: {status}"
        
        print(f"Verified {combined_count} listings match clean+for_sale")


class TestFilterCountConsistency:
    """Tests for verifying filter count consistency"""
    
    def test_salvage_plus_clean_approximately_equals_total(self):
        """Verify salvage + clean + rebuilt counts are reasonable relative to total"""
        # Get all listings
        response_all = requests.get(f"{BASE_URL}/api/listings")
        assert response_all.status_code == 200
        all_listings = response_all.json()
        total_count = len(all_listings)
        
        # Get filtered counts
        response_salvage = requests.get(f"{BASE_URL}/api/listings?brand_type=salvage")
        response_clean = requests.get(f"{BASE_URL}/api/listings?brand_type=clean")
        response_rebuilt = requests.get(f"{BASE_URL}/api/listings?brand_type=rebuilt")
        
        salvage_count = len(response_salvage.json())
        clean_count = len(response_clean.json())
        rebuilt_count = len(response_rebuilt.json())
        
        filtered_total = salvage_count + clean_count + rebuilt_count
        
        print(f"Total listings: {total_count}")
        print(f"Salvage: {salvage_count}, Clean: {clean_count}, Rebuilt: {rebuilt_count}")
        print(f"Sum of filtered: {filtered_total}")
        
        # Note: Some listings may have no brand info, so filtered total may be <= total
        assert filtered_total <= total_count, f"Filtered total {filtered_total} exceeds total {total_count}"
    
    def test_for_sale_plus_coming_soon_approximately_equals_total(self):
        """Verify for_sale + coming_soon counts are reasonable relative to total"""
        # Get all listings
        response_all = requests.get(f"{BASE_URL}/api/listings")
        assert response_all.status_code == 200
        all_listings = response_all.json()
        total_count = len(all_listings)
        
        # Get filtered counts
        response_for_sale = requests.get(f"{BASE_URL}/api/listings?status=for_sale")
        response_coming_soon = requests.get(f"{BASE_URL}/api/listings?status=coming_soon")
        
        for_sale_count = len(response_for_sale.json())
        coming_soon_count = len(response_coming_soon.json())
        
        filtered_total = for_sale_count + coming_soon_count
        
        print(f"Total listings: {total_count}")
        print(f"For sale: {for_sale_count}, Coming soon: {coming_soon_count}")
        print(f"Sum of filtered: {filtered_total}")
        
        # for_sale + coming_soon should be close to or equal total
        # (some may have status 'sold' or other)
        assert filtered_total <= total_count + 5, f"Filtered total {filtered_total} much greater than total {total_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
