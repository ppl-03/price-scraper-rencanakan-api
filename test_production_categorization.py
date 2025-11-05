import os
import sys
import django
import requests
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_scraper_rencanakan_api.settings')
django.setup()

from db_pricing.models import GemilangProduct, Mitra10Product, DepoBangunanProduct, JuraganMaterialProduct
from db_pricing.categorization import ProductCategorizer
from db_pricing.auto_categorization_service import AutoCategorizationService


BASE_URL = "http://localhost:8000"


def print_header(text):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_section(text):
    print("\n" + "-" * 80)
    print(f"  {text}")
    print("-" * 80)


def test_database_connection():
    print_header("TEST 1: DATABASE CONNECTION")
    
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            print(f"✅ Connected to database: {db_name}")
            
            cursor.execute("SELECT COUNT(*) FROM gemilang_products")
            count = cursor.fetchone()[0]
            print(f"📊 Gemilang products count: {count}")
            
            cursor.execute("SELECT COUNT(*) FROM mitra10_products")
            count = cursor.fetchone()[0]
            print(f"📊 Mitra10 products count: {count}")
            
            cursor.execute("SELECT COUNT(*) FROM depobangunan_products")
            count = cursor.fetchone()[0]
            print(f"📊 DepoBangunan products count: {count}")
            
            cursor.execute("SELECT COUNT(*) FROM juragan_material_products")
            count = cursor.fetchone()[0]
            print(f"📊 JuraganMaterial products count: {count}")
            
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False


def test_categorization_logic():
    print_header("TEST 2: CATEGORIZATION LOGIC")
    
    categorizer = ProductCategorizer()
    
    test_cases = [
        ("Besi Beton 10mm SNI", "Baja dan Besi Tulangan"),
        ("Wiremesh M8 2.10x5.40", "Baja dan Besi Tulangan"),
        ("Baja Ringan 0.75mm", "Baja dan Besi Tulangan"),
        ("Hollow Galvanis 4x4", "Baja dan Besi Tulangan"),
        ("Besi Siku 40x40x4mm", "Baja dan Besi Tulangan"),
        ("Semen Portland 50kg", None),
        ("Cat Tembok Putih", None),
    ]
    
    passed = 0
    failed = 0
    
    for product_name, expected_category in test_cases:
        result = categorizer.categorize(product_name)
        if result == expected_category:
            icon = "🔩" if result else "📦"
            print(f"✅ {icon} {product_name} → {result or 'None'}")
            passed += 1
        else:
            print(f"❌ {product_name} → Expected: {expected_category}, Got: {result}")
            failed += 1
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_auto_categorization_service():
    print_header("TEST 3: AUTO CATEGORIZATION SERVICE")
    
    try:
        print("Creating test products...")
        
        test_products = [
            GemilangProduct.objects.create(
                name="Test Besi Beton 12mm",
                price=100000,
                url="http://test.com/test1",
                unit="batang"
            ),
            GemilangProduct.objects.create(
                name="Test Semen",
                price=65000,
                url="http://test.com/test2",
                unit="sak"
            ),
        ]
        
        product_ids = [p.id for p in test_products]
        print(f"Created {len(product_ids)} test products")
        
        service = AutoCategorizationService()
        result = service.categorize_products('gemilang', product_ids)
        
        print(f"✅ Categorization complete:")
        print(f"   Total: {result['total']}")
        print(f"   Categorized: {result['categorized']}")
        print(f"   Uncategorized: {result['uncategorized']}")
        
        for product_id in product_ids:
            product = GemilangProduct.objects.get(id=product_id)
            icon = "🔩" if product.category else "📦"
            print(f"   {icon} {product.name} → {product.category or 'None'}")
        
        for product_id in product_ids:
            GemilangProduct.objects.filter(id=product_id).delete()
        print("Cleaned up test products")
        
        return result['categorized'] == 1
        
    except Exception as e:
        print(f"❌ Auto categorization test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_existing_products_categorization():
    print_header("TEST 4: CATEGORIZE EXISTING PRODUCTS")
    
    try:
        print("Fetching existing products...")
        
        gemilang_count = GemilangProduct.objects.count()
        mitra10_count = Mitra10Product.objects.count()
        depo_count = DepoBangunanProduct.objects.count()
        juragan_count = JuraganMaterialProduct.objects.count()
        
        print(f"📊 Current product counts:")
        print(f"   Gemilang: {gemilang_count}")
        print(f"   Mitra10: {mitra10_count}")
        print(f"   DepoBangunan: {depo_count}")
        print(f"   JuraganMaterial: {juragan_count}")
        
        if gemilang_count > 0:
            print("\nSample Gemilang products:")
            products = GemilangProduct.objects.all()[:5]
            categorizer = ProductCategorizer()
            
            for product in products:
                category = categorizer.categorize(product.name)
                icon = "🔩" if category else "📦"
                print(f"   {icon} {product.name[:50]} → {category or 'None'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False


def test_api_endpoint():
    print_header("TEST 5: API ENDPOINT TEST")
    
    try:
        response = requests.get(f"{BASE_URL}/api/db-status/", timeout=5)
        
        if response.status_code == 200:
            print(f"✅ Server is running at {BASE_URL}")
            data = response.json()
            print(f"   Database: {data.get('database', 'Unknown')}")
            return True
        else:
            print(f"⚠️ Server responded with status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to server at {BASE_URL}")
        print("   Make sure Django server is running: python manage.py runserver")
        return False
    except Exception as e:
        print(f"❌ API test failed: {str(e)}")
        return False


def test_scrape_and_categorize_integration():
    print_header("TEST 6: SCRAPE & CATEGORIZE INTEGRATION")
    
    try:
        print("📊 Getting product count BEFORE scraping...")
        before_count = GemilangProduct.objects.count()
        print(f"   Products before: {before_count}")
        
        print("\n🔍 Scraping with keyword 'besi' (will scrape to MAIN DATABASE)...")
        
        url = f"{BASE_URL}/api/gemilang/scrape-and-save/"
        headers = {
            'Content-Type': 'application/json',
            'X-API-Token': 'dev-token-12345'
        }
        payload = {
            'keyword': 'besi',
            'page': 0
        }
        
        print(f"📡 Calling: {url}")
        print(f"🔍 Keyword: {payload['keyword']}")
        print("⏳ Please wait, scraping in progress...")
        
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Scraping Complete!")
            print(f"   Saved: {data.get('saved', 0)}")
            print(f"   Inserted: {data.get('inserted', 0)}")
            print(f"   Updated: {data.get('updated', 0)}")
            print(f"   Categorized: {data.get('categorized', 0)}")
            
            print("\n📊 Getting product count AFTER scraping...")
            after_count = GemilangProduct.objects.count()
            print(f"   Products after: {after_count}")
            print(f"   New products: {after_count - before_count}")
            
            print("\n🔍 Checking newly scraped products...")
            latest_products = GemilangProduct.objects.order_by('-created_at')[:10]
            
            steel_count = 0
            other_count = 0
            
            print("\n📦 Latest 10 products from scrape:")
            for product in latest_products:
                if product.category == "Baja dan Besi Tulangan":
                    icon = "🔩"
                    steel_count += 1
                elif product.category:
                    icon = "📦"
                    other_count += 1
                else:
                    icon = "❓"
                    other_count += 1
                
                print(f"   {icon} {product.name[:60]:<60} | Category: {product.category or 'None'}")
            
            print(f"\n📊 Categorization Results:")
            print(f"   Steel products: {steel_count}/10")
            print(f"   Other products: {other_count}/10")
            
            all_steel = GemilangProduct.objects.filter(category="Baja dan Besi Tulangan").count()
            all_products = GemilangProduct.objects.count()
            print(f"\n📊 Overall Database Statistics:")
            print(f"   Total products: {all_products}")
            print(f"   Steel products: {all_steel} ({(all_steel/all_products*100) if all_products > 0 else 0:.1f}%)")
            
            return True
        else:
            print(f"⚠️ Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to server at {BASE_URL}")
        print("   Make sure Django server is running: python manage.py runserver")
        print("   Skipping integration test")
        return None
    except Exception as e:
        print(f"❌ Integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "🔧" * 40)
    print("  PRODUCTION DATABASE TEST SUITE")
    print("  Auto-Categorization System")
    print("🔧" * 40)
    
    results = {}
    
    results['database'] = test_database_connection()
    
    if not results['database']:
        print("\n❌ Database connection failed. Cannot proceed with other tests.")
        return
    
    results['categorization_logic'] = test_categorization_logic()
    results['auto_categorization'] = test_auto_categorization_service()
    results['existing_products'] = test_existing_products_categorization()
    results['api_endpoint'] = test_api_endpoint()
    
    if results['api_endpoint']:
        results['integration'] = test_scrape_and_categorize_integration()
    else:
        results['integration'] = None
    
    print_header("SUMMARY")
    
    total_tests = 0
    passed_tests = 0
    skipped_tests = 0
    
    for test_name, result in results.items():
        if result is None:
            status = "⏭️ SKIPPED"
            skipped_tests += 1
        elif result:
            status = "✅ PASSED"
            passed_tests += 1
        else:
            status = "❌ FAILED"
        total_tests += 1
        print(f"{status} - {test_name.replace('_', ' ').title()}")
    
    print(f"\n📊 Total: {total_tests} tests")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {total_tests - passed_tests - skipped_tests}")
    print(f"⏭️ Skipped: {skipped_tests}")
    
    if passed_tests == total_tests - skipped_tests:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️ Some tests failed. Please review the output above.")


if __name__ == "__main__":
    main()
