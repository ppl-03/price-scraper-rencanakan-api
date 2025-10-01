"""
Simple script to test Mitra10 scraper
"""
from api.mitra10.factory import create_mitra10_scraper

def main():
    # Create scraper
    scraper = create_mitra10_scraper()
    
    # Test keywords
    keywords = ["semen"]
    
    print(f"Testing Mitra10 scraper with keywords: {keywords}")
    print("="*60)
    
    # Scrape products
    products = scraper.scrape_batch(keywords)
    
    print(f"\nFound {len(products)} products:")
    print("="*60)
    
    # Display results
    for i, product in enumerate(products[:5], 1):  # Show first 5 products
        print(f"\n{i}. {product['name']}")
        print(f"   Price: Rp {product['price']:,}")
        print(f"   URL: {product['url']}")
        print(f"   Slug: {product['slug']}")
    
    if len(products) > 5:
        print(f"\n... and {len(products) - 5} more products")

if __name__ == "__main__":
    main()
