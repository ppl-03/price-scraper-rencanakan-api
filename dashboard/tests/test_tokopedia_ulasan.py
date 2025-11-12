from django.test import TestCase, Client
from unittest.mock import patch, MagicMock, Mock
from dashboard import views
from api.tokopedia.url_builder_ulasan import TokopediaUrlBuilderUlasan


class TokopediaUlasanScraperTests(TestCase):

    def test_create_tokopedia_ulasan_scraper(self):
        scraper, url_builder = views._create_tokopedia_ulasan_scraper()
        
        self.assertIsNotNone(scraper)
        self.assertIsNotNone(url_builder)
        self.assertIsInstance(url_builder, TokopediaUrlBuilderUlasan)
        self.assertTrue(hasattr(scraper, 'http_client'))
        self.assertTrue(hasattr(scraper, 'url_builder'))
        self.assertTrue(hasattr(scraper, 'html_parser'))
        self.assertIsInstance(scraper.url_builder, TokopediaUrlBuilderUlasan)

    def test_ulasan_url_builder_uses_ob5_parameter(self):
        url_builder = TokopediaUrlBuilderUlasan()
        
        url = url_builder.build_search_url(
            keyword="semen",
            sort_by_price=True,
            page=0
        )
        
        self.assertIn("ob=5", url)
        
    def test_ulasan_url_builder_without_sorting(self):
        url_builder = TokopediaUrlBuilderUlasan()
        
        url = url_builder.build_search_url(
            keyword="semen",
            sort_by_price=False,
            page=0
        )
        
        self.assertIsInstance(url, str)
        self.assertIn("semen", url)


class TokopediaDashboardIntegrationTests(TestCase):

    @patch('dashboard.views._run_vendor_to_prices')
    def test_scrape_all_vendors_uses_ulasan_scraper(self, mock_run_vendor):
        mock_run_vendor.return_value = []
        request = Mock()
        
        views._scrape_all_vendors(request, "semen")
        
        self.assertEqual(mock_run_vendor.call_count, 5)
        tokopedia_call = mock_run_vendor.call_args_list[4]
        maker_func = tokopedia_call[0][2]
        scraper, url_builder = maker_func()
        self.assertIsInstance(url_builder, TokopediaUrlBuilderUlasan)
        
    def test_trigger_scrape_uses_ulasan_scraper(self):
        scraper_func = views._create_tokopedia_ulasan_scraper
        scraper, url_builder = scraper_func()
        self.assertIsInstance(url_builder, TokopediaUrlBuilderUlasan)
        self.assertIsNotNone(scraper)


class TokopediaFallbackTests(TestCase):

    @patch('dashboard.views._human_get')
    def test_try_simple_tokopedia_url_uses_ulasan(self, mock_human_get):
        mock_human_get.return_value = '<html><body></body></html>'
        
        products, url, html_len = views._try_simple_tokopedia_url("semen", sort_by_price=True, page=0)
        
        mock_human_get.assert_called_once()
        called_url = mock_human_get.call_args[0][0]
        self.assertIn("ob=5", called_url)
        
    @patch('dashboard.views._try_simple_tokopedia_url')
    def test_tokopedia_fallback_uses_updated_simple_url(self, mock_try_simple):
        mock_try_simple.return_value = ([], "https://test.com", 100)
        
        products, url, html_len = views._tokopedia_fallback("semen", sort_by_price=True, page=0)
        
        mock_try_simple.assert_called_once_with("semen", True, 0)


class TokopediaUlasanE2ETests(TestCase):

    @patch('dashboard.views.TokopediaHttpClient')
    @patch('dashboard.views.TokopediaHtmlParser')
    def test_ulasan_scraper_full_flow(self, mock_parser_class, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        
        scraper, url_builder = views._create_tokopedia_ulasan_scraper()
        
        self.assertIsNotNone(scraper)
        self.assertIsInstance(url_builder, TokopediaUrlBuilderUlasan)
        
        url = url_builder.build_search_url("semen", sort_by_price=True, page=0)
        self.assertIn("ob=5", url)
        
    @patch('dashboard.views._execute_vendor_scraping')
    def test_run_vendor_to_prices_with_ulasan_scraper(self, mock_execute):
        mock_execute.return_value = [
            {
                'name': 'Semen Gresik 50kg',
                'price': 65000,
                'unit': 'zak',
                'location': 'Jakarta',
                'source': 'Tokopedia'
            }
        ]
        
        request = Mock()
        keyword = "semen"
        
        results = views._run_vendor_to_prices(
            request,
            keyword,
            views._create_tokopedia_ulasan_scraper,
            views.TOKOPEDIA_SOURCE,
            fallback=views._tokopedia_fallback,
            limit=20
        )
        
        self.assertIsInstance(results, list)
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args
        self.assertEqual(call_args[1]['limit'], 20)


class TokopediaUrlBuilderCompatibilityTests(TestCase):

    def test_build_search_url_method(self):
        url_builder = TokopediaUrlBuilderUlasan()
        
        self.assertTrue(hasattr(url_builder, 'build_search_url'))
        
        url = url_builder.build_search_url("test", sort_by_price=True, page=0)
        self.assertIsInstance(url, str)
        self.assertIn("ob=5", url)
        
    def test_build_search_url_with_filters_method(self):
        url_builder = TokopediaUrlBuilderUlasan()
        
        self.assertTrue(hasattr(url_builder, 'build_search_url_with_filters'))
        
        url = url_builder.build_search_url_with_filters(
            keyword="test",
            sort_by_price=True,
            page=0,
            min_price=10000,
            max_price=100000,
            location_ids=[1, 2]
        )
        self.assertIsInstance(url, str)
        self.assertIn("ob=5", url)
        
    def test_url_builder_defensive_method_check(self):
        url_builder = TokopediaUrlBuilderUlasan()
        
        url = views._build_url_defensively(url_builder, "test", sort_by_price=True, page=0)
        
        self.assertIsInstance(url, str)
        self.assertIn("ob=5", url)


class TokopediaScraperParameterTests(TestCase):

    @patch('dashboard.views._safe_scrape_products')
    def test_scraper_receives_limit_parameter(self, mock_safe_scrape):
        mock_safe_scrape.return_value = MagicMock(success=True, products=[])
        
        request = Mock()
        
        with patch('dashboard.views._fetch_len', return_value=1000):
            with patch('dashboard.views.messages'):
                views._execute_vendor_scraping(
                    request,
                    "semen",
                    views._create_tokopedia_ulasan_scraper,
                    views.TOKOPEDIA_SOURCE,
                    None,
                    limit=20
                )
        
        mock_safe_scrape.assert_called_once()
        call_kwargs = mock_safe_scrape.call_args[1]
        self.assertEqual(call_kwargs.get('limit'), 20)
        
    def test_scraper_receives_sort_by_price_parameter(self):
        scraper, url_builder = views._create_tokopedia_ulasan_scraper()
        
        url = url_builder.build_search_url("test", sort_by_price=True, page=0)
        
        self.assertIn("ob=5", url)
