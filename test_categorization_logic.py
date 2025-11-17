import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_scraper_rencanakan_api.settings')
django.setup()

from db_pricing.categorization import ProductCategorizer

def test_categorization():
    print("="*80)
    print("  CATEGORIZATION LOGIC TEST")
    print("="*80)
    
    categorizer = ProductCategorizer()
    
    print("\n📋 Testing Steel Products:")
    steel_products = [
        "Besi Beton 10mm",
        "Baja Ringan 0.75mm",
        "Wiremesh M8",
        "Hollow 4x4",
        "Siku 40x40",
        "CNP 100",
        "Besi Tulangan 12mm",
        "H-Beam 200x200",
    ]
    
    for product in steel_products:
        category = categorizer.categorize(product)
        print(f"   ✓ {product:<30} → {category}")
    
    print("\n🏠 Testing Material Interior Products:")
    interior_products = [
        "Cat Tembok Avian",
        "Keramik Lantai 40x40",
        "Wallpaper Motif Bunga",
        "Granit 60x60 Polished",
        "Karpet Vinyl",
        "Lantai Kayu Laminated",
        "Cat Kayu Aqua",
        "Plafon PVC",
        "Gypsum Board 9mm",
        "Lem Keramik",
    ]
    
    for product in interior_products:
        category = categorizer.categorize(product)
        print(f"   ✓ {product:<30} → {category}")
    
    print("\n❌ Testing Non-Categorized Products:")
    other_products = [
        "Semen Portland",
        "Pasir Beton",
        "Batu Split",
        "Pipa PVC 3 inch",
        "Kabel NYM 2x1.5",
    ]
    
    for product in other_products:
        category = categorizer.categorize(product)
        print(f"   ✓ {product:<30} → {category if category else 'None (Uncategorized)'}")
    
    print("\n" + "="*80)
    print("  CATEGORIZATION TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    test_categorization()
