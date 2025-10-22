#!/usr/bin/env python3
"""
Government Wage API Usage Examples

This script demonstrates how to use the government wage scraper API endpoints.
Run this script after starting the Django development server.

Usage:
    python government_wage_api_demo.py

Requirements:
    - Django server running on http://localhost:8000
    - requests library (pip install requests)
"""

import requests
import json
import time


class GovernmentWageAPIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def get_available_regions(self):
        """Get list of all available regions"""
        print("\n=== Getting Available Regions ===")
        
        try:
            response = self.session.get(f"{self.base_url}/api/government_wage/regions/")
            response.raise_for_status()
            
            data = response.json()
            if data['success']:
                print(f"✅ Found {data['count']} available regions")
                print("📋 Available regions:")
                for i, region in enumerate(data['regions'][:10], 1):  # Show first 10
                    print(f"   {i}. {region}")
                if len(data['regions']) > 10:
                    print(f"   ... and {len(data['regions']) - 10} more")
            else:
                print(f"❌ Failed: {data.get('error_message', 'Unknown error')}")
            
            return data
            
        except requests.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None

    def scrape_region_data(self, region="Kab. Cilacap"):
        """Scrape government wage data for a specific region"""
        print(f"\n=== Scraping Region Data for {region} ===")
        
        try:
            params = {'region': region}
            response = self.session.get(
                f"{self.base_url}/api/government_wage/scrape/", 
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            if data['success']:
                print(f"✅ Scraped {data['count']} wage items from {data['region']}")
                
                if data['data']:
                    print("📊 Sample wage data:")
                    for i, item in enumerate(data['data'][:3], 1):  # Show first 3 items
                        print(f"   {i}. Work Code: {item['work_code']}")
                        print(f"      Description: {item['work_description']}")
                        print(f"      Unit Price: Rp {item['unit_price_idr']:,}")
                        print(f"      Unit: {item['unit']}")
                        print()
                    
                    if len(data['data']) > 3:
                        print(f"   ... and {len(data['data']) - 3} more items")
            else:
                print(f"❌ Failed: {data.get('error_message', 'Unknown error')}")
            
            return data
            
        except requests.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None

    def search_by_work_code(self, work_code, region=None):
        """Search government wage data by work code"""
        region_text = f" in {region}" if region else ""
        print(f"\n=== Searching for Work Code '{work_code}'{region_text} ===")
        
        try:
            params = {'work_code': work_code}
            if region:
                params['region'] = region
                
            response = self.session.get(
                f"{self.base_url}/api/government_wage/search/", 
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            if data['success']:
                print(f"✅ Found {data['count']} matching items")
                
                if data['data']:
                    print("🔍 Search results:")
                    for i, item in enumerate(data['data'], 1):
                        print(f"   {i}. Work Code: {item['work_code']}")
                        print(f"      Description: {item['work_description']}")
                        print(f"      Unit Price: Rp {item['unit_price_idr']:,}")
                        print(f"      Region: {item['region']}")
                        print()
                else:
                    print("📭 No matching items found")
            else:
                print(f"❌ Failed: {data.get('error_message', 'Unknown error')}")
            
            return data
            
        except requests.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None

    def scrape_limited_regions(self, max_regions=3):
        """Scrape data from a limited number of regions (for demo purposes)"""
        print(f"\n=== Scraping Data from {max_regions} Regions (Demo) ===")
        print("⚠️  This may take several minutes...")
        
        try:
            params = {'max_regions': max_regions}
            response = self.session.get(
                f"{self.base_url}/api/government_wage/scrape-all/", 
                params=params,
                timeout=300  # 5 minute timeout
            )
            response.raise_for_status()
            
            data = response.json()
            if data['success']:
                print(f"✅ Scraped {data['total_items']} items from {data['total_regions']} regions")
                
                print("📈 Region summary:")
                for region, items in data['regions_data'].items():
                    print(f"   📍 {region}: {len(items)} items")
            else:
                print(f"❌ Failed: {data.get('error_message', 'Unknown error')}")
            
            return data
            
        except requests.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None


def main():
    """Main demo function"""
    print("🏗️  Government Wage Scraper API Demo")
    print("=" * 50)
    
    # Initialize API client
    client = GovernmentWageAPIClient()
    
    # Test API endpoints
    try:
        # 1. Get available regions
        regions_data = client.get_available_regions()
        
        # 2. Scrape data for default region
        if regions_data and regions_data['success']:
            sample_region = regions_data['regions'][0] if regions_data['regions'] else "Kab. Cilacap"
            client.scrape_region_data(sample_region)
        
        # 3. Search by work code
        client.search_by_work_code("6.1.1", "Kab. Cilacap")
        
        # 4. Ask user if they want to run the intensive scraping demo
        print("\n" + "=" * 50)
        print("⚠️  WARNING: The next demo will scrape multiple regions")
        print("   This may take several minutes and should only be used for testing.")
        
        choice = input("\nDo you want to run the multi-region scraping demo? (y/N): ").strip().lower()
        
        if choice == 'y':
            client.scrape_limited_regions(3)
        else:
            print("👍 Skipping multi-region demo")
        
        print("\n🎉 Demo completed successfully!")
        print("\n📚 API Documentation:")
        print("   - GET /api/government_wage/regions/")
        print("   - GET /api/government_wage/scrape/?region=<region_name>")
        print("   - GET /api/government_wage/search/?work_code=<code>&region=<region>")
        print("   - GET /api/government_wage/scrape-all/?max_regions=<number>")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")


if __name__ == "__main__":
    main()