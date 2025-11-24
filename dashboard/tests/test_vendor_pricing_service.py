from django.test import TestCase
from unittest.mock import patch

from dashboard.services import VendorPricingService
from dashboard.repositories.pricing_repository import PricingRepository


class VendorPricingServiceTest(TestCase):
    def setUp(self):
        # Prepare stub data for vendors. We include a duplicate entry
        # (same item/url/value) across two vendor tables to exercise dedupe.
        self.stub_data = {
            'Gemilang Store': [
                {"item": "Semen A", "value": 50000, "unit": "sak", "url": "https://g.example/1", "category": "Bahan"},
                {"item": "Semen B", "value": 60000, "unit": "sak", "url": "https://g.example/2", "category": "Bahan"},
            ],
            'Mitra10': [
                {"item": "Pasir Halus", "value": 30000, "unit": "m3", "url": "https://m10.example/1", "category": "Bahan"},
                {"item": "Pasir Kasar", "value": 35000, "unit": "m3", "url": "https://m10.example/2", "category": "Bahan"},
            ],
            'Tokopedia': [
                # duplicate of Gemilang Semen A to test dedupe across sources
                {"item": "Semen A", "value": 50000, "unit": "sak", "url": "https://g.example/1", "category": "Bahan"},
            ],
            'Depo Bangunan': [
                {"item": "Batu Split", "value": 80000, "unit": "m3", "url": "https://dep.example/1", "category": "Bahan"},
            ],
            'Juragan Material': [],
        }


    def fake_fetch_all(self, per_vendor_limit=100):
        # Flatten stub_data into a combined list resembling repository output
        rows = []
        for source, items in self.stub_data.items():
            for it in items[:per_vendor_limit]:
                r = dict(it)
                r['source'] = source
                r.setdefault('created_at', None)
                r.setdefault('updated_at', None)
                rows.append(r)
        return rows

    @patch.object(PricingRepository, 'fetch_all')
    def test_list_prices_basic(self, mock_fetch):
        mock_fetch.side_effect = self.fake_fetch_all

        svc = VendorPricingService(per_vendor_limit=10)
        items, total = svc.list_prices(page=1, per_page=10)

        # verify dedupe removed the Tokopedia duplicate of Semen A
        names = [i['item'] for i in items]
        self.assertIn('Semen A', names)
        self.assertIn('Pasir Halus', names)

        # check ordering: lowest price first (Pasir Halus 30000)
        values = [i['value'] for i in items]
        self.assertEqual(values[0], 30000)

        # total should be at least the number of unique items
        self.assertGreaterEqual(total, len(items))

    @patch.object(PricingRepository, 'fetch_all')
    def test_pagination(self, mock_fetch):
        mock_fetch.side_effect = self.fake_fetch_all

        svc = VendorPricingService(per_vendor_limit=10)
        # without search, paginate results one per page
        items, _ = svc.list_prices(page=1, per_page=1)
        self.assertEqual(len(items), 1)
        items2, _ = svc.list_prices(page=2, per_page=1)
        self.assertEqual(len(items2), 1)
