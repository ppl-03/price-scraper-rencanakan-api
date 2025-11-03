import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_scraper_rencanakan_api.settings')
django.setup()

from db_pricing.models import GemilangProduct, Mitra10Product, DepoBangunanProduct, JuraganMaterialProduct
from db_pricing.auto_categorization_service import AutoCategorizationService


def print_header(text):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def categorize_vendor(vendor_key, vendor_name, model_class):
    print(f"\n🔄 Processing {vendor_name}...")
    
    total = model_class.objects.count()
    before_steel = model_class.objects.filter(category="Baja dan Besi Tulangan").count()
    before_interior = model_class.objects.filter(category="Material Interior").count()
    
    print(f"   Before: {total} total, {before_steel} steel, {before_interior} interior")
    
    if total == 0:
        print(f"   ⚠️  No products found for {vendor_name}")
        return
    
    service = AutoCategorizationService()
    result = service.categorize_all_products(vendor_key)
    
    after_steel = model_class.objects.filter(category="Baja dan Besi Tulangan").count()
    after_interior = model_class.objects.filter(category="Material Interior").count()
    uncategorized = total - after_steel - after_interior
    
    print(f"   After:  {after_steel} steel (+{after_steel - before_steel}), {after_interior} interior (+{after_interior - before_interior}), {uncategorized} uncategorized")
    
    if after_steel > 0:
        samples = model_class.objects.filter(category="Baja dan Besi Tulangan")[:3]
        print(f"   Sample Steel Products:")
        for product in samples:
            print(f"      🔩 {product.name[:70]}")
    
    if after_interior > 0:
        samples = model_class.objects.filter(category="Material Interior")[:3]
        print(f"   Sample Interior Products:")
        for product in samples:
            print(f"      🏠 {product.name[:70]}")
    
    return {
        'total': total,
        'steel': after_steel,
        'interior': after_interior,
        'uncategorized': uncategorized
    }


def main():
    print("\n" + "🔧" * 40)
    print("  CATEGORIZE AND SAVE TO PRODUCTION DATABASE")
    print("  Database: " + os.getenv('MYSQL_DATABASE', 'N/A'))
    print("  Host: " + os.getenv('MYSQL_HOST', 'N/A'))
    print("🔧" * 40)
    
    vendors = [
        ('gemilang', 'Gemilang', GemilangProduct),
        ('mitra10', 'Mitra10', Mitra10Product),
        ('depobangunan', 'DepoBangunan', DepoBangunanProduct),
        ('juraganmaterial', 'JuraganMaterial', JuraganMaterialProduct),
    ]
    
    print_header("STEP 1: Categorize All Products and Save to Database")
    
    results = {}
    for vendor_key, vendor_name, model_class in vendors:
        try:
            result = categorize_vendor(vendor_key, vendor_name, model_class)
            if result:
                results[vendor_name] = result
        except Exception as e:
            print(f"   ❌ Error processing {vendor_name}: {str(e)}")
    
    print_header("STEP 2: Final Summary")
    
    grand_total = 0
    grand_steel = 0
    grand_interior = 0
    grand_uncategorized = 0
    
    print("\n📊 Final Statistics by Vendor:")
    for vendor_name, stats in results.items():
        grand_total += stats['total']
        grand_steel += stats['steel']
        grand_interior += stats['interior']
        grand_uncategorized += stats['uncategorized']
        
        steel_pct = (stats['steel'] / stats['total'] * 100) if stats['total'] > 0 else 0
        interior_pct = (stats['interior'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
        print(f"   {vendor_name}:")
        print(f"      Total: {stats['total']}")
        print(f"      Steel: {stats['steel']} ({steel_pct:.1f}%)")
        print(f"      Interior: {stats['interior']} ({interior_pct:.1f}%)")
        print(f"      Uncategorized: {stats['uncategorized']}")
    
    print("\n" + "=" * 80)
    print("  GRAND TOTAL - ALL VENDORS")
    print("=" * 80)
    print(f"   Total Products: {grand_total}")
    print(f"   Steel Products: {grand_steel} ({grand_steel/grand_total*100:.1f}%)")
    print(f"   Interior Products: {grand_interior} ({grand_interior/grand_total*100:.1f}%)")
    print(f"   Uncategorized: {grand_uncategorized} ({grand_uncategorized/grand_total*100:.1f}%)")
    print(f"   Categorized: {grand_steel + grand_interior} ({(grand_steel + grand_interior)/grand_total*100:.1f}%)")
    
    print("\n✅ All categorizations saved to database!")
    print("✅ You can now query using SQL:")
    print("   SELECT * FROM gemilang_products WHERE category = 'Material Interior';")
    print("   SELECT * FROM mitra10_products WHERE category = 'Baja dan Besi Tulangan';")
    
    print("\n" + "✓" * 40)
    print("  CATEGORIZATION COMPLETED AND SAVED")
    print("✓" * 40 + "\n")


if __name__ == "__main__":
    main()
