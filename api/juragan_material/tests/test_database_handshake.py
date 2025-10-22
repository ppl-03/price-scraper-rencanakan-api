from db_pricing.models import JuraganMaterialProduct
from django.core.exceptions import ValidationError
from django.db import connection
from .test_base import MySQLTestCase, get_table_columns, table_exists


class TestJuraganMaterialDatabaseHandshake(MySQLTestCase):
    
    def test_database_connection_exists(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertIsNotNone(result)
            self.assertEqual(result[0], 1)
    
    def test_juragan_material_products_table_exists(self):
        exists = table_exists('juragan_material_products')
        self.assertTrue(exists, "juragan_material_products table should exist")
    
    def test_juragan_material_products_table_has_correct_columns(self):
        column_names = get_table_columns('juragan_material_products')
        
        self.assertIn('id', column_names)
        self.assertIn('name', column_names)
        self.assertIn('price', column_names)
        self.assertIn('url', column_names)
        self.assertIn('unit', column_names)
        self.assertIn('created_at', column_names)
        self.assertIn('updated_at', column_names)


class TestJuraganMaterialProductModel(MySQLTestCase):
    
    def test_create_product_with_all_fields(self):
        product = JuraganMaterialProduct.objects.create(
            name="Test Semen 50kg",
            price=65000,
            url="https://juraganmaterial.id/test",
            unit="KG"
        )
        
        self.assertIsNotNone(product.id)
        self.assertEqual(product.name, "Test Semen 50kg")
        self.assertEqual(product.price, 65000)
        self.assertEqual(product.url, "https://juraganmaterial.id/test")
        self.assertEqual(product.unit, "KG")
        self.assertIsNotNone(product.created_at)
        self.assertIsNotNone(product.updated_at)
    
    def test_create_product_without_unit(self):
        product = JuraganMaterialProduct.objects.create(
            name="Product without unit",
            price=10000,
            url="https://juraganmaterial.id/test"
        )
        
        self.assertIsNotNone(product.id)
        self.assertEqual(product.unit, '')
    
    def test_retrieve_product_by_id(self):
        created_product = JuraganMaterialProduct.objects.create(
            name="Retrievable Product",
            price=30000,
            url="https://juraganmaterial.id/test",
            unit="M²"
        )
        
        retrieved_product = JuraganMaterialProduct.objects.get(id=created_product.id)
        
        self.assertEqual(retrieved_product.name, "Retrievable Product")
        self.assertEqual(retrieved_product.price, 30000)
        self.assertEqual(retrieved_product.unit, "M²")
    
    def test_retrieve_all_products(self):
        JuraganMaterialProduct.objects.create(
            name="Product 1",
            price=1000,
            url="https://juraganmaterial.id/p1",
            unit="KG"
        )
        JuraganMaterialProduct.objects.create(
            name="Product 2",
            price=2000,
            url="https://juraganmaterial.id/p2",
            unit="M"
        )
        
        all_products = JuraganMaterialProduct.objects.all()
        
        self.assertEqual(all_products.count(), 2)
    
    def test_filter_products_by_name(self):
        JuraganMaterialProduct.objects.create(
            name="Semen Portland 50kg",
            price=65000,
            url="https://juraganmaterial.id/semen",
            unit="KG"
        )
        JuraganMaterialProduct.objects.create(
            name="Keramik 40x40",
            price=45000,
            url="https://juraganmaterial.id/keramik",
            unit="M²"
        )
        
        semen_products = JuraganMaterialProduct.objects.filter(name__icontains="semen")
        
        self.assertEqual(semen_products.count(), 1)
        self.assertIn("Semen", semen_products.first().name)
    
    def test_update_product(self):
        product = JuraganMaterialProduct.objects.create(
            name="Original Name",
            price=10000,
            url="https://juraganmaterial.id/test",
            unit="KG"
        )
        
        original_created_at = product.created_at
        
        product.name = "Updated Name"
        product.price = 20000
        product.save()
        
        updated_product = JuraganMaterialProduct.objects.get(id=product.id)
        
        self.assertEqual(updated_product.name, "Updated Name")
        self.assertEqual(updated_product.price, 20000)
        self.assertEqual(updated_product.created_at, original_created_at)
        self.assertNotEqual(updated_product.updated_at, updated_product.created_at)
    
    def test_delete_product(self):
        product = JuraganMaterialProduct.objects.create(
            name="To Delete",
            price=5000,
            url="https://juraganmaterial.id/test",
            unit="LITER"
        )
        
        product_id = product.id
        product.delete()
        
        with self.assertRaises(JuraganMaterialProduct.DoesNotExist):
            JuraganMaterialProduct.objects.get(id=product_id)
    
    def test_product_string_representation(self):
        product = JuraganMaterialProduct.objects.create(
            name="String Test",
            price=15000,
            url="https://juraganmaterial.id/test",
            unit="KG"
        )
        
        expected_string = "String Test - Rp15000"
        self.assertEqual(str(product), expected_string)
    
    def test_product_price_must_be_positive(self):
        product = JuraganMaterialProduct(
            name="Negative Price Test",
            price=-1000,
            url="https://juraganmaterial.id/test",
            unit="KG"
        )
        
        with self.assertRaises(ValidationError):
            product.full_clean()
    
    def test_product_price_zero_is_valid(self):
        product = JuraganMaterialProduct.objects.create(
            name="Zero Price",
            price=0,
            url="https://juraganmaterial.id/test",
            unit="KG"
        )
        
        self.assertEqual(product.price, 0)
    
    def test_product_name_max_length(self):
        long_name = "A" * 500
        product = JuraganMaterialProduct.objects.create(
            name=long_name,
            price=10000,
            url="https://juraganmaterial.id/test",
            unit="KG"
        )
        
        self.assertEqual(len(product.name), 500)
    
    def test_product_url_max_length(self):
        long_url = "https://juraganmaterial.id/" + "a" * 973
        product = JuraganMaterialProduct.objects.create(
            name="Long URL Test",
            price=10000,
            url=long_url,
            unit="KG"
        )
        
        self.assertEqual(len(product.url), 1000)
    
    def test_product_unit_max_length(self):
        long_unit = "M" * 50
        product = JuraganMaterialProduct.objects.create(
            name="Long Unit Test",
            price=10000,
            url="https://juraganmaterial.id/test",
            unit=long_unit
        )
        
        self.assertEqual(len(product.unit), 50)
    
    def test_order_by_created_at_descending(self):
        JuraganMaterialProduct.objects.create(
            name="First Product",
            price=10000,
            url="https://juraganmaterial.id/p1",
            unit="KG"
        )
        JuraganMaterialProduct.objects.create(
            name="Second Product",
            price=20000,
            url="https://juraganmaterial.id/p2",
            unit="M"
        )
        
        recent_products = JuraganMaterialProduct.objects.order_by('-created_at')
        
        self.assertEqual(recent_products.first().name, "Second Product")
        self.assertEqual(recent_products.last().name, "First Product")
    
    def test_filter_by_price_range(self):
        JuraganMaterialProduct.objects.create(name="Cheap", price=1000, url="https://juraganmaterial.id/p1", unit="KG")
        JuraganMaterialProduct.objects.create(name="Medium", price=5000, url="https://juraganmaterial.id/p2", unit="KG")
        JuraganMaterialProduct.objects.create(name="Expensive", price=10000, url="https://juraganmaterial.id/p3", unit="KG")
        
        mid_range = JuraganMaterialProduct.objects.filter(price__gte=2000, price__lte=7000)
        
        self.assertEqual(mid_range.count(), 1)
        self.assertEqual(mid_range.first().name, "Medium")
    
    def test_bulk_create_products(self):
        products = [
            JuraganMaterialProduct(name=f"Product {i}", price=i*1000, url=f"https://juraganmaterial.id/p{i}", unit="KG")
            for i in range(1, 6)
        ]
        
        created_products = JuraganMaterialProduct.objects.bulk_create(products)
        
        self.assertEqual(len(created_products), 5)
        self.assertEqual(JuraganMaterialProduct.objects.count(), 5)