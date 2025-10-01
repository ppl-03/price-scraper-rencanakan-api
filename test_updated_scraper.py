"""
Test updated Mitra10 scraper with improved selectors and loading strategy
"""
from api.mitra10.factory import create_mitra10_scraper

def test_updated_scraper():
    print("Testing updated Mitra10 scraper...")
    
    # Create scraper
    scraper = create_mitra10_scraper()
    
    # Test with different keywords
    test_keywords = ["pipe", "cat", "paku"]
    
    for keyword in test_keywords:
        print(f"\n🔍 Testing '{keyword}'...")
        
        try:
            products = scraper.scrape_batch([keyword])
            
            if products:
                print(f"✅ SUCCESS! Found {len(products)} products for '{keyword}'")
                
                # Show first few products
                for i, product in enumerate(products[:3], 1):
                    print(f"  {i}. {product.name[:50]}...")
                    print(f"     Price: Rp {product.price:,}")
                    print(f"     URL: {product.url[:60]}...")
                
                return True  # Success! Stop testing
            else:
                print(f"❌ No products found for '{keyword}'")
                
        except Exception as e:
            print(f"❌ Error with '{keyword}': {e}")
            continue
    
    print("\n⚠️ All tests failed - scraper needs more debugging")
    return False

if __name__ == "__main__":
    success = test_updated_scraper()
    if success:
        print("\n🎉 Mitra10 scraper is now working!")
    else:
        print("\n🔧 Scraper still needs fixes")