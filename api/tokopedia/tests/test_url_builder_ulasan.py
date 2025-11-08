import unittest
from urllib.parse import urlparse, parse_qs

from api.tokopedia.url_builder_ulasan import TokopediaUrlBuilderUlasan


class TestTokopediaUrlBuilderUlasan(unittest.TestCase):
    
    def setUp(self):
        self.url_builder = TokopediaUrlBuilderUlasan()
        self.base_url = "https://www.tokopedia.com"
        self.search_path = "/p/pertukangan/material-bangunan"

    def test_initialization_with_defaults(self):
        builder = TokopediaUrlBuilderUlasan()
        self.assertEqual(builder.base_url, "https://www.tokopedia.com")
        self.assertEqual(builder.search_path, "/p/pertukangan/material-bangunan")

    def test_basic_search_url_building_ulasan(self):
        keyword = "semen"
        url = self.url_builder.build_search_url(keyword, sort_by_price=True)

        expected_base = f"{self.base_url}{self.search_path}"
        self.assertTrue(url.startswith(expected_base))
        self.assertIn('q=semen', url)
        self.assertIn('ob=5', url)  # Tokopedia-specific sort by "ulasan" / popularity

    def test_search_url_without_ulasan_sorting(self):
        keyword = "bata merah"
        url = self.url_builder.build_search_url(keyword, sort_by_price=False)

        self.assertIn('q=bata+merah', url)
        self.assertNotIn('ob=5', url)

    def test_search_url_with_pagination(self):
        keyword = "semen"
        url = self.url_builder.build_search_url(keyword, page=2)

        self.assertIn('q=semen', url)
        self.assertIn('page=3', url)  # Tokopedia uses 1-based pagination

    def test_search_url_with_zero_page(self):
        keyword = "semen"
        url = self.url_builder.build_search_url(keyword, page=0)

        self.assertIn('q=semen', url)
        self.assertNotIn('page=', url)

    def test_build_params_method(self):
        params = self.url_builder._build_params("semen", True, 0)
        expected = {'q': 'semen', 'ob': '5'}
        self.assertEqual(params, expected)

        params_no_sort = self.url_builder._build_params("semen", False, 1)
        expected_no_sort = {'q': 'semen', 'page': 2}
        self.assertEqual(params_no_sort, expected_no_sort)

    def test_advanced_url_with_price_filters(self):
        keyword = "semen"
        url = self.url_builder.build_search_url_with_filters(
            keyword=keyword,
            sort_by_ulasan=True,
            min_price=50000,
            max_price=100000
        )

        self.assertIn('q=semen', url)
        self.assertIn('ob=5', url)
        self.assertIn('pmin=50000', url)
        self.assertIn('pmax=100000', url)

    def test_advanced_url_with_single_location_id(self):
        url = self.url_builder.build_search_url_with_filters(
            keyword="bata merah",
            location_ids=176
        )

        self.assertIn('q=bata+merah', url)
        self.assertIn('fcity=176', url)

    def test_advanced_url_with_multiple_location_ids(self):
        url = self.url_builder.build_search_url_with_filters(
            keyword="semen",
            location_ids=[174, 175, 176]
        )

        self.assertIn('q=semen', url)
        self.assertIn('fcity=174%2C175%2C176', url)

    def test_advanced_url_with_all_filters(self):
        url = self.url_builder.build_search_url_with_filters(
            keyword="semen portland",
            sort_by_ulasan=True,
            page=1,
            min_price=50000,
            max_price=100000,
            location_ids=[174, 175, 176]
        )

        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        self.assertIn('semen+portland', url)
        self.assertEqual(params['q'], ['semen portland'])
        self.assertEqual(params['ob'], ['5'])
        self.assertEqual(params['page'], ['2'])
        self.assertEqual(params['pmin'], ['50000'])
        self.assertEqual(params['pmax'], ['100000'])
        self.assertEqual(params['fcity'], ['174,175,176'])

    def test_validation_and_error_handling(self):
        with self.assertRaises(ValueError):
            self.url_builder.build_search_url_with_filters("")

        with self.assertRaises(ValueError):
            self.url_builder.build_search_url_with_filters("   ")

        with self.assertRaises(ValueError):
            self.url_builder.build_search_url_with_filters(None)

        with self.assertRaises(ValueError):
            self.url_builder.build_search_url_with_filters("semen", page=-1)

    def test_url_structure_and_encoding(self):
        url = self.url_builder.build_search_url_with_filters(
            keyword="semen & bata merah",
            min_price=50000
        )

        parsed = urlparse(url)
        self.assertEqual(parsed.scheme, 'https')
        self.assertEqual(parsed.netloc, 'www.tokopedia.com')
        self.assertEqual(parsed.path, '/p/pertukangan/material-bangunan')

        params = parse_qs(parsed.query)
        self.assertEqual(params['q'], ['semen & bata merah'])
        self.assertEqual(params['pmin'], ['50000'])

    def test_build_search_url_compatibility(self):
        keyword = "semen"
        sort_flag = True
        page = 1

        basic_url = self.url_builder.build_search_url(keyword, sort_flag, page)
        advanced_url = self.url_builder.build_search_url_with_filters(
            keyword=keyword,
            sort_by_ulasan=sort_flag,
            page=page
        )

        self.assertEqual(basic_url, advanced_url)


if __name__ == '__main__':
    unittest.main()
