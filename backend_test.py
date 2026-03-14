#!/usr/bin/env python3
"""
Backend API Testing for AutoFlip Intelligence
Tests all API endpoints systematically using the public URL
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any

class AutoFlipAPITester:
    def __init__(self, base_url="https://flipbot-monitor.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Dict[Any, Any] = None, params: Dict[str, Any] = None) -> tuple:
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            success = response.status_code == expected_status
            result = {
                'test': name,
                'method': method,
                'endpoint': endpoint,
                'expected_status': expected_status,
                'actual_status': response.status_code,
                'success': success,
                'response_size': len(response.text) if response.text else 0,
                'response_json': None,
                'error': None
            }
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    if response.text:
                        result['response_json'] = response.json()
                        if isinstance(result['response_json'], list):
                            print(f"   Response: List with {len(result['response_json'])} items")
                        elif isinstance(result['response_json'], dict):
                            print(f"   Response: Dict with {len(result['response_json'])} fields")
                        else:
                            print(f"   Response: {type(result['response_json']).__name__}")
                except:
                    pass
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                if response.text:
                    print(f"   Error Response: {response.text[:200]}")
                result['error'] = response.text[:200]
                
            self.test_results.append(result)
            return success, result['response_json'] if result['response_json'] else {}
            
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            result = {
                'test': name,
                'method': method,
                'endpoint': endpoint,
                'expected_status': expected_status,
                'actual_status': 0,
                'success': False,
                'response_size': 0,
                'response_json': None,
                'error': str(e)
            }
            self.test_results.append(result)
            return False, {}

    def test_api_root(self):
        """Test API root endpoint"""
        return self.run_test("API Root", "GET", "/", 200)

    def test_get_listings(self):
        """Test GET /listings with various parameters"""
        # Basic listings fetch
        success, response = self.run_test("Get All Listings", "GET", "/listings", 200)
        
        # Test with filters
        self.run_test("Get Listings - Filter by Source", "GET", "/listings", 200, 
                     params={"source": "cathcart_rebuilders"})
        self.run_test("Get Listings - Filter by Price", "GET", "/listings", 200,
                     params={"min_price": 5000, "max_price": 15000})
        self.run_test("Get Listings - Filter by Score", "GET", "/listings", 200,
                     params={"min_score": 50})
        self.run_test("Get Listings - Sort by Price", "GET", "/listings", 200,
                     params={"sort_by": "price", "sort_order": "asc"})
        
        return success, response

    def test_get_single_listing(self, listing_id=None):
        """Test GET /listings/{id}"""
        if not listing_id:
            # Get a listing ID first
            success, listings = self.test_get_listings()
            if success and listings and len(listings) > 0:
                listing_id = listings[0].get('id')
        
        if listing_id:
            return self.run_test("Get Single Listing", "GET", f"/listings/{listing_id}", 200)
        else:
            print("⚠️  Skipping single listing test - no listings found")
            return False, {}

    def test_stats(self):
        """Test GET /stats"""
        return self.run_test("Get Dashboard Stats", "GET", "/stats", 200)

    def test_watchlist_operations(self):
        """Test watchlist CRUD operations"""
        # Get watchlist
        success, watchlist = self.run_test("Get Watchlist", "GET", "/watchlist", 200)
        
        # Try to add to watchlist (need a listing ID first)
        success, listings = self.test_get_listings()
        if success and listings and len(listings) > 0:
            listing_id = listings[0].get('id')
            
            # Add to watchlist
            add_success, add_response = self.run_test("Add to Watchlist", "POST", "/watchlist", 200,
                                                    data={"listing_id": listing_id, "notes": "Test watchlist entry"})
            
            if add_success:
                watchlist_id = add_response.get('id')
                if watchlist_id:
                    # Update watchlist entry
                    self.run_test("Update Watchlist", "PUT", f"/watchlist/{watchlist_id}", 200,
                                data={"notes": "Updated test notes"})
                    
                    # Remove from watchlist
                    self.run_test("Remove from Watchlist", "DELETE", f"/watchlist/{watchlist_id}", 200)
        
        return success, watchlist

    def test_portfolio_operations(self):
        """Test portfolio CRUD operations"""
        # Get portfolio
        success, portfolio = self.run_test("Get Portfolio", "GET", "/portfolio", 200)
        
        # Create portfolio entry
        create_success, create_response = self.run_test("Create Portfolio Entry", "POST", "/portfolio", 200, data={
            "vehicle_description": "2020 Test Vehicle",
            "buy_date": "2024-01-15",
            "buy_price": 8500,
            "repair_items": [
                {"description": "Test repair", "cost": 500, "date": "2024-01-20"}
            ],
            "sale_date": "2024-02-15",
            "sale_price": 12000,
            "notes": "Test portfolio entry"
        })
        
        if create_success and create_response:
            portfolio_id = create_response.get('id')
            if portfolio_id:
                # Update portfolio
                self.run_test("Update Portfolio Entry", "PUT", f"/portfolio/{portfolio_id}", 200,
                            data={"notes": "Updated test notes"})
                
                # Delete portfolio entry
                self.run_test("Delete Portfolio Entry", "DELETE", f"/portfolio/{portfolio_id}", 200)
        
        return success, portfolio

    def test_settings_operations(self):
        """Test settings operations"""
        # Get settings
        success, settings = self.run_test("Get Settings", "GET", "/settings", 200)
        
        # Update settings
        update_success, update_response = self.run_test("Update Settings", "PUT", "/settings", 200, data={
            "diy_mode": True,
            "shop_rate": 120.0,
            "available_capital": 60000.0,
            "alert_filters": {
                "max_price": 25000,
                "min_deal_score": 45
            }
        })
        
        # Test notification (will likely fail without API keys, but should return structured response)
        self.run_test("Test Notifications", "POST", "/settings/test-notify", 200)
        
        return success, settings

    def test_market_intelligence(self):
        """Test market intelligence endpoint"""
        return self.run_test("Get Market Intelligence", "GET", "/market-intelligence", 200)

    def test_individual_listing_operations(self):
        """Test listing-specific operations like analysis and recalculation"""
        # Get a listing ID first
        success, listings = self.test_get_listings()
        if success and listings and len(listings) > 0:
            listing_id = listings[0].get('id')
            
            # Test get photos
            self.run_test("Get Listing Photos", "GET", f"/listings/{listing_id}/photos", 200)
            
            # Test get analysis
            self.run_test("Get Listing Analysis", "GET", f"/listings/{listing_id}/analysis", 200)
            
            # Test recalculate
            self.run_test("Recalculate Listing", "POST", f"/listings/{listing_id}/recalculate", 200)
            
            # Test analyze (may fail without EMERGENT_LLM_KEY, but should return structured response)
            self.run_test("Analyze Listing Photos", "POST", f"/listings/{listing_id}/analyze", 200)

    def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🚀 Starting AutoFlip Intelligence API Testing")
        print(f"📡 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test API availability
        self.test_api_root()
        
        # Core listing functionality
        self.test_get_listings()
        self.test_get_single_listing()
        self.test_individual_listing_operations()
        
        # Dashboard stats
        self.test_stats()
        
        # Watchlist operations
        self.test_watchlist_operations()
        
        # Portfolio operations  
        self.test_portfolio_operations()
        
        # Settings
        self.test_settings_operations()
        
        # Market intelligence
        self.test_market_intelligence()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Results Summary")
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Show failed tests
        failed_tests = [t for t in self.test_results if not t['success']]
        if failed_tests:
            print(f"\n❌ Failed Tests ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"   • {test['test']}: {test['method']} {test['endpoint']} -> {test['actual_status']} (expected {test['expected_status']})")
                if test['error']:
                    print(f"     Error: {test['error']}")
        else:
            print("\n🎉 All tests passed!")
        
        return self.tests_passed == self.tests_run

def main():
    print("AutoFlip Intelligence - Backend API Tests")
    print("Testing all endpoints systematically...")
    
    tester = AutoFlipAPITester()
    success = tester.run_comprehensive_test()
    
    # Save detailed results
    results_file = f"/app/test_reports/backend_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'base_url': tester.base_url,
                'summary': {
                    'total_tests': tester.tests_run,
                    'passed': tester.tests_passed,
                    'failed': tester.tests_run - tester.tests_passed,
                    'success_rate': (tester.tests_passed/tester.tests_run*100) if tester.tests_run > 0 else 0
                },
                'detailed_results': tester.test_results
            }, f, indent=2)
        print(f"\n📄 Detailed results saved to: {results_file}")
    except Exception as e:
        print(f"⚠️  Could not save results: {e}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())