"""
Analyze the actual HTML structure to find correct CSS selectors
"""
from api.playwright_client import PlaywrightHttpClient
from bs4 import BeautifulSoup
import re

def analyze_html_structure():
    print("Fetching and analyzing Mitra10 HTML structure...")
    
    client = PlaywrightHttpClient(headless=True, browser_type="chromium")
    
    try:
        with client:
            html = client.get("https://www.mitra10.com/catalogsearch/result?q=pipe", timeout=60)
            
        print(f"✅ Fetched {len(html)} bytes of HTML")
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for elements that might contain product information
        print("\n🔍 Analyzing potential product containers...")
        
        # Find elements with price-like text
        price_elements = []
        for element in soup.find_all(text=re.compile(r'Rp[\s\d.,]+')):
            parent = element.parent
            while parent and parent.name not in ['div', 'span', 'article', 'li']:
                parent = parent.parent
            if parent:
                price_elements.append(parent)
        
        print(f"Found {len(price_elements)} elements containing price text")
        
        # Analyze common parent structures
        if price_elements:
            sample_price_element = price_elements[0]
            print(f"\n📦 Sample price element structure:")
            print(f"Tag: {sample_price_element.name}")
            print(f"Classes: {sample_price_element.get('class', [])}")
            
            # Get the product container (likely a parent element)
            product_container = sample_price_element
            for _ in range(5):  # Go up 5 levels to find product container
                if product_container.parent:
                    product_container = product_container.parent
                    classes = product_container.get('class', [])
                    if any('product' in str(c).lower() or 'item' in str(c).lower() or 'card' in str(c).lower() for c in classes):
                        print(f"\n🎯 Potential product container found:")
                        print(f"Tag: {product_container.name}")
                        print(f"Classes: {classes}")
                        break
            
            # Find common class patterns
            print(f"\n🔍 Analyzing class patterns in price elements...")
            class_patterns = {}
            for elem in price_elements[:10]:  # Sample first 10
                classes = elem.get('class', [])
                for cls in classes:
                    if cls in class_patterns:
                        class_patterns[cls] += 1
                    else:
                        class_patterns[cls] = 1
            
            print("Most common classes in price elements:")
            for cls, count in sorted(class_patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {cls}: {count} occurrences")
        
        # Look for link elements that might be product links
        print(f"\n🔗 Analyzing product links...")
        product_links = soup.find_all('a', href=re.compile(r'/product/|/detail/|\.html'))
        print(f"Found {len(product_links)} potential product links")
        
        if product_links:
            sample_link = product_links[0]
            print(f"Sample link: {sample_link.get('href', '')}")
            print(f"Link classes: {sample_link.get('class', [])}")
            
            # Check if the link contains product name
            link_text = sample_link.get_text(strip=True)
            if link_text:
                print(f"Link text: '{link_text[:100]}...'")
        
        # Save detailed analysis
        with open('html_analysis.txt', 'w', encoding='utf-8') as f:
            f.write("=== MITRA10 HTML STRUCTURE ANALYSIS ===\n\n")
            f.write(f"Total HTML size: {len(html)} bytes\n")
            f.write(f"Price elements found: {len(price_elements)}\n")
            f.write(f"Product links found: {len(product_links)}\n\n")
            
            if price_elements:
                f.write("SAMPLE PRICE ELEMENT HTML:\n")
                f.write(str(price_elements[0].prettify())[:2000])
                f.write("\n\n")
            
            if product_links:
                f.write("SAMPLE PRODUCT LINK HTML:\n")
                f.write(str(product_links[0].prettify())[:2000])
                f.write("\n\n")
        
        print("\n✅ Analysis complete! Check 'html_analysis.txt' for detailed results.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    analyze_html_structure()