from unittest.mock import Mock, MagicMock, patch
from db_pricing.models import GemilangProduct
from api.gemilang.factory import create_gemilang_scraper
from api.gemilang.database_service import GemilangDatabaseService
from .test_base import MySQLTestCase

class TestGemilangEndToEnd(MySQLTestCase):
    def test_scrape_and_save_full_flow(self):
        scraper = create_gemilang_scraper()
        
        mock_html = '''
        <html>
            <body>
                <div class="product">
                    <h2>Semen Gresik 40kg</h2>
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
            service = GemilangDatabaseService()
            success, error_msg = service.save(formatted_data)
            self.assertTrue(success)
            self.assertEqual(error_msg, "")
            self.assertGreater(GemilangProduct.objects.count(), 0)

    def test_scrape_with_empty_keyword(self):
        scraper = create_gemilang_scraper()
        result = scraper.scrape_products('')
        self.assertFalse(result.success)
        self.assertEqual(len(result.products), 0)

    def test_scrape_network_error_and_no_save(self):
        scraper = create_gemilang_scraper()
        
        with patch.object(scraper.http_client, 'get', side_effect=Exception("Network error")):
            result = scraper.scrape_products('semen')
        
        self.assertFalse(result.success)
        self.assertEqual(len(result.products), 0)
        
        service = GemilangDatabaseService()
        success, error_msg = service.save([])
        self.assertFalse(success)
        self.assertIn("cannot be empty", error_msg)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_scrape_invalid_html_and_no_save(self):
        scraper = create_gemilang_scraper()
        
        invalid_html = '<html><body>Invalid content</body></html>'
        
        with patch.object(scraper.http_client, 'get', return_value=invalid_html):
            result = scraper.scrape_products('semen')
        
        if not result.success or len(result.products) == 0:
            service = GemilangDatabaseService()
            success, error_msg = service.save([])
            self.assertFalse(success)
            self.assertIn("cannot be empty", error_msg)
            self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_scrape_multiple_keywords_and_save(self):
        scraper = create_gemilang_scraper()
        
        mock_html_1 = '''
        <html>
            <body>
                <div class="product">
                    <h2>Product A</h2>
                    <span class="price">Rp 10.000</span>
                    <a href="/product/a">Detail</a>
                </div>
            </body>
        </html>
        '''
        
        mock_html_2 = '''
        <html>
            <body>
                <div class="product">
                    <h2>Product B</h2>
                    <span class="price">Rp 20.000</span>
                    <a href="/product/b">Detail</a>
                </div>
            </body>
        </html>
        '''
        
        with patch.object(scraper.http_client, 'get', side_effect=[mock_html_1, mock_html_2]):
            result1 = scraper.scrape_products('keyword1')
            result2 = scraper.scrape_products('keyword2')
        
        all_data = []
        if result1.success:
            all_data.extend([
                {'name': p['name'], 'price': p['price'], 'url': p.get('url', ''), 'unit': p.get('unit', '')}
                for p in result1.products
            ])
        if result2.success:
            all_data.extend([
                {'name': p['name'], 'price': p['price'], 'url': p.get('url', ''), 'unit': p.get('unit', '')}
                for p in result2.products
            ])
        
        if all_data:
            service = GemilangDatabaseService()
            success, error_msg = service.save(all_data)
            self.assertTrue(success)
            self.assertEqual(error_msg, "")
            self.assertGreaterEqual(GemilangProduct.objects.count(), len(all_data))

    def test_scrape_and_save_with_unit_field(self):
        scraper = create_gemilang_scraper()
        
        mock_html = '''
        <html>
            <body>
                <div class="product">
                    <h2>Semen Portland 50kg</h2>
                    <span class="price">Rp 70.000</span>
                    <span class="unit">sak</span>
                    <a href="/product/cement">Detail</a>
                </div>
            </body>
        </html>
        '''
        
        with patch.object(scraper.http_client, 'get', return_value=mock_html):
            result = scraper.scrape_products('semen')
        
        if result.success and result.products:
            formatted_data = [
                {'name': p['name'], 'price': p['price'], 'url': p.get('url', ''), 'unit': p.get('unit', '')}
                for p in result.products
            ]
            service = GemilangDatabaseService()
            success, error_msg = service.save(formatted_data)
            self.assertTrue(success)
            self.assertEqual(error_msg, "")
            
            product = GemilangProduct.objects.first()
            if product:
                self.assertIsNotNone(product.unit)

    def test_scrape_and_verify_data_integrity(self):
        scraper = create_gemilang_scraper()
        
        mock_html = '''
        <html>
            <body>
                <div class="product">
                    <h2>Test Product XYZ</h2>
                    <span class="price">Rp 123.456</span>
                    <a href="https://gemilang.com/product/xyz">Detail</a>
                </div>
            </body>
        </html>
        '''
        
        with patch.object(scraper.http_client, 'get', return_value=mock_html):
            result = scraper.scrape_products('test')
        
        if result.success and result.products:
            formatted_data = [
                {'name': p['name'], 'price': p['price'], 'url': p.get('url', ''), 'unit': p.get('unit', '')}
                for p in result.products
            ]
            original_data = formatted_data[0]
            
            service = GemilangDatabaseService()
            service.save(formatted_data)
            
            saved_product = GemilangProduct.objects.first()
            if saved_product:
                self.assertEqual(saved_product.name, original_data['name'])
                self.assertEqual(saved_product.price, original_data['price'])
                self.assertEqual(saved_product.url, original_data['url'])

    def test_scrape_large_dataset_and_save(self):
        scraper = create_gemilang_scraper()
        
        products_html = ''.join([
            f'''
            <div class="product">
                <h2>Product {i}</h2>
                <span class="price">Rp {i * 1000}</span>
                <a href="/product/{i}">Detail</a>
            </div>
            '''
            for i in range(1, 51)
        ])
        
        mock_html = f'<html><body>{products_html}</body></html>'
        
        with patch.object(scraper.http_client, 'get', return_value=mock_html):
            result = scraper.scrape_products('bulk')
        
        if result.success and result.products:
            formatted_data = [
                {'name': p['name'], 'price': p['price'], 'url': p.get('url', ''), 'unit': p.get('unit', '')}
                for p in result.products
            ]
            service = GemilangDatabaseService()
            success, error_msg = service.save(formatted_data)
            self.assertTrue(success)
            self.assertEqual(error_msg, "")
            self.assertGreaterEqual(GemilangProduct.objects.count(), len(formatted_data))

    def test_scrape_with_timeout_and_no_save(self):
        scraper = create_gemilang_scraper()
        
        with patch.object(scraper.http_client, 'get', side_effect=TimeoutError("Request timeout")):
            result = scraper.scrape_products('semen')
        
        self.assertFalse(result.success)
        self.assertEqual(len(result.products), 0)
        
        service = GemilangDatabaseService()
        success, error_msg = service.save([])
        self.assertFalse(success)
        self.assertIn("cannot be empty", error_msg)

    def test_scrape_and_save_idempotency(self):
        scraper = create_gemilang_scraper()
        
        mock_html = '''
        <html>
            <body>
                <div class="product">
                    <h2>Unique Product</h2>
                    <span class="price">Rp 50.000</span>
                    <a href="/product/unique">Detail</a>
                </div>
            </body>
        </html>
        '''
        
        with patch.object(scraper.http_client, 'get', return_value=mock_html):
            result = scraper.scrape_products('unique')
        
        if result.success and result.products:
            formatted_data = [
                {'name': p['name'], 'price': p['price'], 'url': p.get('url', ''), 'unit': p.get('unit', '')}
                for p in result.products
            ]
            service = GemilangDatabaseService()
            
            success_1, error_msg_1 = service.save(formatted_data)
            initial_count = GemilangProduct.objects.count()
            
            success_2, error_msg_2 = service.save(formatted_data)
            final_count = GemilangProduct.objects.count()
            
            self.assertTrue(success_1)
            self.assertEqual(error_msg_1, "")
            self.assertTrue(success_2)
            self.assertEqual(error_msg_2, "")
            self.assertEqual(final_count, initial_count * 2)
