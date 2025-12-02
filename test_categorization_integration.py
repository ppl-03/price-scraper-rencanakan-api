"""
Quick test script to verify product categorization integration
"""

from db_pricing.categorization import ProductCategorizer

def test_categorization():
    """Test that categorization works correctly"""
    categorizer = ProductCategorizer()
    
    test_products = [
        ("Semen Portland 50kg", "Tanah, Pasir, Batu, dan Semen"),
        ("Besi Beton 10mm", "Baja dan Besi Tulangan"),
        ("Pipa PVC 3 inch", "Material Pipa Air"),
        ("Keramik Granite 60x60", "Material Interior"),
        ("Kabel NYY 3x2.5mm", "Material Listrik"),
        ("Closet Duduk TOTO", "Material Sanitair"),
        ("Palu Besi 1kg", "Peralatan Kerja"),
        ("Excavator Komatsu", "Alat Berat"),
    ]
    
    print("Testing Product Categorization Integration\n")
    print("=" * 80)
    
    all_passed = True
    for product_name, expected_category in test_products:
        result = categorizer.categorize(product_name)
        status = "✓ PASS" if result == expected_category else "✗ FAIL"
        
        if result != expected_category:
            all_passed = False
            
        print(f"{status} | {product_name:<35} | {result or 'Lainnya':<40}")
        if result != expected_category:
            print(f"       Expected: {expected_category}")
    
    print("=" * 80)
    
    if all_passed:
        print("\n✓ All categorization tests passed!")
    else:
        print("\n✗ Some tests failed. Please review the categorization logic.")
    
    return all_passed

if __name__ == "__main__":
    test_categorization()
