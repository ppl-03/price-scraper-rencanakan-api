"""
Simple test script to verify Juragan Material categorization integration.
Run this with: python manage.py shell < test_juragan_categorization.py
"""

from db_pricing.models import JuraganMaterialProduct
from api.juragan_material.database_service import JuraganMaterialDatabaseService
from db_pricing.auto_categorization_service import AutoCategorizationService

print("=" * 60)
print("Testing Juragan Material Categorization Integration")
print("=" * 60)

# Clean up existing test data
print("\n1. Cleaning up existing test data...")
JuraganMaterialProduct.objects.filter(name__contains='TEST_SEMEN').delete()

# Create test products
print("\n2. Creating test products...")
db_service = JuraganMaterialDatabaseService()
test_products = [
    {
        'name': 'TEST_SEMEN Gresik 50kg',
        'price': 65000,
        'url': 'https://test.com/semen-gresik',
        'unit': 'sak',
        'location': 'Jakarta'
    },
    {
        'name': 'TEST_SEMEN Holcim 40kg',
        'price': 62000,
        'url': 'https://test.com/semen-holcim',
        'unit': 'sak',
        'location': 'Bandung'
    }
]

result = db_service.save_with_price_update(test_products)
print(f"   Save result: {result}")

# Get the inserted products
print("\n3. Retrieving inserted products...")
products = JuraganMaterialProduct.objects.filter(name__contains='TEST_SEMEN').order_by('-id')
product_ids = list(products.values_list('id', flat=True))
print(f"   Found {len(product_ids)} products: {product_ids}")

# Show products before categorization
print("\n4. Products before categorization:")
for product in products:
    print(f"   - {product.name}: category='{product.category}'")

# Categorize products
print("\n5. Categorizing products...")
cat_service = AutoCategorizationService()
cat_result = cat_service.categorize_products('juragan_material', product_ids)
print(f"   Categorization result: {cat_result}")

# Show products after categorization
print("\n6. Products after categorization:")
for product in JuraganMaterialProduct.objects.filter(id__in=product_ids):
    print(f"   - {product.name}: category='{product.category}'")

# Test price update (should preserve category)
print("\n7. Testing price update (should preserve category)...")
update_products = [
    {
        'name': 'TEST_SEMEN Gresik 50kg',
        'price': 66000,  # Updated price
        'url': 'https://test.com/semen-gresik',
        'unit': 'sak',
        'location': 'Jakarta'
    }
]
update_result = db_service.save_with_price_update(update_products)
print(f"   Update result: {update_result}")

# Verify category is preserved
updated_product = JuraganMaterialProduct.objects.get(name='TEST_SEMEN Gresik 50kg')
print(f"   Updated product: {updated_product.name}")
print(f"   - Price: {updated_product.price}")
print(f"   - Category: '{updated_product.category}'")

print("\n" + "=" * 60)
print("Test completed successfully!")
print("=" * 60)

# Clean up
print("\nCleaning up test data...")
JuraganMaterialProduct.objects.filter(name__contains='TEST_SEMEN').delete()
print("Done!")
