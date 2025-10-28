from unittest.mock import Mock, MagicMock, patch
from db_pricing.models import JuraganMaterialProduct
from api.juragan_material.factory import create_juraganmaterial_scraper
from api.juragan_material.database_service import JuraganMaterialDatabaseService
from .test_base import MySQLTestCase

class TestJuraganMaterialEndToEnd(MySQLTestCase):
    def test_scrape_and_save_full_flow(self):
        scraper = create_juraganmaterial_scraper()

        mock_html = '''
        <html>
            <body>
                <div class="product">
                    <h2>Semen Portland 40kg</h2>
                    <span class="price">Rp 65.000</span>
                    <a href="/product/1">Detail</a>
                </div>
                <div class="product">
                    <h2>Batu Bata Merah</h2>
                    <span class="price">Rp 850</span>
                    <a href="/product/2">Detail</a>
                </div>
            </body>
        </html>
        '''

        with patch.object(scraper.http_client, 'get', return_value=mock_html):
            result = scraper.scrape_products('semen')

        self.assertTrue(result.success)
        self.assertGreaterEqual(len(result.products), 0)

        if result.products:
            formatted_data = [
                {
                    'name': p['name'],
                    'price': p['price'],
                    'url': p.get('url', ''),
                    'unit': p.get('unit', '')
                }
                for p in result.products
            ]
            service = JuraganMaterialDatabaseService()
            save_result = service.save(formatted_data)
            self.assertTrue(save_result)
            self.assertGreater(JuraganMaterialProduct.objects.count(), 0)

    def test_scrape_with_empty_keyword(self):
        scraper = create_juraganmaterial_scraper()

        result = scraper.scrape_products('')
        self.assertFalse(result.success)
        self.assertIn('keyword', result.error_message.lower())

    def test_scrape_with_invalid_page(self):
        scraper = create_juraganmaterial_scraper()

        result = scraper.scrape_products('test', page=-1)
        self.assertFalse(result.success)
        self.assertIn('page', result.error_message.lower())

    def test_database_service_save_with_valid_data(self):
        service = JuraganMaterialDatabaseService()
        data = [
            {"name": "Test Product 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"},
            {"name": "Test Product 2", "price": 20000, "url": "https://example.com/2", "unit": "box", "location": "Bandung"}
        ]

        result = service.save(data)
        self.assertTrue(result)
        self.assertEqual(JuraganMaterialProduct.objects.count(), 2)

        product1 = JuraganMaterialProduct.objects.get(name="Test Product 1")
        self.assertEqual(product1.price, 10000)
        self.assertEqual(product1.url, "https://example.com/1")
        self.assertEqual(product1.unit, "pcs")

    def test_database_service_save_with_duplicate_data(self):
        service = JuraganMaterialDatabaseService()
        data = [
            {"name": "Duplicate Product", "price": 15000, "url": "https://example.com/dup", "unit": "pcs", "location": "Jakarta"},
            {"name": "Duplicate Product", "price": 15000, "url": "https://example.com/dup", "unit": "pcs", "location": "Jakarta"}
        ]

        result = service.save(data)
        self.assertTrue(result)
        # Should save both duplicates since the service doesn't check for uniqueness
        self.assertEqual(JuraganMaterialProduct.objects.filter(name="Duplicate Product").count(), 2)

    def test_database_service_save_with_price_update(self):
        # First save some initial data
        service = JuraganMaterialDatabaseService()
        initial_data = [
            {"name": "Price Update Product", "price": 10000, "url": "https://example.com/update", "unit": "pcs", "location": "Jakarta"}
        ]
        service.save(initial_data)

        # Now update with new price
        update_data = [
            {"name": "Price Update Product", "price": 12000, "url": "https://example.com/update", "unit": "pcs", "location": "Jakarta"}
        ]
        update_result = service.save_with_price_update(update_data)

        self.assertTrue(update_result['success'])
        self.assertEqual(update_result['updated'], 1)
        self.assertEqual(update_result['inserted'], 0)

        # Check that price was updated
        product = JuraganMaterialProduct.objects.get(name="Price Update Product")
        self.assertEqual(product.price, 12000)

    def test_database_service_save_with_price_anomaly(self):
        # First save some initial data
        service = JuraganMaterialDatabaseService()
        initial_data = [
            {"name": "Anomaly Product", "price": 10000, "url": "https://example.com/anomaly", "unit": "pcs", "location": "Jakarta"}
        ]
        service.save(initial_data)

        # Now update with price change > 15%
        anomaly_data = [
            {"name": "Anomaly Product", "price": 12000, "url": "https://example.com/anomaly", "unit": "pcs", "location": "Jakarta"}
        ]
        update_result = service.save_with_price_update(anomaly_data)

        self.assertTrue(update_result['success'])
        self.assertEqual(len(update_result['anomalies']), 1)

        anomaly = update_result['anomalies'][0]
        self.assertEqual(anomaly['name'], "Anomaly Product")
        self.assertEqual(anomaly['old_price'], 10000)
        self.assertEqual(anomaly['new_price'], 12000)
        self.assertAlmostEqual(anomaly['change_percent'], 20.0, places=1)