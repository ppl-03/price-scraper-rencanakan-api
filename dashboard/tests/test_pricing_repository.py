from types import SimpleNamespace
from django.test import TestCase
from unittest.mock import patch

from dashboard.repositories.pricing_repository import PricingRepository


class DummyModel:
    def __init__(self, table_name):
        self._meta = SimpleNamespace(db_table=table_name)


class FakeCursor:
    def __init__(self, rows, cols, store):
        # rows: list of tuples
        self._rows = rows
        # description expects sequence of 7-tuples, but driver uses first element as name
        self.description = [(c,) for c in cols]
        self._store = store

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        # store the executed SQL and params for assertions
        self._store['sql'] = sql
        self._store['params'] = list(params or [])

    def fetchall(self):
        return self._rows


class PricingRepositoryTest(TestCase):
    def test_fetch_all_returns_combined_rows_and_params(self):
        # Prepare two dummy models
        m1 = DummyModel('gemilang_products')
        m2 = DummyModel('mitra10_products')

        repo = PricingRepository([(m1, 'Gemilang Store'), (m2, 'Mitra10')])

        # Prepare fake rows (two rows from two vendors)
        cols = ['item', 'value', 'unit', 'url', 'location', 'category', 'created_at', 'updated_at', 'source']
        rows = [
            ("Semen A", 50000, 'sak', 'https://g.example/1', 'Jakarta', 'Bahan', None, None, 'Gemilang Store'),
            ("Pasir Halus", 30000, 'm3', 'https://m10.example/1', 'Bandung', 'Bahan', None, None, 'Mitra10'),
        ]

        store = {}

        with patch('dashboard.repositories.pricing_repository.connection.cursor', return_value=FakeCursor(rows, cols, store)):
            out = repo.fetch_all(per_vendor_limit=5)

        # Ensure returned rows are dicts with expected keys
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]['item'], 'Semen A')
        self.assertEqual(out[1]['source'], 'Mitra10')

        # Verify the SQL params ordering: [source1, limit, source2, limit]
        self.assertIn('params', store)
        self.assertEqual(store['params'], ['Gemilang Store', 5, 'Mitra10', 5])

    def test_fetch_all_handles_no_vendors(self):
        repo = PricingRepository([])
        out = repo.fetch_all(per_vendor_limit=3)
        self.assertEqual(out, [])

    def test_fetch_all_rejects_invalid_per_vendor_limit(self):
        """Test that invalid per_vendor_limit raises ValueError"""
        m1 = DummyModel('test_products')
        repo = PricingRepository([(m1, 'Test')])

        # Test negative limit
        with self.assertRaises(ValueError) as ctx:
            repo.fetch_all(per_vendor_limit=-5)
        self.assertIn("must be a positive integer", str(ctx.exception))

        # Test zero limit
        with self.assertRaises(ValueError) as ctx:
            repo.fetch_all(per_vendor_limit=0)
        self.assertIn("must be a positive integer", str(ctx.exception))

        # Test non-integer limit
        with self.assertRaises(ValueError) as ctx:
            repo.fetch_all(per_vendor_limit="invalid")  # type: ignore
        self.assertIn("must be a positive integer", str(ctx.exception))

    def test_fetch_all_rejects_unsafe_table_name(self):
        """Test that unsafe table names raise ValueError"""
        # Create model with SQL injection attempt in table name
        unsafe_model = DummyModel('products; DROP TABLE users--')
        repo = PricingRepository([(unsafe_model, 'Evil Source')])

        with self.assertRaises(ValueError) as ctx:
            repo.fetch_all(per_vendor_limit=10)
        self.assertIn("Unsafe table name detected", str(ctx.exception))

    def test_fetch_all_handles_missing_table_introspection(self):
        """Test repository works when table introspection fails"""
        m1 = DummyModel('valid_table')
        repo = PricingRepository([(m1, 'Source1')])

        cols = ['item', 'value', 'unit', 'url', 'location', 'category', 'created_at', 'updated_at', 'source']
        rows = [("Product A", 10000, 'pcs', 'https://ex.com/1', 'City', 'Cat', None, None, 'Source1')]
        store = {}

        # Mock introspection to raise exception
        with patch('dashboard.repositories.pricing_repository.connection.introspection.table_names', side_effect=Exception("Introspection error")):
            with patch('dashboard.repositories.pricing_repository.connection.cursor', return_value=FakeCursor(rows, cols, store)):
                out = repo.fetch_all(per_vendor_limit=5)

        # Should still work via fallback
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['item'], 'Product A')

    def test_fetch_all_handles_table_not_in_existing_tables(self):
        """Test repository handles when table is not in introspection results"""
        m1 = DummyModel('virtual_table')
        repo = PricingRepository([(m1, 'VirtualSource')])

        cols = ['item', 'value', 'unit', 'url', 'location', 'category', 'created_at', 'updated_at', 'source']
        rows = [("Virtual Product", 25000, 'unit', 'https://v.com/1', 'Place', 'Type', None, None, 'VirtualSource')]
        store = {}

        # Mock introspection to return list without our table
        with patch('dashboard.repositories.pricing_repository.connection.introspection.table_names', return_value=['other_table', 'another_table']):
            with patch('dashboard.repositories.pricing_repository.connection.cursor', return_value=FakeCursor(rows, cols, store)):
                out = repo.fetch_all(per_vendor_limit=10)

        # Should still work (falls back to regex/quoting validation)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['item'], 'Virtual Product')

    def test_fetch_all_handles_prepared_cursor_exception(self):
        """Test fallback when prepared cursor is not supported"""
        m1 = DummyModel('standard_table')
        repo = PricingRepository([(m1, 'StandardSource')])

        cols = ['item', 'value', 'unit', 'url', 'location', 'category', 'created_at', 'updated_at', 'source']
        rows = [("Standard Product", 15000, 'box', 'https://s.com/1', 'Location', 'Category', None, None, 'StandardSource')]
        store = {}

        def mock_cursor_factory(prepared=None):
            if prepared:
                raise TypeError("prepared argument not supported")
            return FakeCursor(rows, cols, store)

        with patch('dashboard.repositories.pricing_repository.connection.cursor', side_effect=mock_cursor_factory):
            out = repo.fetch_all(per_vendor_limit=8)

        # Should fallback to regular cursor and still work
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['item'], 'Standard Product')
