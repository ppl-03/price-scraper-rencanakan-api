"""
Diagnostic script to analyze Mitra10 HTML structure and find correct selectors
"""
from api.mitra10.factory import create_mitra10_scraper
from bs4 import BeautifulSoup
import re

def analyze_html_structure():
    # Create scraper
    scraper = create_mitra10_scraper()
    
    # Test URL
    url = "https://www.mitra10.com/catalogsearch/result?q=semen&sort=%7B%22key%22%3A%22price%22%2C%22value%22%3A%22ASC%22%7D&page=1"
    
    print("Fetching HTML content...")
    try:
        # Get HTML using the playwright client
        with scraper.http_client as client:
            html_content = client.get(url, timeout=30)
        
        print(f"✅ Successfully fetched {len(html_content)} bytes of HTML")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        print("\n" + "="*60)
        print("ANALYZING HTML STRUCTURE")
        print("="*60)
        
        # Look for common product container patterns
        print("\n🔍 Searching for product containers...")
        
        # Check for various div patterns that might contain products
        patterns_to_check = [
            "div[class*='product']",
            "div[class*='item']", 
            "div[class*='card']",
            "div[class*='grid']",
            "article",
            "li[class*='product']",
            "div[data-testid*='product']",
        ]
        
        for pattern in patterns_to_check:
            elements = soup.select(pattern)
            if elements:
                print(f"  ✅ Found {len(elements)} elements matching '{pattern}'")
                
                # Show first element structure
                if len(elements) > 0:
                    first_element = elements[0]
                    print(f"     Sample element classes: {first_element.get('class', [])}")
                    print(f"     Sample element attributes: {list(first_element.attrs.keys())}")
            else:
                print(f"  ❌ No elements found for '{pattern}'")
        
        # Look for price elements
        print("\n💰 Searching for price elements...")
        price_patterns = [
            "span[class*='price']",
            "div[class*='price']", 
            "p[class*='price']",
            "*[class*='currency']",
            "*[class*='amount']",
        ]
        
        for pattern in price_patterns:
            elements = soup.select(pattern)
            if elements:
                print(f"  ✅ Found {len(elements)} price elements matching '{pattern}'")
                # Show sample price text
                for i, elem in enumerate(elements[:3]):
                    text = elem.get_text(strip=True)
                    if text and any(char.isdigit() for char in text):
                        print(f"     Sample price text: '{text}'")
                        break
        
        # Look for product names/titles
        print("\n📝 Searching for product names...")
        name_patterns = [
            "h1", "h2", "h3", "h4",
            "a[class*='title']",
            "a[class*='name']", 
            "p[class*='title']",
            "span[class*='title']",
        ]
        
        for pattern in name_patterns:
            elements = soup.select(pattern)
            if elements:
                print(f"  ✅ Found {len(elements)} name elements matching '{pattern}'")
                # Show sample text
                for elem in elements[:3]:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 10:  # Likely product name
                        print(f"     Sample name: '{text[:50]}...'")
                        break
        
        # Save a sample of HTML for manual inspection
        print(f"\n💾 Saving first 5000 characters to 'mitra10_sample.html'...")
        with open("mitra10_sample.html", "w", encoding="utf-8") as f:
            f.write(html_content[:5000])
        
        print("\n✅ Analysis complete! Check 'mitra10_sample.html' for manual inspection.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    analyze_html_structure()