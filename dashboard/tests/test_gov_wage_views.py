from django.test import TestCase, Client
from unittest.mock import patch, MagicMock
from api.government_wage.scraper import GovernmentWageItem
import json

from dashboard import gov_wage_views as gvw

class GovWageViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
    
    def create_mock_item(self, item_number='1', work_code='1.1.1.1', description='Test Item', 
                         unit='m', price=100000, region='Kab. Test'):
        return GovernmentWageItem(
            item_number=item_number, work_code=work_code, work_description=description,
            unit=unit, unit_price_idr=price, region=region, edition='Edisi Ke - 2',
            year='2025', sector='Bidang Cipta Karya'
        )

    def test_parse_price_range_and_filters_and_sorting(self):
        test_cases = [
            ('0-500000', (0, 500000)),
            ('500000-1000000', (500000, 1000000)),
            ('1000000-2000000', (1000000, 2000000)),
            ('2000000-', (2000000, float('inf'))),
            ('300000-400000', (300000, 400000)),
        ]
        for price_range, expected in test_cases:
            self.assertEqual(gvw.parse_price_range(price_range), expected)

        data = [
            {'work_description': 'Pagar batu', 'work_code': '1.1', 'unit_price_idr': 100000, 'category': 'pagar'},
            {'work_description': 'Panel Beton', 'work_code': '1.2', 'unit_price_idr': 600000, 'category': 'panel'},
            {'work_description': 'Lainnya', 'work_code': '1.3', 'unit_price_idr': 1500000, 'category': 'lainnya'},
        ]

        self.assertEqual(len(gvw.apply_search_filter(data, 'pagar')), 1)
        self.assertTrue(all(i['category'] == 'pagar' for i in gvw.apply_category_filter(data, 'pagar')))
        self.assertEqual(len(gvw.apply_price_range_filter(data, '0-500000')), 1)
        
        sorted_by_price = gvw.apply_sorting(data, 'unit_price_idr', 'asc')
        self.assertEqual(sorted_by_price[0]['unit_price_idr'], 100000)
        
        self.assertEqual(len(gvw.apply_price_range_filter(data, 'invalid-range')), 3)
        bad_data = [{'unit_price_idr': 'not_a_number'}, {'unit_price_idr': 100000}]
        self.assertEqual(len(gvw.apply_sorting(bad_data, 'unit_price_idr', 'asc')), 2)


    def test_get_regions_endpoint(self):
        resp = self.client.get('/api/gov-wage/regions/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertIsInstance(data.get('regions'), list)

    @patch('dashboard.gov_wage_views.get_cached_or_scrape')
    def test_get_wage_data_handles_scraper_error(self, mock_get_cached):
        mock_get_cached.side_effect = Exception('scraper not available')
        resp = self.client.get('/api/gov-wage/data/?region=Kab. Test&page=1')
        self.assertEqual(resp.status_code, 500)
        self.assertFalse(resp.json().get('success'))
        
        mock_get_cached.side_effect = RuntimeError('Unexpected error')
        resp = self.client.get('/api/gov-wage/data/?region=Kab. Test&page=1')
        self.assertEqual(resp.status_code, 500)
        self.assertFalse(resp.json().get('success'))


    @patch('dashboard.gov_wage_views.get_cached_or_scrape')
    def test_get_wage_data_with_mock_cache(self, mock_get_cached):
        mock_items = [
            self.create_mock_item('1', '1.1.1.1', 'Test Pagar'),
            self.create_mock_item('2', '1.1.1.2', 'Test Panel', 'm2', 200000),
        ]
        mock_get_cached.return_value = mock_items

        resp = self.client.get('/api/gov-wage/data/?region=Kab. Test&page=1')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(len(data['data']), 2)
        self.assertEqual(data['data'][0]['work_code'], '1.1.1.1')


    def test_categorize_work_item_categories(self):
        # Test all categories including edge cases
        test_cases = [
            ('Pembuatan pagar sementara', 'pagar'),
            ('Panel Beton Pracetak', 'panel'),
            ('Papan nama pekerjaan', 'papan_nama'),
            ('Kantor sementara', 'bangunan_sementara'),
            ('Jalan sementara Lapis Macadam', 'jalan_sementara'),
            ('PAGAR SEMENTARA', 'pagar'),  # Case insensitive
            ('panel beton', 'panel'),
            ('Papan Nama Proyek Besi', 'papan_nama'),  # Priority test
            ('  pagar  ', 'pagar'),  # Whitespace
            ('Unknown item', 'lainnya'),
            ('', 'lainnya'),
            (None, 'lainnya'),
        ]
        for description, expected_category in test_cases:
            self.assertEqual(gvw.categorize_work_item(description), expected_category)


    def test_apply_filters_combined(self):
        data = [
            {'work_description': 'Pagar batu', 'work_code': '1.1', 'unit_price_idr': 100000, 'category': 'pagar'},
            {'work_description': 'Panel kolom', 'work_code': '1.2', 'unit_price_idr': 600000, 'category': 'panel'},
            {'work_description': 'Pagar besi', 'work_code': '1.3', 'unit_price_idr': 1500000, 'category': 'pagar'},
        ]
        
        filtered = gvw.apply_filters(data, 'pagar', 'pagar', '0-500000')
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['work_code'], '1.1')

    def test_gov_wage_page_view_exists(self):
        from dashboard.gov_wage_views import gov_wage_page
        self.assertTrue(callable(gov_wage_page))

    def test_gov_wage_page_renders(self):
        resp = self.client.get('/gov-wage/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'HSPK')

    @patch('dashboard.gov_wage_views.get_cached_or_scrape')
    def test_get_wage_data_pagination(self, mock_get_cached):
        mock_items = [self.create_mock_item(str(i), f'1.1.1.{i}', f'Test Item {i}', 
                      price=100000 + i * 10000) for i in range(1, 26)]
        mock_get_cached.return_value = mock_items

        resp = self.client.get('/api/gov-wage/data/?region=Kab. Test&page=2&per_page=10')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data['pagination']['current_page'], 2)
        self.assertEqual(data['pagination']['total_items'], 25)
        self.assertEqual(len(data['data']), 10)


    @patch('dashboard.gov_wage_views.get_cached_or_scrape')
    def test_get_wage_data_with_all_param(self, mock_get_cached):
        mock_items = [self.create_mock_item(str(i), f'1.1.1.{i}', f'Test Item {i}',
                      price=100000 + i * 10000) for i in range(1, 16)]
        mock_get_cached.return_value = mock_items

        resp = self.client.get('/api/gov-wage/data/?region=Kab. Test&all=true')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(len(data['data']), 15)
        self.assertEqual(data['pagination']['total_pages'], 1)
        self.assertEqual(data['pagination']['total_items'], 15)


    @patch('dashboard.gov_wage_views.get_cached_or_scrape')
    def test_search_work_code_view(self, mock_get_cached):
        mock_items = [
            self.create_mock_item('1', '1.1.1.1', 'Test Item 1'),
            self.create_mock_item('2', '2.2.2.2', 'Test Item 2', 'm2', 200000),
        ]
        mock_get_cached.return_value = mock_items

        resp = self.client.post('/api/gov-wage/search/',
            data=json.dumps({'work_code': '1.1.1', 'region': 'Kab. Test'}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['work_code'], '1.1.1.1')


    @patch('dashboard.gov_wage_views.get_cached_or_scrape')
    def test_search_work_code_empty_code(self, mock_get_cached):
        resp = self.client.post('/api/gov-wage/search/',
            data=json.dumps({'work_code': '', 'region': 'Kab. Test'}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json().get('success'))


    @patch('dashboard.gov_wage_views.get_cached_or_scrape')
    def test_search_work_code_no_matches(self, mock_get_cached):
        mock_get_cached.return_value = [self.create_mock_item()]

        resp = self.client.post('/api/gov-wage/search/',
            data=json.dumps({'work_code': '9.9.9', 'region': 'Kab. Test'}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json().get('success'))


    def test_search_work_code_invalid_json(self):
        resp = self.client.post('/api/gov-wage/search/',
            data='invalid json', content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json().get('success'))


    @patch('dashboard.gov_wage_views.get_cached_or_scrape')
    def test_search_work_code_exception(self, mock_get_cached):
        mock_get_cached.side_effect = Exception('Database error')

        resp = self.client.post('/api/gov-wage/search/',
            data=json.dumps({'work_code': '1.1.1', 'region': 'Kab. Test'}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 500)
        self.assertFalse(resp.json().get('success'))


    @patch('dashboard.gov_wage_views.get_cached_or_scrape')
    def test_get_pagination_info(self, mock_get_cached):
        mock_items = [self.create_mock_item(str(i), f'1.1.1.{i}') for i in range(1, 26)]
        mock_get_cached.return_value = mock_items

        resp = self.client.get('/api/gov-wage/pagination/?region=Kab. Test')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data['total_items'], 25)
        self.assertEqual(data['total_pages'], 3) 
 

    @patch('dashboard.gov_wage_views.get_cached_or_scrape')
    def test_get_pagination_info_error(self, mock_get_cached):
        mock_get_cached.side_effect = Exception('Cache error')
        resp = self.client.get('/api/gov-wage/pagination/?region=Kab. Test')
        self.assertEqual(resp.status_code, 500)
        self.assertFalse(resp.json().get('success'))

    def test_apply_filters_edge_cases(self):
        data = [
            {'work_description': 'PAGAR BESI', 'work_code': '1.1', 'category': 'pagar'},
            {'work_description': 'Panel Beton', 'work_code': '1.2', 'category': 'panel'},
            {'work_description': 'Test', 'category': 'lainnya'},
        ]
        self.assertEqual(len(gvw.apply_search_filter(data, 'pagar')), 1)
        self.assertEqual(len(gvw.apply_category_filter(data, 'lainnya')), 1)


    @patch('dashboard.gov_wage_views.get_cached_or_scrape')
    def test_get_wage_data_with_malformed_item(self, mock_get_cached):
        class BadItem:
            @property
            def item_number(self):
                raise AttributeError("Bad item")
        
        mock_get_cached.return_value = [BadItem()]
        resp = self.client.get('/api/gov-wage/data/?region=Kab. Test&page=1')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get('success'))
        self.assertEqual(len(resp.json()['data']), 0)


    @patch('dashboard.gov_wage_views.get_cached_or_scrape')
    def test_get_pagination_info_with_data(self, mock_get_cached):
        mock_items = [self.create_mock_item(str(i), f'1.{i}') for i in range(1, 101)]
        mock_get_cached.return_value = mock_items

        resp = self.client.get('/api/gov-wage/pagination/?region=Kab. Test&year=2025')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data['total_items'], 100)
        self.assertEqual(data['total_pages'], 10)
        self.assertEqual(data['region'], 'Kab. Test')
        self.assertEqual(data['year'], '2025')


    @patch('api.government_wage.scraper.load_from_local_file')
    def test_test_api_success(self, mock_load):
        mock_load.return_value = [self.create_mock_item(region='Kab. Cilacap')]
        resp = self.client.get('/api/gov-wage/test/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data['item_count'], 1)
        self.assertIn('first_item', data)


    @patch('api.government_wage.scraper.load_from_local_file')
    def test_test_api_no_cache(self, mock_load):
        mock_load.return_value = None
        resp = self.client.get('/api/gov-wage/test/')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json().get('success'))
        self.assertIn('No cached data', resp.json()['message'])


    @patch('api.government_wage.scraper.load_from_local_file')
    def test_test_api_empty_list(self, mock_load):
        mock_load.return_value = []
        resp = self.client.get('/api/gov-wage/test/')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json().get('success'))


    @patch('api.government_wage.scraper.load_from_local_file')
    def test_test_api_exception(self, mock_load):
        mock_load.side_effect = Exception('File read error')
        resp = self.client.get('/api/gov-wage/test/')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json().get('success'))
        self.assertIn('error', resp.json())


    @patch('dashboard.gov_wage_views.categorize_work_item')
    @patch('dashboard.gov_wage_views.get_cached_or_scrape')
    def test_get_wage_data_categorization_exception(self, mock_get_cached, mock_categorize):
        mock_items = [
            GovernmentWageItem(
                item_number='1',
                work_code='1.1.1.1',
                work_description='Test',
                unit='m',
                unit_price_idr=100000,
                region='Kab. Test',
                edition='Edisi Ke - 2',
                year='2025',
                sector='Bidang Cipta Karya'
            ),
        ]
        mock_get_cached.return_value = mock_items
        mock_categorize.side_effect = Exception('Categorization failed')

        resp = self.client.get('/api/gov-wage/data/?region=Kab. Test&page=1')
        self.assertEqual(resp.status_code, 200)  
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(len(data['data']), 0)