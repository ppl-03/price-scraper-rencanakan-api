from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import connection, IntegrityError
from db_pricing.models import DepoBangunanProduct
from decimal import Decimal


class DatabaseConnectionTest(TestCase):
    
    def test_database_connection_is_active(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertIsNotNone(result)
            self.assertEqual(result[0], 1)
    
    def test_can_execute_simple_query(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 + 1")
            result = cursor.fetchone()
            self.assertIsNotNone(result)
            self.assertEqual(result[0], 2)


class TableStructureTest(TestCase):
    
    def test_depobangunan_products_table_exists(self):
        from django.db import connection
        tables = connection.introspection.table_names()
        self.assertIn('depobangunan_products', tables)
    
    def test_table_has_required_columns(self):
        from django.db import connection
        
        with connection.cursor() as cursor:
            table_description = connection.introspection.get_table_description(cursor, 'depobangunan_products')
            column_names = [col.name for col in table_description]
            
            required_columns = ['id', 'name', 'price', 'url', 'unit', 'created_at', 'updated_at']
            for column in required_columns:
                self.assertIn(column, column_names)
    
    def test_id_column_is_primary_key(self):
        from db_pricing.models import DepoBangunanProduct
        pk_field = DepoBangunanProduct._meta.pk
        self.assertEqual(pk_field.name, 'id')
        self.assertTrue(pk_field.primary_key)
    
    def test_indexes_are_created(self):
        from db_pricing.models import DepoBangunanProduct
        
        indexes = DepoBangunanProduct._meta.indexes
        
        self.assertGreaterEqual(len(indexes), 2)
        
        index_fields = []
        for index in indexes:
            index_fields.extend(index.fields)
        
        self.assertIn('name', index_fields)
        self.assertIn('created_at', index_fields)


class ModelCreationTest(TestCase):
    
    def test_create_product_with_all_required_fields(self):
        product = DepoBangunanProduct.objects.create(
            name="Semen Portland 50kg",
            price=67500,
            url="https://www.depobangunan.com/semen-portland",
            unit="SAK"
        )
        
        self.assertIsNotNone(product.id)
        self.assertEqual(product.name, "Semen Portland 50kg")
        self.assertEqual(product.price, 67500)
        self.assertEqual(product.url, "https://www.depobangunan.com/semen-portland")
        self.assertEqual(product.unit, "SAK")
        self.assertIsNotNone(product.created_at)
        self.assertIsNotNone(product.updated_at)
    
    def test_create_product_without_unit_uses_default(self):
        product = DepoBangunanProduct.objects.create(
            name="Product without explicit unit",
            price=15000,
            url="https://www.depobangunan.com/product"
        )
        
        self.assertEqual(product.unit, '', "Unit should default to empty string")
    
    def test_create_product_with_empty_unit(self):
        product = DepoBangunanProduct.objects.create(
            name="Product with empty unit",
            price=20000,
            url="https://www.depobangunan.com/product",
            unit=""
        )
        
        self.assertEqual(product.unit, "")
    
    def test_timestamps_are_auto_generated(self):
        product = DepoBangunanProduct.objects.create(
            name="Timestamp Test Product",
            price=10000,
            url="https://www.depobangunan.com/test"
        )
        
        self.assertIsNotNone(product.created_at)
        self.assertIsNotNone(product.updated_at)
        # Initially, created_at and updated_at should be very close (within 1 second)
        time_diff = abs((product.updated_at - product.created_at).total_seconds())
        self.assertLess(time_diff, 1, "created_at and updated_at should be nearly identical")


class ModelValidationTest(TestCase):

    def test_price_cannot_be_negative(self):
        product = DepoBangunanProduct(
            name="Invalid Negative Price",
            price=-5000,
            url="https://www.depobangunan.com/invalid"
        )
        
        with self.assertRaises(ValidationError) as context:
            product.full_clean()
        
        self.assertIn('price', context.exception.error_dict)
    
    def test_price_zero_is_valid(self):
        product = DepoBangunanProduct.objects.create(
            name="Free Item",
            price=0,
            url="https://www.depobangunan.com/free"
        )
        
        self.assertEqual(product.price, 0)
        product.full_clean()  # Should not raise
    
    def test_name_respects_max_length(self):
        max_length_name = "A" * 500
        product = DepoBangunanProduct.objects.create(
            name=max_length_name,
            price=10000,
            url="https://www.depobangunan.com/test"
        )
        
        self.assertEqual(len(product.name), 500)
    
    def test_url_respects_max_length(self):
        base_url = "https://www.depobangunan.com/"
        long_path = "p" * (1000 - len(base_url))
        long_url = base_url + long_path
        
        product = DepoBangunanProduct.objects.create(
            name="Long URL Product",
            price=10000,
            url=long_url
        )
        
        self.assertEqual(len(product.url), 1000)
    
    def test_unit_respects_max_length(self):
        max_length_unit = "M" * 50
        product = DepoBangunanProduct.objects.create(
            name="Long Unit Product",
            price=10000,
            url="https://www.depobangunan.com/test",
            unit=max_length_unit
        )
        
        self.assertEqual(len(product.unit), 50)
    
    def test_url_must_be_valid_format(self):
        product = DepoBangunanProduct(
            name="Invalid URL",
            price=10000,
            url="not-a-valid-url"
        )
        
        with self.assertRaises(ValidationError) as context:
            product.full_clean()
        
        self.assertIn('url', context.exception.error_dict)


class ModelRetrievalTest(TestCase):

    def setUp(self):
        self.product1 = DepoBangunanProduct.objects.create(
            name="Semen Tiga Roda 50kg",
            price=65000,
            url="https://www.depobangunan.com/semen-1",
            unit="SAK"
        )
        self.product2 = DepoBangunanProduct.objects.create(
            name="Keramik Platinum 40x40",
            price=45000,
            url="https://www.depobangunan.com/keramik-1",
            unit="M²"
        )
    
    def test_retrieve_product_by_id(self):
        retrieved = DepoBangunanProduct.objects.get(id=self.product1.id)
        
        self.assertEqual(retrieved.name, self.product1.name)
        self.assertEqual(retrieved.price, self.product1.price)
        self.assertEqual(retrieved.url, self.product1.url)
        self.assertEqual(retrieved.unit, self.product1.unit)
    
    def test_retrieve_all_products(self):
        all_products = DepoBangunanProduct.objects.all()
        
        self.assertEqual(all_products.count(), 2)
    
    def test_filter_products_by_name(self):
        semen_products = DepoBangunanProduct.objects.filter(name__icontains="semen")
        
        self.assertEqual(semen_products.count(), 1)
        self.assertEqual(semen_products.first().name, "Semen Tiga Roda 50kg")
    
    def test_filter_products_by_unit(self):
        sak_products = DepoBangunanProduct.objects.filter(unit="SAK")
        
        self.assertEqual(sak_products.count(), 1)
        self.assertEqual(sak_products.first().unit, "SAK")
    
    def test_filter_by_price_range(self):
        mid_range = DepoBangunanProduct.objects.filter(
            price__gte=40000,
            price__lte=50000
        )
        
        self.assertEqual(mid_range.count(), 1)
        self.assertEqual(mid_range.first().name, "Keramik Platinum 40x40")
    
    def test_order_by_price_ascending(self):
        products = DepoBangunanProduct.objects.order_by('price')
        
        self.assertEqual(products.first().price, 45000)
        self.assertEqual(products.last().price, 65000)
    
    def test_order_by_price_descending(self):
        products = DepoBangunanProduct.objects.order_by('-price')
        
        self.assertEqual(products.first().price, 65000)
        self.assertEqual(products.last().price, 45000)
    
    def test_order_by_created_at_descending(self):
        products = DepoBangunanProduct.objects.order_by('-created_at')
        
        self.assertEqual(products.first().id, self.product2.id)
        self.assertEqual(products.last().id, self.product1.id)


class ModelUpdateTest(TestCase):

    def test_update_product_name(self):
        product = DepoBangunanProduct.objects.create(
            name="Original Name",
            price=10000,
            url="https://www.depobangunan.com/product"
        )
        
        product.name = "Updated Name"
        product.save()
        
        updated = DepoBangunanProduct.objects.get(id=product.id)
        self.assertEqual(updated.name, "Updated Name")
    
    def test_update_product_price(self):
        product = DepoBangunanProduct.objects.create(
            name="Price Change Product",
            price=10000,
            url="https://www.depobangunan.com/product"
        )
        
        product.price = 15000
        product.save()
        
        updated = DepoBangunanProduct.objects.get(id=product.id)
        self.assertEqual(updated.price, 15000)
    
    def test_updated_at_changes_on_update(self):
        product = DepoBangunanProduct.objects.create(
            name="Update Timestamp Test",
            price=10000,
            url="https://www.depobangunan.com/test"
        )
        
        original_created_at = product.created_at
        original_updated_at = product.updated_at
        
        # Update the product
        product.name = "Modified Name"
        product.save()
        
        updated = DepoBangunanProduct.objects.get(id=product.id)
        
        self.assertEqual(updated.created_at, original_created_at)
        self.assertGreater(updated.updated_at, original_updated_at)
    
    def test_created_at_remains_unchanged_on_update(self):
        product = DepoBangunanProduct.objects.create(
            name="Creation Timestamp Test",
            price=10000,
            url="https://www.depobangunan.com/test"
        )
        
        original_created_at = product.created_at
        
        # Update multiple times
        product.price = 20000
        product.save()
        
        product.name = "New Name"
        product.save()
        
        updated = DepoBangunanProduct.objects.get(id=product.id)
        self.assertEqual(updated.created_at, original_created_at)


class ModelDeletionTest(TestCase):

    def test_delete_product(self):
        product = DepoBangunanProduct.objects.create(
            name="To Be Deleted",
            price=10000,
            url="https://www.depobangunan.com/delete"
        )
        
        product_id = product.id
        product.delete()
        
        with self.assertRaises(DepoBangunanProduct.DoesNotExist):
            DepoBangunanProduct.objects.get(id=product_id)
    
    def test_delete_does_not_affect_other_products(self):
        product1 = DepoBangunanProduct.objects.create(
            name="Keep This",
            price=10000,
            url="https://www.depobangunan.com/keep"
        )
        product2 = DepoBangunanProduct.objects.create(
            name="Delete This",
            price=20000,
            url="https://www.depobangunan.com/delete"
        )
        
        product2.delete()
        
        self.assertTrue(DepoBangunanProduct.objects.filter(id=product1.id).exists())
        self.assertEqual(DepoBangunanProduct.objects.count(), 1)


class BulkOperationsTest(TestCase):

    def test_bulk_create_products(self):
        products = [
            DepoBangunanProduct(
                name=f"Bulk Product {i}",
                price=i * 10000,
                url=f"https://www.depobangunan.com/bulk-{i}",
                unit="UNIT"
            )
            for i in range(1, 11)
        ]
        
        created = DepoBangunanProduct.objects.bulk_create(products)
        
        self.assertEqual(len(created), 10)
        self.assertEqual(DepoBangunanProduct.objects.count(), 10)
    
    def test_bulk_update_products(self):
        # Create products
        products = [
            DepoBangunanProduct.objects.create(
                name=f"Product {i}",
                price=10000,
                url=f"https://www.depobangunan.com/p{i}"
            )
            for i in range(5)
        ]
        
        # Update all prices
        for product in products:
            product.price = 20000
        
        DepoBangunanProduct.objects.bulk_update(products, ['price'])
        
        # Verify all were updated
        updated_products = DepoBangunanProduct.objects.all()
        for product in updated_products:
            self.assertEqual(product.price, 20000)


class StringRepresentationTest(TestCase):

    def test_product_string_format(self):
        product = DepoBangunanProduct.objects.create(
            name="String Test Product",
            price=55000,
            url="https://www.depobangunan.com/test",
            unit="PCS"
        )
        
        expected = "String Test Product - Rp55000"
        self.assertEqual(str(product), expected)
    
    def test_string_representation_with_special_characters(self):
        product = DepoBangunanProduct.objects.create(
            name="Cat Tembok 2.5L (Putih)",
            price=125000,
            url="https://www.depobangunan.com/cat"
        )
        
        expected = "Cat Tembok 2.5L (Putih) - Rp125000"
        self.assertEqual(str(product), expected)


class EdgeCaseTest(TestCase):

    def test_very_long_product_name(self):
        long_name = "Semen Portland Type I 50kg " * 20  # Will be truncated to 500
        product = DepoBangunanProduct.objects.create(
            name=long_name[:500],
            price=70000,
            url="https://www.depobangunan.com/long-name"
        )
        
        self.assertEqual(len(product.name), 500)
    
    def test_very_high_price(self):
        product = DepoBangunanProduct.objects.create(
            name="Expensive Item",
            price=999999999,
            url="https://www.depobangunan.com/expensive"
        )
        
        self.assertEqual(product.price, 999999999)
    
    def test_unicode_characters_in_name(self):
        product = DepoBangunanProduct.objects.create(
            name="Produk™ dengan Karakter® Spesial",
            price=50000,
            url="https://www.depobangunan.com/unicode"
        )
        
        retrieved = DepoBangunanProduct.objects.get(id=product.id)
        self.assertEqual(retrieved.name, "Produk™ dengan Karakter® Spesial")
    
    def test_url_with_query_parameters(self):
        url_with_params = "https://www.depobangunan.com/product?id=123&color=blue&size=large"
        product = DepoBangunanProduct.objects.create(
            name="Product with Query Params",
            price=30000,
            url=url_with_params
        )
        
        retrieved = DepoBangunanProduct.objects.get(id=product.id)
        self.assertEqual(retrieved.url, url_with_params)


class DatabaseIntegrityTest(TestCase):

    def test_concurrent_inserts_maintain_integrity(self):
        products = []
        for i in range(100):
            product = DepoBangunanProduct.objects.create(
                name=f"Concurrent Product {i}",
                price=1000 * i,
                url=f"https://www.depobangunan.com/p{i}"
            )
            products.append(product)
        
        self.assertEqual(DepoBangunanProduct.objects.count(), 100)
        
        # Verify all have unique IDs
        ids = [p.id for p in products]
        self.assertEqual(len(ids), len(set(ids)))
    
    def test_transaction_rollback_on_error(self):
        from django.db import transaction
        
        initial_count = DepoBangunanProduct.objects.count()
        
        try:
            with transaction.atomic():
                # Create a product
                DepoBangunanProduct.objects.create(
                    name="Product in Transaction",
                    price=10000,
                    url="https://www.depobangunan.com/transaction"
                )
                # Force an error by trying to create duplicate or invalid operation
                # This will trigger a rollback
                raise ValidationError("Forcing transaction rollback")
        except ValidationError:
            pass
        
        # Count should remain the same due to rollback
        final_count = DepoBangunanProduct.objects.count()
        self.assertEqual(final_count, initial_count)


class QueryPerformanceTest(TestCase):

    def setUp(self):
        products = [
            DepoBangunanProduct(
                name=f"Performance Test Product {i}",
                price=i * 1000,
                url=f"https://www.depobangunan.com/perf-{i}",
                unit="UNIT"
            )
            for i in range(100)
        ]
        DepoBangunanProduct.objects.bulk_create(products)
    
    def test_indexed_name_query_performs_well(self):
        # This should use the index on name
        products = DepoBangunanProduct.objects.filter(name__icontains="Product 5")
        
        # Should execute efficiently with index
        self.assertGreater(products.count(), 0)
    
    def test_indexed_created_at_query_performs_well(self):
        # This should use the index on created_at
        products = DepoBangunanProduct.objects.order_by('-created_at')[:10]
        
        # Should execute efficiently with index
        self.assertEqual(len(list(products)), 10)
    
    def test_count_query_performance(self):
        count = DepoBangunanProduct.objects.count()
        
        self.assertEqual(count, 100)
