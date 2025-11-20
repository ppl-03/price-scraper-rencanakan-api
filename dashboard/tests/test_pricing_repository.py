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
