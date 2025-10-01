"""
Test basic connectivity to Mitra10 website
"""
from api.playwright_client import PlaywrightHttpClient

def test_basic_connectivity():
    print("Testing basic connectivity to Mitra10...")
    
    # Test different URLs
    urls_to_test = [
        "https://www.mitra10.com/",
        "https://www.mitra10.com/catalogsearch/result?q=semen",
        "https://www.mitra10.com/catalogsearch/result?q=pipe",
    ]
    
    for url in urls_to_test:
        print(f"\n🔗 Testing: {url}")
        
        try:
            client = PlaywrightHttpClient(headless=True, browser_type="chromium")
            
            with client:
                # Try with longer timeout
                html = client.get(url, timeout=60)
                
                print(f"✅ Success! Retrieved {len(html)} bytes")
                
                # Check if it looks like a valid page
                if "mitra10" in html.lower():
                    print("✅ Content appears to be from Mitra10")
                else:
                    print("⚠️ Content doesn't appear to be from Mitra10")
                    
                # Save a sample for inspection
                filename = f"sample_{url.split('/')[-1] or 'homepage'}.html"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html[:5000])  # First 5KB
                print(f"💾 Sample saved to {filename}")
                
                break  # Success - no need to test other URLs
                
        except Exception as e:
            print(f"❌ Failed: {e}")
            continue
    
    print("\n✅ Test completed")

if __name__ == "__main__":
    test_basic_connectivity()