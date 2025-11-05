import unittest
from api.government_wage.url_builder import GovernmentWageUrlBuilder


class TestGovernmentWageUrlBuilder(unittest.TestCase):
    def setUp(self):
        self.builder = GovernmentWageUrlBuilder()

    def test_default_base_and_path(self):
        self.assertEqual(
            self.builder.base_url,
            "https://maspetruk.dpubinmarcipka.jatengprov.go.id",
        )
        self.assertEqual(self.builder.search_path, "/harga_satuan/hspk")

    def test_build_search_url_returns_combined_url(self):
        url = self.builder.build_search_url()
        self.assertEqual(
            url,
            "https://maspetruk.dpubinmarcipka.jatengprov.go.id/harga_satuan/hspk",
        )

    def test_build_search_url_ignores_keyword_and_page(self):
        url_1 = self.builder.build_search_url(keyword="Cilacap")
        url_2 = self.builder.build_search_url(sort_by_price=False, page=2)
        expected = "https://maspetruk.dpubinmarcipka.jatengprov.go.id/harga_satuan/hspk"
        self.assertEqual(url_1, expected)
        self.assertEqual(url_2, expected)

    def test_build_region_url_delegates_to_search_url(self):
        out1 = self.builder.build_region_url()
        out2 = self.builder.build_search_url()
        self.assertEqual(out1, out2)

    def test_custom_base_and_path_override_defaults(self):
        builder = GovernmentWageUrlBuilder(
            base_url="https://example.com",
            search_path="/custom/path"
        )
        self.assertEqual(builder.build_search_url(), "https://example.com/custom/path")

    def test_build_region_url_returns_consistent_url(self):
        # Since build_region_url no longer takes parameters, test it returns consistent URL
        result1 = self.builder.build_region_url()
        result2 = self.builder.build_region_url()
        expected = "https://maspetruk.dpubinmarcipka.jatengprov.go.id/harga_satuan/hspk"
        self.assertEqual(result1, expected)
        self.assertEqual(result2, expected)


if __name__ == "__main__":
    unittest.main()