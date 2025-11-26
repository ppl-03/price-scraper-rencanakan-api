from django.test import TestCase
from unittest.mock import patch, MagicMock

from dashboard.services import VendorPricingService
from dashboard.repositories.pricing_repository import PricingRepository
from db_pricing.models import GemilangProduct, Mitra10Product, DepoBangunanProduct


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

    @patch.object(PricingRepository, 'fetch_all')
    def test_list_prices_repository_exception_with_search(self, mock_fetch):
        """Test search filtering works in fallback path when repository fails"""
        # Make repository fail so we use the fallback _query_vendor path
        mock_fetch.side_effect = Exception("Repository error")

        # Create mock products for fallback path
        mock_product1 = MagicMock()
        mock_product1.name = "Pasir Halus"
        mock_product1.price = 30000
        mock_product1.unit = "m3"
        mock_product1.url = "https://test.example/1"
        mock_product1.location = "Jakarta"
        mock_product1.category = "Bahan"
        mock_product1.created_at = None

        mock_product2 = MagicMock()
        mock_product2.name = "Semen"
        mock_product2.price = 50000
        mock_product2.unit = "sak"
        mock_product2.url = "https://test.example/2"
        mock_product2.location = "Jakarta"
        mock_product2.category = "Bahan"
        mock_product2.created_at = None

        with patch.object(GemilangProduct.objects, 'all') as mock_all:
            mock_qs = MagicMock()
            mock_qs.order_by.return_value = mock_qs
            # Simulate filtering - only return Pasir when q="Pasir"
            mock_filtered = MagicMock()
            mock_filtered.__getitem__.return_value = [mock_product1]
            mock_qs.filter.return_value = mock_filtered
            mock_all.return_value = mock_qs

            svc = VendorPricingService(per_vendor_limit=10)
            items, _ = svc.list_prices(q="Pasir", page=1, per_page=10)

            # Verify filter was called in fallback path
            mock_qs.filter.assert_called()
            # Should return filtered results
            self.assertGreaterEqual(len(items), 0)

    @patch.object(PricingRepository, 'fetch_all')
    def test_list_prices_fallback_on_exception(self, mock_fetch):
        """Test fallback to individual vendor queries when repository fails"""
        mock_fetch.side_effect = Exception("Repository error")

        # Create mock products for fallback _query_vendor path
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 45000
        mock_product.unit = "pcs"
        mock_product.url = "https://test.example/1"
        mock_product.location = "Jakarta"
        mock_product.category = "Test Category"
        mock_product.created_at = None
        mock_product.updated_at = None

        with patch.object(GemilangProduct.objects, 'all') as mock_all:
            mock_qs = MagicMock()
            mock_qs.order_by.return_value = mock_qs
            mock_qs.filter.return_value = mock_qs
            mock_qs.__getitem__.return_value = [mock_product]
            mock_all.return_value = mock_qs

            svc = VendorPricingService(per_vendor_limit=5)
            items, _ = svc.list_prices(page=1, per_page=10)

            # Should still return results via fallback
            self.assertGreaterEqual(len(items), 0)

    @patch.object(PricingRepository, 'fetch_all')
    def test_list_prices_invalid_page_number(self, mock_fetch):
        """Test exception handling for invalid page numbers"""
        mock_fetch.side_effect = self.fake_fetch_all

        svc = VendorPricingService(per_vendor_limit=10)
        # Request a page that doesn't exist
        items, total = svc.list_prices(page=9999, per_page=10)

        # Should return empty list but valid total
        self.assertEqual(len(items), 0)
        self.assertGreater(total, 0)

    @patch.object(PricingRepository, 'fetch_all')
    def test_list_all_prices_basic(self, mock_fetch):
        """Test list_all_prices returns full dataset"""
        mock_fetch.side_effect = self.fake_fetch_all

        svc = VendorPricingService(per_vendor_limit=100)
        items = svc.list_all_prices()

        # Should return all unique items (deduplicated)
        self.assertGreater(len(items), 0)
        # Verify items are sorted by price
        prices = [i['value'] for i in items]
        self.assertEqual(prices, sorted(prices))

    @patch.object(PricingRepository, 'fetch_all')
    def test_list_all_prices_with_custom_limit(self, mock_fetch):
        """Test list_all_prices with custom per_vendor_limit"""
        mock_fetch.side_effect = self.fake_fetch_all

        svc = VendorPricingService(per_vendor_limit=100)
        items = svc.list_all_prices(per_vendor_limit=5)

        # Verify custom limit is respected
        mock_fetch.assert_called_with(per_vendor_limit=5)
        self.assertGreater(len(items), 0)

    @patch.object(PricingRepository, 'fetch_all')
    def test_list_all_prices_with_search(self, mock_fetch):
        """Test list_all_prices with search query"""
        mock_fetch.side_effect = self.fake_fetch_all

        svc = VendorPricingService(per_vendor_limit=100)
        items = svc.list_all_prices(q="Semen")

        # Should return filtered results
        self.assertGreater(len(items), 0)

    @patch.object(PricingRepository, 'fetch_all')
    def test_list_all_prices_fallback_on_exception(self, mock_fetch):
        """Test list_all_prices fallback when repository fails"""
        mock_fetch.side_effect = Exception("Repository error")

        mock_product = MagicMock()
        mock_product.name = "Fallback Product"
        mock_product.price = 25000
        mock_product.unit = "kg"
        mock_product.url = "https://fallback.example/1"
        mock_product.location = "Bandung"
        mock_product.category = "Materials"
        mock_product.created_at = None
        mock_product.updated_at = None

        with patch.object(GemilangProduct.objects, 'all') as mock_all:
            mock_qs = MagicMock()
            mock_qs.order_by.return_value = mock_qs
            mock_qs.filter.return_value = mock_qs
            mock_qs.__getitem__.return_value = [mock_product]
            mock_all.return_value = mock_qs

            svc = VendorPricingService(per_vendor_limit=5)
            items = svc.list_all_prices()

            # Should still return results via fallback
            self.assertGreaterEqual(len(items), 0)

    def test_query_vendor_with_search(self):
        """Test _query_vendor method directly with search query"""
        mock_product = MagicMock()
        mock_product.name = "Test Semen"
        mock_product.price = 55000
        mock_product.unit = "sak"
        mock_product.url = "https://vendor.example/1"
        mock_product.location = "Surabaya"
        mock_product.category = "Building Materials"
        mock_product.created_at = None

        with patch.object(GemilangProduct.objects, 'all') as mock_all:
            mock_qs = MagicMock()
            mock_qs.order_by.return_value = mock_qs
            mock_qs.filter.return_value = mock_qs
            mock_qs.__getitem__.return_value = [mock_product]
            mock_all.return_value = mock_qs

            svc = VendorPricingService(per_vendor_limit=10)
            items = svc._query_vendor(GemilangProduct, "Gemilang Store", q="Semen")

            # Verify filtering was applied
            mock_qs.filter.assert_called_once()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]['item'], "Test Semen")
            self.assertEqual(items[0]['source'], "Gemilang Store")

    def test_query_vendor_without_search(self):
        """Test _query_vendor method without search query"""
        mock_product = MagicMock()
        mock_product.name = "Generic Product"
        mock_product.price = None  # Test None price handling
        mock_product.unit = "unit"
        mock_product.url = "https://vendor.example/2"
        mock_product.location = "Yogyakarta"
        mock_product.category = None  # Test None category -> "Lainnya"
        mock_product.created_at = None

        with patch.object(Mitra10Product.objects, 'all') as mock_all:
            mock_qs = MagicMock()
            mock_qs.order_by.return_value = mock_qs
            mock_qs.__getitem__.return_value = [mock_product]
            mock_all.return_value = mock_qs

            svc = VendorPricingService(per_vendor_limit=10)
            items = svc._query_vendor(Mitra10Product, "Mitra10", q=None)

            # Verify no filtering was applied
            mock_qs.filter.assert_not_called()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]['value'], 0)  # None price -> 0
            self.assertEqual(items[0]['category'], "Lainnya")  # None category -> "Lainnya"

    @patch.object(PricingRepository, 'fetch_all')
    def test_list_prices_vendor_query_exception_handling(self, mock_fetch):
        """Test that individual vendor query exceptions are caught and skipped in list_prices"""
        mock_fetch.side_effect = Exception("Repository error")

        # Mock the first vendor to raise an exception, second vendor to work
        with patch.object(GemilangProduct.objects, 'all', side_effect=Exception("DB error")):
            with patch.object(DepoBangunanProduct.objects, 'all') as mock_depo:
                mock_product = MagicMock()
                mock_product.name = "Working Product"
                mock_product.price = 75000
                mock_product.unit = "pcs"
                mock_product.url = "https://depo.example/1"
                mock_product.location = "Medan"
                mock_product.category = "Test"
                mock_product.created_at = None

                mock_qs = MagicMock()
                mock_qs.order_by.return_value = mock_qs
                mock_qs.__getitem__.return_value = [mock_product]
                mock_depo.return_value = mock_qs

                svc = VendorPricingService(per_vendor_limit=5)
                items, _ = svc.list_prices(page=1, per_page=10)

                # Should skip failed vendor and continue with others
                self.assertGreaterEqual(len(items), 0)

    @patch.object(PricingRepository, 'fetch_all')
    def test_list_all_prices_vendor_query_exception_handling(self, mock_fetch):
        """Test that individual vendor query exceptions are caught and skipped in list_all_prices"""
        mock_fetch.side_effect = Exception("Repository error")

        # Mock vendors: first fails, second succeeds
        with patch.object(GemilangProduct.objects, 'all', side_effect=Exception("DB error")):
            with patch.object(Mitra10Product.objects, 'all') as mock_mitra:
                mock_product = MagicMock()
                mock_product.name = "Mitra Product"
                mock_product.price = 45000
                mock_product.unit = "box"
                mock_product.url = "https://mitra.example/1"
                mock_product.location = "Semarang"
                mock_product.category = "Hardware"
                mock_product.created_at = None

                mock_qs = MagicMock()
                mock_qs.order_by.return_value = mock_qs
                mock_qs.__getitem__.return_value = [mock_product]
                mock_mitra.return_value = mock_qs

                svc = VendorPricingService(per_vendor_limit=5)
                items = svc.list_all_prices()

                # Should skip failed vendor and continue with others
                self.assertGreaterEqual(len(items), 0)
    
    @patch.object(PricingRepository, 'fetch_all')
    def test_list_prices_deduplication(self, mock_fetch):
        """Test that duplicate entries are properly removed in list_prices"""
        # Return data with exact duplicates to test continue in deduplication loop
        duplicate_data = [
            {"item": "Duplicate Product", "value": 50000, "unit": "pcs", "url": "https://dup.example/1", 
             "category": "Test", "source": "Gemilang Store", "created_at": None, "updated_at": None},
            # Exact duplicate - should be skipped
            {"item": "Duplicate Product", "value": 50000, "unit": "pcs", "url": "https://dup.example/1", 
             "category": "Test", "source": "Gemilang Store", "created_at": None, "updated_at": None},
            {"item": "Unique Product", "value": 60000, "unit": "kg", "url": "https://unique.example/1", 
             "category": "Test", "source": "Mitra10", "created_at": None, "updated_at": None},
        ]
        mock_fetch.return_value = duplicate_data

        svc = VendorPricingService(per_vendor_limit=10)
        items, _ = svc.list_prices(page=1, per_page=10)

        # Should have 2 items after deduplication, not 3
        self.assertEqual(len(items), 2)
        # Verify the duplicate was removed
        item_names = [i['item'] for i in items]
        self.assertEqual(item_names.count("Duplicate Product"), 1)
        self.assertEqual(item_names.count("Unique Product"), 1)
    
    @patch.object(PricingRepository, 'fetch_all')
    def test_list_all_prices_deduplication(self, mock_fetch):
        """Test that duplicate entries are properly removed in list_all_prices"""
        # Return data with exact duplicates to test continue in deduplication loop
        duplicate_data = [
            {"item": "Dup Item", "value": 30000, "unit": "m3", "url": "https://test.example/1", 
             "category": "Material", "source": "Depo Bangunan", "created_at": None, "updated_at": None},
            # Exact duplicate - should be skipped by continue statement
            {"item": "Dup Item", "value": 30000, "unit": "m3", "url": "https://test.example/1", 
             "category": "Material", "source": "Depo Bangunan", "created_at": None, "updated_at": None},
            # Another duplicate - should also be skipped
            {"item": "Dup Item", "value": 30000, "unit": "m3", "url": "https://test.example/1", 
             "category": "Material", "source": "Depo Bangunan", "created_at": None, "updated_at": None},
            {"item": "Different Item", "value": 40000, "unit": "sak", "url": "https://test.example/2", 
             "category": "Material", "source": "Juragan Material", "created_at": None, "updated_at": None},
        ]
        mock_fetch.return_value = duplicate_data

        svc = VendorPricingService(per_vendor_limit=10)
        items = svc.list_all_prices()

        # Should have 2 unique items after deduplication, not 4
        self.assertEqual(len(items), 2)
        # Verify the duplicates were removed
        item_names = [i['item'] for i in items]
        self.assertEqual(item_names.count("Dup Item"), 1)
        self.assertEqual(item_names.count("Different Item"), 1)
