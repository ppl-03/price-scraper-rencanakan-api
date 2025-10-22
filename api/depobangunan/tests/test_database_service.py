
from django.test import TestCase
from django.core.exceptions import ValidationError
from db_pricing.models import DepoBangunanProduct
from api.depobangunan.database_service import (
    ProductData,
    DepoBangunanProductRepository,
    ProductQueryService,
    BulkProductService,
    DatabaseHandshakeService,
    DepoBangunanDatabaseService
)
from unittest.mock import patch, MagicMock
from .test_base import MySQLTestCase


class ProductDataTest(TestCase):

    def test_create_valid_product_data(self):
        product_data = ProductData(
            name="Test Product",
            price=10000,
            url="https://www.depobangunan.com/test",
            unit="PCS"
        )
        
        self.assertEqual(product_data.name, "Test Product")
        self.assertEqual(product_data.price, 10000)
        self.assertEqual(product_data.url, "https://www.depobangunan.com/test")
        self.assertEqual(product_data.unit, "PCS")
    
    def test_product_data_with_default_unit(self):
        product_data = ProductData(
            name="Test Product",
            price=10000,
            url="https://www.depobangunan.com/test"
        )
        
        self.assertEqual(product_data.unit, '')
    
    def test_validate_rejects_empty_name(self):
        product_data = ProductData(
            name="",
            price=10000,
            url="https://www.depobangunan.com/test"
        )
        
        with self.assertRaises(ValidationError) as context:
            product_data.validate()
        
        self.assertIn("name cannot be empty", str(context.exception))
    
    def test_validate_rejects_whitespace_only_name(self):
        product_data = ProductData(
            name="   ",
            price=10000,
            url="https://www.depobangunan.com/test"
        )
        
        with self.assertRaises(ValidationError):
            product_data.validate()
    
    def test_validate_rejects_negative_price(self):
        product_data = ProductData(
            name="Test Product",
            price=-5000,
            url="https://www.depobangunan.com/test"
        )
        
        with self.assertRaises(ValidationError) as context:
            product_data.validate()
        
        self.assertIn("price cannot be negative", str(context.exception))
    
    def test_validate_accepts_zero_price(self):
        product_data = ProductData(
            name="Free Product",
            price=0,
            url="https://www.depobangunan.com/test"
        )
        
        # Should not raise
        product_data.validate()
    
    def test_validate_rejects_empty_url(self):
        product_data = ProductData(
            name="Test Product",
            price=10000,
            url=""
        )
        
        with self.assertRaises(ValidationError) as context:
            product_data.validate()
        
        self.assertIn("URL cannot be empty", str(context.exception))
    
    def test_validate_rejects_too_long_name(self):
        product_data = ProductData(
            name="A" * 501,
            price=10000,
            url="https://www.depobangunan.com/test"
        )
        
        with self.assertRaises(ValidationError) as context:
            product_data.validate()
        
        self.assertIn("name exceeds maximum length", str(context.exception))
    
    def test_validate_accepts_max_length_name(self):
        product_data = ProductData(
            name="A" * 500,
            price=10000,
            url="https://www.depobangunan.com/test"
        )
        
        # Should not raise
        product_data.validate()


class ProductRepositoryTest(TestCase):

    def setUp(self):
        self.repository = DepoBangunanProductRepository()
    
    def test_create_product_successfully(self):
        product_data = ProductData(
            name="Repository Test Product",
            price=25000,
            url="https://www.depobangunan.com/repo-test",
            unit="KG"
        )
        
        product = self.repository.create(product_data)
        
        self.assertIsNotNone(product.id)
        self.assertEqual(product.name, "Repository Test Product")
        self.assertEqual(product.price, 25000)
        self.assertEqual(product.unit, "KG")
    
    def test_create_trims_whitespace(self):
        product_data = ProductData(
            name="  Trimmed Product  ",
            price=10000,
            url="  https://www.depobangunan.com/test  ",
            unit="  PCS  "
        )
        
        product = self.repository.create(product_data)
        
        self.assertEqual(product.name, "Trimmed Product")
        self.assertEqual(product.url, "https://www.depobangunan.com/test")
        self.assertEqual(product.unit, "PCS")
    
    def test_get_by_id_returns_product(self):
        # Create a product first
        product_data = ProductData(
            name="Get By ID Test",
            price=15000,
            url="https://www.depobangunan.com/test"
        )
        created = self.repository.create(product_data)
        
        # Retrieve it
        retrieved = self.repository.get_by_id(created.id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, created.id)
        self.assertEqual(retrieved.name, "Get By ID Test")
    
    def test_get_by_id_returns_none_for_nonexistent(self):
        result = self.repository.get_by_id(99999)
        
        self.assertIsNone(result)
    
    def test_update_product_successfully(self):
        # Create product
        product_data = ProductData(
            name="Original Name",
            price=10000,
            url="https://www.depobangunan.com/original"
        )
        product = self.repository.create(product_data)
        
        # Update it
        updated_data = ProductData(
            name="Updated Name",
            price=20000,
            url="https://www.depobangunan.com/updated",
            unit="NEW"
        )
        updated = self.repository.update(product.id, updated_data)
        
        self.assertEqual(updated.id, product.id)
        self.assertEqual(updated.name, "Updated Name")
        self.assertEqual(updated.price, 20000)
        self.assertEqual(updated.unit, "NEW")
    
    def test_update_nonexistent_raises_exception(self):
        product_data = ProductData(
            name="Test",
            price=10000,
            url="https://www.depobangunan.com/test"
        )
        
        with self.assertRaises(DepoBangunanProduct.DoesNotExist):
            self.repository.update(99999, product_data)
    
    def test_delete_product_successfully(self):
        # Create product
        product_data = ProductData(
            name="To Be Deleted",
            price=10000,
            url="https://www.depobangunan.com/delete"
        )
        product = self.repository.create(product_data)
        
        # Delete it
        result = self.repository.delete(product.id)
        
        self.assertTrue(result)
        self.assertIsNone(self.repository.get_by_id(product.id))
    
    def test_delete_nonexistent_returns_false(self):
        result = self.repository.delete(99999)
        
        self.assertFalse(result)
    
    def test_get_all_returns_all_products(self):
        # Create multiple products
        for i in range(5):
            product_data = ProductData(
                name=f"Product {i}",
                price=i * 1000,
                url=f"https://www.depobangunan.com/p{i}"
            )
            self.repository.create(product_data)
        
        all_products = self.repository.get_all()
        
        self.assertEqual(len(all_products), 5)


class ProductQueryServiceTest(TestCase):

    def setUp(self):
        self.service = ProductQueryService()
        
        # Create test products
        DepoBangunanProduct.objects.create(
            name="Semen Portland 50kg",
            price=67500,
            url="https://www.depobangunan.com/semen",
            unit="SAK"
        )
        DepoBangunanProduct.objects.create(
            name="Keramik 40x40",
            price=45000,
            url="https://www.depobangunan.com/keramik",
            unit="M²"
        )
        DepoBangunanProduct.objects.create(
            name="Cat Tembok 5L",
            price=125000,
            url="https://www.depobangunan.com/cat",
            unit="LITER"
        )
    
    def test_filter_by_name_finds_matches(self):
        results = self.service.filter_by_name("semen")
        
        self.assertEqual(len(results), 1)
        self.assertIn("Semen", results[0].name)
    
    def test_filter_by_name_case_insensitive(self):
        results = self.service.filter_by_name("SEMEN")
        
        self.assertEqual(len(results), 1)
    
    def test_filter_by_name_returns_empty_for_no_match(self):
        results = self.service.filter_by_name("nonexistent")
        
        self.assertEqual(len(results), 0)
    
    def test_filter_by_name_handles_empty_keyword(self):
        results = self.service.filter_by_name("")
        
        self.assertEqual(len(results), 0)
    
    def test_filter_by_price_range_both_bounds(self):
        results = self.service.filter_by_price_range(40000, 70000)
        
        self.assertEqual(len(results), 2)  # Semen and Keramik
    
    def test_filter_by_price_range_min_only(self):
        results = self.service.filter_by_price_range(min_price=50000)
        
        self.assertEqual(len(results), 2)  # Semen and Cat
    
    def test_filter_by_price_range_max_only(self):
        results = self.service.filter_by_price_range(max_price=50000)
        
        self.assertEqual(len(results), 1)  # Keramik
    
    def test_filter_by_unit(self):
        results = self.service.filter_by_unit("SAK")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].unit, "SAK")
    
    def test_get_recent_products_respects_limit(self):
        results = self.service.get_recent_products(limit=2)
        
        self.assertEqual(len(results), 2)
    
    def test_get_recent_products_orders_by_created_at(self):
        results = self.service.get_recent_products(limit=3)
        
        # Should be in descending order (newest first)
        self.assertEqual(results[0].name, "Cat Tembok 5L")
        self.assertEqual(results[-1].name, "Semen Portland 50kg")
    
    def test_search_products_with_multiple_filters(self):
        results = self.service.search_products(
            keyword="Semen",
            min_price=60000,
            max_price=70000,
            unit="SAK"
        )
        
        self.assertEqual(len(results), 1)
        self.assertIn("Semen", results[0].name)
    
    def test_search_products_with_no_filters_returns_all(self):
        results = self.service.search_products()
        
        self.assertEqual(len(results), 3)


class BulkProductServiceTest(TestCase):

    def setUp(self):
        repository = DepoBangunanProductRepository()
        self.service = BulkProductService(repository)
    
    def test_bulk_create_creates_multiple_products(self):
        products_data = [
            ProductData(
                name=f"Bulk Product {i}",
                price=i * 1000,
                url=f"https://www.depobangunan.com/bulk-{i}",
                unit="UNIT"
            )
            for i in range(5)
        ]
        
        created = self.service.bulk_create(products_data)
        
        self.assertEqual(len(created), 5)
        self.assertEqual(DepoBangunanProduct.objects.count(), 5)
    
    def test_bulk_create_validates_all_data_first(self):
        products_data = [
            ProductData(name="Valid", price=1000, url="https://test.com"),
            ProductData(name="Invalid", price=-1000, url="https://test.com"),  # Invalid
        ]
        
        with self.assertRaises(ValidationError):
            self.service.bulk_create(products_data)
        
        # No products should be created due to validation failure
        self.assertEqual(DepoBangunanProduct.objects.count(), 0)
    
    def test_bulk_update_prices_updates_multiple(self):
        # Create products
        products = [
            DepoBangunanProduct.objects.create(
                name=f"Product {i}",
                price=10000,
                url=f"https://www.depobangunan.com/p{i}"
            )
            for i in range(3)
        ]
        
        product_ids = [p.id for p in products]
        
        # Bulk update
        updated_count = self.service.bulk_update_prices(product_ids, 25000)
        
        self.assertEqual(updated_count, 3)
        
        # Verify all were updated
        for product_id in product_ids:
            product = DepoBangunanProduct.objects.get(id=product_id)
            self.assertEqual(product.price, 25000)
    
    def test_bulk_update_prices_rejects_negative(self):
        with self.assertRaises(ValidationError):
            self.service.bulk_update_prices([1, 2, 3], -1000)
    
    def test_bulk_delete_removes_multiple(self):
        # Create products
        products = [
            DepoBangunanProduct.objects.create(
                name=f"To Delete {i}",
                price=10000,
                url=f"https://www.depobangunan.com/del{i}"
            )
            for i in range(4)
        ]
        
        product_ids = [p.id for p in products]
        
        # Bulk delete
        deleted_count = self.service.bulk_delete(product_ids)
        
        self.assertEqual(deleted_count, 4)
        self.assertEqual(DepoBangunanProduct.objects.count(), 0)


class DatabaseHandshakeServiceTest(TestCase):

    def setUp(self):
        self.service = DatabaseHandshakeService()
    
    def test_create_product_creates_successfully(self):
        product = self.service.create_product(
            name="Handshake Product",
            price=35000,
            url="https://www.depobangunan.com/handshake",
            unit="BOX"
        )
        
        self.assertIsNotNone(product.id)
        self.assertEqual(product.name, "Handshake Product")
        self.assertEqual(product.price, 35000)
        self.assertEqual(product.unit, "BOX")
    
    def test_get_product_retrieves_successfully(self):
        created = self.service.create_product(
            name="Get Test",
            price=10000,
            url="https://www.depobangunan.com/get"
        )
        
        retrieved = self.service.get_product(created.id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, created.id)
    
    def test_update_product_updates_successfully(self):
        created = self.service.create_product(
            name="Original",
            price=10000,
            url="https://www.depobangunan.com/original"
        )
        
        updated = self.service.update_product(
            created.id,
            name="Updated",
            price=20000,
            url="https://www.depobangunan.com/updated",
            unit="NEW"
        )
        
        self.assertEqual(updated.name, "Updated")
        self.assertEqual(updated.price, 20000)
    
    def test_delete_product_deletes_successfully(self):
        created = self.service.create_product(
            name="Delete Test",
            price=10000,
            url="https://www.depobangunan.com/delete"
        )
        
        result = self.service.delete_product(created.id)
        
        self.assertTrue(result)
        self.assertIsNone(self.service.get_product(created.id))
    
    def test_search_by_keyword_finds_products(self):
        self.service.create_product(
            name="Searchable Product",
            price=10000,
            url="https://www.depobangunan.com/search"
        )
        
        results = self.service.search_by_keyword("Searchable")
        
        self.assertEqual(len(results), 1)
    
    def test_get_all_products_returns_all(self):
        for i in range(3):
            self.service.create_product(
                name=f"Product {i}",
                price=i * 1000,
                url=f"https://www.depobangunan.com/p{i}"
            )
        
        all_products = self.service.get_all_products()
        
        self.assertEqual(len(all_products), 3)
    
    def test_verify_connection_returns_success(self):
        result = self.service.verify_connection()
        
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['connected'])
    
    def test_get_statistics_returns_correct_data(self):
        # Create test products with known prices
        self.service.create_product("P1", 10000, "https://test.com/1")
        self.service.create_product("P2", 20000, "https://test.com/2")
        self.service.create_product("P3", 30000, "https://test.com/3")
        
        stats = self.service.get_statistics()
        
        self.assertEqual(stats['total_products'], 3)
        self.assertEqual(stats['min_price'], 10000)
        self.assertEqual(stats['max_price'], 30000)
        self.assertEqual(stats['avg_price'], 20000.0)
    
    def test_get_statistics_handles_empty_database(self):
        stats = self.service.get_statistics()
        
        self.assertEqual(stats['total_products'], 0)
        self.assertEqual(stats['avg_price'], 0)


class DatabaseServiceExtraTests(TestCase):

    def test_repository_create_raises_validation_error(self):
        repo = DepoBangunanProductRepository()
        invalid = ProductData(name='', price=100, url='https://x')

        with self.assertRaises(ValidationError):
            repo.create(invalid)

    def test_repository_create_handles_unexpected_exception(self):
        repo = DepoBangunanProductRepository()
        valid = ProductData(name='OK', price=100, url='https://x')

        # Force the underlying ORM create to raise an exception
        with patch('db_pricing.models.DepoBangunanProduct.objects.create', side_effect=Exception('db error')):
            with self.assertRaises(Exception) as cm:
                repo.create(valid)

            self.assertIn('db error', str(cm.exception))

    def test_verify_connection_failure_returns_error(self):
        service = DatabaseHandshakeService()

        # Make cursor.__enter__ raise so the try block goes to except
        with patch('django.db.connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.__enter__.side_effect = Exception('conn fail')
            mock_conn.cursor.return_value = mock_cursor

            result = service.verify_connection()

            self.assertEqual(result['status'], 'error')
            self.assertFalse(result['connected'])

    def test_get_statistics_handles_exception(self):
        service = DatabaseHandshakeService()

        # Force the count() call to raise
        with patch('db_pricing.models.DepoBangunanProduct.objects.count', side_effect=Exception('count fail')):
            result = service.get_statistics()

            # Should return a safe error structure
            self.assertEqual(result.get('total_products'), 0)
            self.assertIn('error', result)

    def test_show_all_tables_success_and_check_table_exists(self):
        service = DatabaseHandshakeService()

        with patch('django.db.connection') as mock_conn:
            mock_cursor = MagicMock()
            # show_all_tables -> fetchall
            mock_cursor.__enter__.return_value.fetchall.return_value = [('tab1',), ('tab2',)]
            # check_table_exists -> fetchone
            mock_cursor.__enter__.return_value.fetchone.return_value = ('tab1',)

            mock_conn.cursor.return_value = mock_cursor
            mock_conn.settings_dict = {'NAME': 'testdb'}

            show_res = service.show_all_tables()
            self.assertEqual(show_res['status'], 'success')
            self.assertEqual(show_res['total_tables'], 2)
            self.assertIn('tab1', show_res['tables'])

            exists_res = service.check_table_exists('tab1')
            self.assertEqual(exists_res['status'], 'success')
            self.assertTrue(exists_res['exists'])

    def test_check_table_exists_handles_no_table(self):
        service = DatabaseHandshakeService()

        with patch('django.db.connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.__enter__.return_value.fetchone.return_value = None
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.settings_dict = {'NAME': 'testdb'}

            res = service.check_table_exists('notable')
            self.assertEqual(res['status'], 'success')
            self.assertFalse(res['exists'])

    def test_productdata_validation_messages(self):
        # Exact message for empty name
        pd_empty = ProductData(name='', price=10, url='https://x')
        with self.assertRaises(ValidationError) as cm:
            pd_empty.validate()
        self.assertIn('Product name cannot be empty', str(cm.exception))

        # Exact message for negative price
        pd_negative = ProductData(name='A', price=-1, url='https://x')
        with self.assertRaises(ValidationError) as cm2:
            pd_negative.validate()
        self.assertIn('Product price cannot be negative', str(cm2.exception))

    def test_show_all_tables_exception_path(self):
        service = DatabaseHandshakeService()

        with patch('django.db.connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.__enter__.side_effect = Exception('show fail')
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.settings_dict = {'NAME': 'testdb'}

            res = service.show_all_tables()
            self.assertEqual(res['status'], 'error')
            self.assertEqual(res['total_tables'], 0)
            self.assertIn('show fail', res['error'])

    def test_check_table_exists_exception_path(self):
        service = DatabaseHandshakeService()

        with patch('django.db.connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.__enter__.side_effect = Exception('check fail')
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.settings_dict = {'NAME': 'testdb'}

            res = service.check_table_exists('any')
            self.assertEqual(res['status'], 'error')
            self.assertFalse(res['exists'])
            self.assertIn('check fail', res['error'])


class TestDepoBangunanDatabaseServiceSave(MySQLTestCase):
    def test_save_valid_data(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"},
            {"name": "Item 2", "price": 20000, "url": "https://example.com/2", "unit": "box"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 2)
        product = DepoBangunanProduct.objects.get(name="Item 1")
        self.assertEqual(product.price, 10000)
        self.assertEqual(product.url, "https://example.com/1")
        self.assertEqual(product.unit, "pcs")

    def test_save_empty_data(self):
        data = []
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 0)

    def test_save_missing_name_field(self):
        data = [
            {"price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 0)

    def test_save_missing_price_field(self):
        data = [
            {"name": "Item 1", "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 0)

    def test_save_missing_url_field(self):
        data = [
            {"name": "Item 1", "price": 10000, "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 0)

    def test_save_missing_unit_field(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 0)

    def test_save_negative_price(self):
        data = [
            {"name": "Item 1", "price": -100, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 0)

    def test_save_zero_price(self):
        data = [
            {"name": "Item 1", "price": 0, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 1)
        product = DepoBangunanProduct.objects.first()
        self.assertEqual(product.price, 0)

    def test_save_duplicate_data(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"},
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 2)

    def test_save_large_price(self):
        data = [
            {"name": "Item 1", "price": 999999999, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = DepoBangunanProduct.objects.first()
        self.assertEqual(product.price, 999999999)

    def test_save_empty_string_unit(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": ""}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = DepoBangunanProduct.objects.first()
        self.assertEqual(product.unit, "")

    def test_save_long_name(self):
        long_name = "A" * 500
        data = [
            {"name": long_name, "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = DepoBangunanProduct.objects.first()
        self.assertEqual(product.name, long_name)

    def test_save_long_url(self):
        long_url = "https://example.com/" + "x" * 980
        data = [
            {"name": "Item 1", "price": 10000, "url": long_url, "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = DepoBangunanProduct.objects.first()
        self.assertEqual(product.url, long_url)

    def test_save_special_characters_in_name(self):
        data = [
            {"name": "Item @#$% & * () 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = DepoBangunanProduct.objects.first()
        self.assertEqual(product.name, "Item @#$% & * () 1")

    def test_save_price_not_integer(self):
        data = [
            {"name": "Item 1", "price": "10000", "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 0)

    def test_save_multiple_batches(self):
        data1 = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        data2 = [
            {"name": "Item 2", "price": 20000, "url": "https://example.com/2", "unit": "box"}
        ]
        service = DepoBangunanDatabaseService()
        result1 = service.save(data1)
        result2 = service.save(data2)
        self.assertTrue(result1)
        self.assertTrue(result2)
        self.assertEqual(DepoBangunanProduct.objects.count(), 2)

    def test_verify_timestamps_created(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        service.save(data)
        product = DepoBangunanProduct.objects.first()
        self.assertIsNotNone(product.created_at)
        self.assertIsNotNone(product.updated_at)


class TestDepoBangunanDatabaseServiceCoverage(MySQLTestCase):
    
    def test_executemany_called_with_correct_params(self):
        service = DepoBangunanDatabaseService()
        data = [
            {"name": "Product 1", "price": 10000, "url": "https://test1.com", "unit": "PCS"},
            {"name": "Product 2", "price": 20000, "url": "https://test2.com", "unit": "BOX"}
        ]
        
        result = service.save(data)
        self.assertTrue(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 2)


class TestDepoBangunanPriceAnomalyDetection(MySQLTestCase):
    
    def test_save_with_price_update_inserts_new_products(self):
        service = DepoBangunanDatabaseService()
        data = [
            {"name": "Product 1", "price": 10000, "url": "https://test.com/1", "unit": "PCS"},
            {"name": "Product 2", "price": 20000, "url": "https://test.com/2", "unit": "BOX"}
        ]
        
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 2)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(len(result["anomalies"]), 0)
        self.assertEqual(DepoBangunanProduct.objects.count(), 2)
    
    def test_save_with_price_update_updates_existing_without_anomaly(self):
        service = DepoBangunanDatabaseService()
        
        initial_data = [
            {"name": "Product 1", "price": 10000, "url": "https://test.com/1", "unit": "PCS"}
        ]
        service.save(initial_data)
        
        updated_data = [
            {"name": "Product 1", "price": 11000, "url": "https://test.com/1", "unit": "PCS"}
        ]
        result = service.save_with_price_update(updated_data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(result["anomalies"]), 0)
        
        product = DepoBangunanProduct.objects.get(name="Product 1")
        self.assertEqual(product.price, 11000)
    
    def test_save_with_price_update_detects_price_increase_anomaly(self):
        service = DepoBangunanDatabaseService()
        
        initial_data = [
            {"name": "Product 1", "price": 10000, "url": "https://test.com/1", "unit": "PCS"}
        ]
        service.save(initial_data)
        
        updated_data = [
            {"name": "Product 1", "price": 12000, "url": "https://test.com/1", "unit": "PCS"}
        ]
        result = service.save_with_price_update(updated_data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(result["anomalies"]), 1)
        
        anomaly = result["anomalies"][0]
        self.assertEqual(anomaly["name"], "Product 1")
        self.assertEqual(anomaly["old_price"], 10000)
        self.assertEqual(anomaly["new_price"], 12000)
        self.assertEqual(anomaly["change_percent"], 20.0)
    
    def test_save_with_price_update_detects_price_decrease_anomaly(self):
        service = DepoBangunanDatabaseService()
        
        initial_data = [
            {"name": "Product 1", "price": 10000, "url": "https://test.com/1", "unit": "PCS"}
        ]
        service.save(initial_data)
        
        updated_data = [
            {"name": "Product 1", "price": 8000, "url": "https://test.com/1", "unit": "PCS"}
        ]
        result = service.save_with_price_update(updated_data)
        
        self.assertTrue(result["success"])
        self.assertEqual(len(result["anomalies"]), 1)
        
        anomaly = result["anomalies"][0]
        self.assertEqual(anomaly["change_percent"], -20.0)
    
    def test_save_with_price_update_no_anomaly_at_14_percent_change(self):
        service = DepoBangunanDatabaseService()
        
        initial_data = [
            {"name": "Product 1", "price": 10000, "url": "https://test.com/1", "unit": "PCS"}
        ]
        service.save(initial_data)
        
        updated_data = [
            {"name": "Product 1", "price": 11400, "url": "https://test.com/1", "unit": "PCS"}
        ]
        result = service.save_with_price_update(updated_data)
        
        self.assertTrue(result["success"])
        self.assertEqual(len(result["anomalies"]), 0)
    
    def test_save_with_price_update_anomaly_at_exactly_15_percent(self):
        service = DepoBangunanDatabaseService()
        
        initial_data = [
            {"name": "Product 1", "price": 10000, "url": "https://test.com/1", "unit": "PCS"}
        ]
        service.save(initial_data)
        
        updated_data = [
            {"name": "Product 1", "price": 11500, "url": "https://test.com/1", "unit": "PCS"}
        ]
        result = service.save_with_price_update(updated_data)
        
        self.assertTrue(result["success"])
        self.assertEqual(len(result["anomalies"]), 1)
        self.assertEqual(result["anomalies"][0]["change_percent"], 15.0)
    
    def test_save_with_price_update_no_anomaly_when_existing_price_is_zero(self):
        service = DepoBangunanDatabaseService()
        
        initial_data = [
            {"name": "Product 1", "price": 0, "url": "https://test.com/1", "unit": "PCS"}
        ]
        service.save(initial_data)
        
        updated_data = [
            {"name": "Product 1", "price": 10000, "url": "https://test.com/1", "unit": "PCS"}
        ]
        result = service.save_with_price_update(updated_data)
        
        self.assertTrue(result["success"])
        self.assertEqual(len(result["anomalies"]), 0)
    
    def test_save_with_price_update_no_update_when_price_unchanged(self):
        service = DepoBangunanDatabaseService()
        
        initial_data = [
            {"name": "Product 1", "price": 10000, "url": "https://test.com/1", "unit": "PCS"}
        ]
        service.save(initial_data)
        
        same_data = [
            {"name": "Product 1", "price": 10000, "url": "https://test.com/1", "unit": "PCS"}
        ]
        result = service.save_with_price_update(same_data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["inserted"], 0)
    
    def test_save_with_price_update_multiple_products_with_mixed_results(self):
        service = DepoBangunanDatabaseService()
        
        initial_data = [
            {"name": "Product 1", "price": 10000, "url": "https://test.com/1", "unit": "PCS"},
            {"name": "Product 2", "price": 20000, "url": "https://test.com/2", "unit": "BOX"}
        ]
        service.save(initial_data)
        
        updated_data = [
            {"name": "Product 1", "price": 12000, "url": "https://test.com/1", "unit": "PCS"},
            {"name": "Product 2", "price": 21000, "url": "https://test.com/2", "unit": "BOX"},
            {"name": "Product 3", "price": 30000, "url": "https://test.com/3", "unit": "UNIT"}
        ]
        result = service.save_with_price_update(updated_data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 2)
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(len(result["anomalies"]), 1)
        self.assertEqual(result["anomalies"][0]["name"], "Product 1")
    
    def test_save_with_price_update_invalid_data_returns_failure(self):
        service = DepoBangunanDatabaseService()
        
        invalid_data = [
            {"name": "Product 1", "price": -1000, "url": "https://test.com/1", "unit": "PCS"}
        ]
        result = service.save_with_price_update(invalid_data)
        
        self.assertFalse(result["success"])
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(len(result["anomalies"]), 0)
