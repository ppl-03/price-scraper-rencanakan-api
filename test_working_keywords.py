"""
Test Mitra10 scraper with working search terms
"""
from api.mitra10.factory import create_mitra10_scraper
from bs4 import BeautifulSoup

def test_with_working_keywords():
    print("Testing Mitra10 scraper with working keywords...")
    
    # Create scraper
    scraper = create_mitra10_scraper()
    
    # Test with keywords that should work
    working_keywords = ["pipe", "cat", "paku", "genteng"]
    
    for keyword in working_keywords:
        print(f"\n🔍 Testing keyword: '{keyword}'")
        
        try:
            products = scraper.scrape_batch([keyword])
            
            print(f"✅ Found {len(products)} products for '{keyword}'")
            
            if products:
                print("📦 Sample products:")
                for i, product in enumerate(products[:3], 1):
                    print(f"  {i}. {product.get('name', 'No name')}")
                    print(f"     Price: Rp {product.get('price', 0):,}")
                    print(f"     URL: {product.get('url', 'No URL')}")
                
                return True  # Success!
            else:
                print("❌ No products parsed (HTML parsing issue)")
                
                # Let's debug the HTML structure
                print("🔍 Debugging HTML structure...")
                with scraper.http_client as client:
                    html = client.get(f"https://www.mitra10.com/catalogsearch/result?q={keyword}")
                    
                    # Save HTML sample for inspection
                    with open(f"debug_{keyword}.html", 'w', encoding='utf-8') as f:
                        f.write(html[:10000])  # First 10KB
                    print(f"💾 HTML sample saved to debug_{keyword}.html")
                    
                    # Quick analysis
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Check for various product patterns
                    product_divs = soup.select('div[class*="product"]')
                    grid_items = soup.select('div[class*="grid"]')
                    mui_items = soup.select('div[class*="Mui"]')
                    
                    print(f"  - Found {len(product_divs)} divs with 'product' in class")
                    print(f"  - Found {len(grid_items)} divs with 'grid' in class") 
                    print(f"  - Found {len(mui_items)} divs with 'Mui' in class")
                    
                    # Look for prices
                    price_spans = soup.select('span[class*="price"]')
                    print(f"  - Found {len(price_spans)} spans with 'price' in class")
                    
                    break  # Stop after first debugging attempt
                        
        except Exception as e:
            print(f"❌ Error with '{keyword}': {e}")
    
    return False

if __name__ == "__main__":
    success = test_with_working_keywords()
    if success:
        print("\n🎉 Mitra10 scraper is working!")
    else:
        print("\n⚠️ Mitra10 scraper needs debugging")