#!/usr/bin/env python3
"""
Backend API Testing for AutoFlip Intelligence Car Dealer Monitoring App
Tests all actual API endpoints systematically using the public URL
"""

import requests
import sys
import json
import time
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
        
        # Test with source filters
        self.run_test("Get Listings - Cathcart Rebuilders", "GET", "/listings", 200, 
                     params={"source": "cathcart_rebuilders"})
        self.run_test("Get Listings - Cathcart Used", "GET", "/listings", 200,
                     params={"source": "cathcart_used"})
        self.run_test("Get Listings - Pic N Save", "GET", "/listings", 200,
                     params={"source": "picnsave"})
        
        # Test with price filters
        self.run_test("Get Listings - Max Price Filter", "GET", "/listings", 200,
                     params={"max_price": 15000})
        
        # Test with profit filters
        self.run_test("Get Listings - Min Profit Filter", "GET", "/listings", 200,
                     params={"min_profit": 2000})
        
        # Test with score filters (scores are 1-10, not 50)
        self.run_test("Get Listings - Min Score 5", "GET", "/listings", 200,
                     params={"min_score": 5})
        self.run_test("Get Listings - Min Score 8", "GET", "/listings", 200,
                     params={"min_score": 8})
        
        # Test search functionality
        self.run_test("Get Listings - Search Toyota", "GET", "/listings", 200,
                     params={"search": "Toyota"})
        self.run_test("Get Listings - Search 2020", "GET", "/listings", 200,
                     params={"search": "2020"})
        
        # Test damage filter
        self.run_test("Get Listings - Front Damage", "GET", "/listings", 200,
                     params={"damage_type": "FRONT"})
        
        # Test sorting
        self.run_test("Get Listings - Sort by Deal Score", "GET", "/listings", 200,
                     params={"sort_by": "deal_score", "sort_order": "desc"})
        self.run_test("Get Listings - Sort by Profit", "GET", "/listings", 200,
                     params={"sort_by": "profit", "sort_order": "desc"})
        self.run_test("Get Listings - Sort by Price Asc", "GET", "/listings", 200,
                     params={"sort_by": "price", "sort_order": "asc"})
        self.run_test("Get Listings - Sort by Mileage", "GET", "/listings", 200,
                     params={"sort_by": "mileage", "sort_order": "asc"})
        
        # Test status filter
        self.run_test("Get Listings - For Sale Status", "GET", "/listings", 200,
                     params={"status": "for_sale"})
        
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
        """Test GET /stats - dashboard statistics"""
        success, response = self.run_test("Get Dashboard Stats", "GET", "/stats", 200)
        
        # Validate required fields in stats response
        if success and response:
            required_fields = ['total_listings', 'buy_count', 'watch_count', 'skip_count', 
                             'top_profit', 'source_counts']
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                print(f"⚠️  Missing required fields in stats: {missing_fields}")
            else:
                print(f"✅ Stats contains all required fields")
                print(f"   Total listings: {response.get('total_listings', 'N/A')}")
                print(f"   BUY deals: {response.get('buy_count', 'N/A')}")
                print(f"   WATCH deals: {response.get('watch_count', 'N/A')}")
                print(f"   SKIP deals: {response.get('skip_count', 'N/A')}")
                print(f"   Top profit: ${response.get('top_profit', 'N/A')}")
        
        return success, response

    def test_scraping_functionality(self):
        """Test scraping endpoints"""
        # Get initial scrape status
        success, initial_status = self.run_test("Get Initial Scrape Status", "GET", "/scrape-status", 200)
        
        # Trigger manual scrape
        success, scrape_response = self.run_test("Trigger Manual Scrape", "POST", "/scrape", 200)
        
        if success and scrape_response:
            if scrape_response.get('status') == 'already_running':
                print("   Scrape already in progress")
            elif scrape_response.get('status') == 'started':
                print("   Scrape started successfully")
                
                # Wait a bit and check status again
                time.sleep(2)
                self.run_test("Get Scrape Status After Start", "GET", "/scrape-status", 200)
        
        return success, scrape_response

    def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🚀 Starting AutoFlip Intelligence Car Dealer Monitoring API Testing")
        print(f"📡 Testing against: {self.base_url}")
        print("=" * 70)
        
        # Test API availability
        self.test_api_root()
        
        # Core listing functionality
        self.test_get_listings()
        self.test_get_single_listing()
        
        # Dashboard stats
        self.test_stats()
        
        # Scraping functionality
        self.test_scraping_functionality()
        
        # Print summary
        print("\n" + "=" * 70)
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
        
        # Show some sample data insights
        print(f"\n📈 Data Insights:")
        for test in self.test_results:
            if test['success'] and test['test'] == 'Get All Listings' and test['response_json']:
                listings = test['response_json']
                print(f"   • Total listings in database: {len(listings)}")
                
                # Count by source
                sources = {}
                deal_scores = {}
                for listing in listings:
                    source = listing.get('source', 'unknown')
                    sources[source] = sources.get(source, 0) + 1
                    
                    deal_label = listing.get('deal_label')
                    if deal_label:
                        deal_scores[deal_label] = deal_scores.get(deal_label, 0) + 1
                
                print(f"   • By source: {sources}")
                print(f"   • By deal score: {deal_scores}")
                break
        
        return self.tests_passed == self.tests_run

def main():
    print("AutoFlip Intelligence - Backend API Tests")
    print("Testing car dealer monitoring app endpoints...")
    
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