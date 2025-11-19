"""
Integration tests for DepoBangunan product categorization.
"""
from django.test import TestCase
from db_pricing.models import DepoBangunanProduct
from db_pricing.auto_categorization_service import AutoCategorizationService
from api.depobangunan.database_service import DepoBangunanDatabaseService


class DepoBangunanCategorizationIntegrationTest(TestCase):
    """Test categorization integration with database service."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.db_service = DepoBangunanDatabaseService()
        self.categorization_service = AutoCategorizationService()
        
    def tearDown(self):
        """Clean up after tests."""
        DepoBangunanProduct.objects.all().delete()
    
    def test_save_and_categorize_new_products(self):
        """Test that new products are saved and categorized."""
        # Prepare test data
        products_data = [
            {
                'name': 'Semen Gresik 50kg',
                'price': 65000,
                'url': 'https://example.com/semen',
                'unit': 'sak',
                'location': 'Jakarta'
            },
            {
                'name': 'Bata Merah Press',
                'price': 1200,
                'url': 'https://example.com/bata',
                'unit': 'buah',
                'location': 'Bandung'
            }
        ]
        
        # Save products
        result = self.db_service.save_with_price_update(products_data)
        
        # Verify save was successful
        self.assertTrue(result['success'])
        self.assertEqual(result['new_count'], 2)
        self.assertEqual(result['updated_count'], 0)
        
        # Get inserted products
        products = DepoBangunanProduct.objects.all().order_by('-id')[:2]
        product_ids = list(products.values_list('id', flat=True))
        
        # Categorize products
        categorization_result = self.categorization_service.categorize_products(
            'depobangunan', 
            product_ids
        )
        
        # Verify categorization
        self.assertEqual(categorization_result['total'], 2)
        self.assertGreater(categorization_result['categorized'], 0)
        
        # Check that products have categories assigned
        for product in DepoBangunanProduct.objects.filter(id__in=product_ids):
            # Category should not be empty for at least some products
            # (depends on categorizer logic)
            self.assertIsNotNone(product.category)
    
    def test_update_existing_product_keeps_category(self):
        """Test that updating price of existing product keeps its category."""
        # Create initial product
        initial_data = [{
            'name': 'Semen Holcim 50kg',
            'price': 70000,
            'url': 'https://example.com/holcim',
            'unit': 'sak',
            'location': 'Jakarta'
        }]
        
        result = self.db_service.save_with_price_update(initial_data)
        self.assertTrue(result['success'])
        
        # Get the product and categorize it
        product = DepoBangunanProduct.objects.first()
        self.categorization_service.categorize_products('depobangunan', [product.id])
        
        # Reload to get updated category
        product.refresh_from_db()
        initial_category = product.category
        
        # Update the product with new price
        updated_data = [{
            'name': 'Semen Holcim 50kg',
            'price': 72000,  # Price changed
            'url': 'https://example.com/holcim',
            'unit': 'sak',
            'location': 'Jakarta'
        }]
        
        result = self.db_service.save_with_price_update(updated_data)
        
        # Verify update happened
        self.assertTrue(result['success'])
        self.assertEqual(result['updated_count'], 1)
        self.assertEqual(result['new_count'], 0)
        
        # Verify category is preserved
        product.refresh_from_db()
        self.assertEqual(product.category, initial_category)
        self.assertEqual(product.price, 72000)
    
    def test_categorization_handles_uncategorizable_products(self):
        """Test that categorization handles products that can't be categorized."""
        # Products with unclear names
        products_data = [
            {
                'name': 'XYZ123',
                'price': 50000,
                'url': 'https://example.com/xyz',
                'unit': 'unit',
                'location': 'Jakarta'
            }
        ]
        
        result = self.db_service.save_with_price_update(products_data)
        self.assertTrue(result['success'])
        
        product = DepoBangunanProduct.objects.first()
        categorization_result = self.categorization_service.categorize_products(
            'depobangunan', 
            [product.id]
        )
        
        # Should complete without errors
        self.assertEqual(categorization_result['total'], 1)
        # May or may not be categorized depending on categorizer logic
        self.assertIn('categorized', categorization_result)
        self.assertIn('uncategorized', categorization_result)
