"""
Simple test to check if Mitra10 scraper is working after JavaScript fix
"""
from api.mitra10.factory import create_mitra10_scraper

def simple_test():
    print("Testing Mitra10 scraper with JavaScript enabled...")
    
    # Create scraper
    scraper = create_mitra10_scraper()
    
    # Test with a simple keyword
    keywords = ["semen"]
    
    try:
        print(f"Scraping for keywords: {keywords}")
        products = scraper.scrape_batch(keywords)
        
        print(f"✅ Scraping completed! Found {len(products)} products")
        
        if products:
            print("\n📦 Sample products:")
            for i, product in enumerate(products[:3], 1):
                print(f"{i}. {product.name}")
                print(f"   Price: Rp {product.price:,}")
                print(f"   URL: {product.url}")
                print()
        else:
            print("❌ No products found. This might be a parsing issue.")
            
    except Exception as e:
        print(f"❌ Error occurred: {e}")

if __name__ == "__main__":
    simple_test()