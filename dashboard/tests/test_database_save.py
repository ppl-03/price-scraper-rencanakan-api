from django.test import TestCase
from dashboard.views import _save_products_to_database
from db_pricing.models import GemilangProduct, Mitra10Product, JuraganMaterialProduct


class MockProduct:
    def __init__(self, name, price, url, unit, location=None):
        self.name = name
        self.price = price
        self.url = url
        self.unit = unit
        if location is not None:
            self.location = location


class AutoSaveProductsTests(TestCase):
    
    def setUp(self):
        GemilangProduct.objects.all().delete()
        Mitra10Product.objects.all().delete()
        JuraganMaterialProduct.objects.all().delete()
    
    def test_save_gemilang_products(self):
        products = [
            MockProduct('Semen Portland', 75000, 'https://gemilang.com/semen', 'sak')
        ]
        
        result = _save_products_to_database(products, 'Gemilang Store')
        
        self.assertTrue(result)
        self.assertEqual(GemilangProduct.objects.count(), 1)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.name, 'Semen Portland')
        self.assertEqual(product.price, 75000)
    
    def test_save_mitra10_products_with_category(self):
        products = [
            MockProduct('Cat Tembok', 95000, 'https://mitra10.com/cat', 'kaleng')
        ]
        
        result = _save_products_to_database(products, 'Mitra10')
        
        self.assertTrue(result)
        self.assertEqual(Mitra10Product.objects.count(), 1)
        product = Mitra10Product.objects.first()
        self.assertEqual(product.name, 'Cat Tembok')
        self.assertEqual(product.price, 95000)
        self.assertIsNotNone(product.category)
    
    def test_save_juragan_material_with_location(self):
        products = [
            MockProduct('Pasir Bangunan', 350000, 'https://juragan.com/pasir', 'm3', 'Jakarta')
        ]
        
        result = _save_products_to_database(products, 'Juragan Material')
        
        self.assertTrue(result)
        self.assertEqual(JuraganMaterialProduct.objects.count(), 1)
        product = JuraganMaterialProduct.objects.first()
        self.assertEqual(product.name, 'Pasir Bangunan')
        self.assertEqual(product.location, 'Jakarta')
    
    def test_save_juragan_material_without_location_uses_default(self):
        product = MockProduct('Batu Split', 400000, 'https://juragan.com/batu', 'm3')
        products = [product]
        
        result = _save_products_to_database(products, 'Juragan Material')
        
        self.assertTrue(result)
        product_db = JuraganMaterialProduct.objects.first()
        self.assertEqual(product_db.location, 'Unknown')
    
    def test_save_unknown_vendor_returns_true(self):
        products = [
            MockProduct('Product', 10000, 'https://test.com', 'pcs')
        ]
        
        result = _save_products_to_database(products, 'Unknown Vendor')
        
        self.assertTrue(result)
        self.assertEqual(GemilangProduct.objects.count(), 0)
    
    def test_save_empty_products_returns_false(self):
        result = _save_products_to_database([], 'Gemilang Store')
        self.assertFalse(result)
    
    def test_update_existing_gemilang_product(self):
        GemilangProduct.objects.create(
            name='Semen Portland',
            price=75000,
            url='https://gemilang.com/semen',
            unit='sak'
        )
        
        products = [
            MockProduct('Semen Portland', 78000, 'https://gemilang.com/semen', 'sak')
        ]
        
        result = _save_products_to_database(products, 'Gemilang Store')
        
        self.assertTrue(result)
        self.assertEqual(GemilangProduct.objects.count(), 1)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.price, 78000)
    
    def test_update_existing_mitra10_product(self):
        Mitra10Product.objects.create(
            name='Cat Tembok',
            price=95000,
            url='https://mitra10.com/cat',
            unit='kaleng',
            category='Cat'
        )
        
        products = [
            MockProduct('Cat Tembok', 100000, 'https://mitra10.com/cat', 'kaleng')
        ]
        
        result = _save_products_to_database(products, 'Mitra10')
        
        self.assertTrue(result)
        product = Mitra10Product.objects.first()
        self.assertEqual(product.price, 100000)
    
    def test_multiple_products_saved_in_batch(self):
        products = [
            MockProduct('Product 1', 10000, 'https://gemilang.com/1', 'pcs'),
            MockProduct('Product 2', 20000, 'https://gemilang.com/2', 'pcs'),
            MockProduct('Product 3', 30000, 'https://gemilang.com/3', 'pcs'),
        ]
        
        result = _save_products_to_database(products, 'Gemilang Store')
        
        self.assertTrue(result)
        self.assertEqual(GemilangProduct.objects.count(), 3)
    
    def test_mitra10_category_required(self):
        products = [
            MockProduct('Paku Beton', 25000, 'https://mitra10.com/paku', 'kg')
        ]
        
        result = _save_products_to_database(products, 'Mitra10')
        
        self.assertTrue(result)
        product = Mitra10Product.objects.first()
        self.assertIsNotNone(product.category)
    
    def test_juragan_location_required(self):
        products = [
            MockProduct('Besi Beton', 85000, 'https://juragan.com/besi', 'batang', 'Bandung')
        ]
        
        result = _save_products_to_database(products, 'Juragan Material')
        
        self.assertTrue(result)
        product = JuraganMaterialProduct.objects.first()
        self.assertEqual(product.location, 'Bandung')


class DatabaseHelperFunctionsTests(TestCase):
    """Test the refactored database helper functions"""
    
    def test_get_database_service_gemilang(self):
        from dashboard.views import _get_database_service
        service = _get_database_service('Gemilang Store')
        self.assertIsNotNone(service)
        self.assertEqual(service.__class__.__name__, 'GemilangDatabaseService')
    
    def test_get_database_service_mitra10(self):
        from dashboard.views import _get_database_service
        service = _get_database_service('Mitra10')
        self.assertIsNotNone(service)
        self.assertEqual(service.__class__.__name__, 'Mitra10DatabaseService')
    
    def test_get_database_service_juragan(self):
        from dashboard.views import _get_database_service
        service = _get_database_service('Juragan Material')
        self.assertIsNotNone(service)
        self.assertEqual(service.__class__.__name__, 'JuraganMaterialDatabaseService')
    
    def test_get_database_service_unknown(self):
        from dashboard.views import _get_database_service
        service = _get_database_service('Unknown Vendor')
        self.assertIsNone(service)
    
    def test_format_product_data_basic(self):
        from dashboard.views import _format_product_data
        from db_pricing.categorization import ProductCategorizer
        
        product = MockProduct('Test Product', 10000, 'https://test.com', 'pcs')
        categorizer = ProductCategorizer()
        
        result = _format_product_data(product, 'Gemilang Store', categorizer)
        
        self.assertEqual(result['name'], 'Test Product')
        self.assertEqual(result['price'], 10000)
        self.assertEqual(result['url'], 'https://test.com')
        self.assertEqual(result['unit'], 'pcs')
        self.assertNotIn('category', result)
        self.assertNotIn('location', result)
    
    def test_format_product_data_with_category(self):
        from dashboard.views import _format_product_data
        from db_pricing.categorization import ProductCategorizer
        
        product = MockProduct('Cat Tembok', 50000, 'https://test.com', 'kaleng')
        categorizer = ProductCategorizer()
        
        result = _format_product_data(product, 'Mitra10', categorizer)
        
        self.assertIn('category', result)
        self.assertIsNotNone(result['category'])
    
    def test_format_product_data_with_location(self):
        from dashboard.views import _format_product_data
        from db_pricing.categorization import ProductCategorizer
        
        product = MockProduct('Pasir', 300000, 'https://test.com', 'm3', 'Jakarta')
        categorizer = ProductCategorizer()
        
        result = _format_product_data(product, 'Juragan Material', categorizer)
        
        self.assertIn('location', result)
        self.assertEqual(result['location'], 'Jakarta')
