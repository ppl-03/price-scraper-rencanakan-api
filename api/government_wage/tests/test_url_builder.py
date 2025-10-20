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
        out1 = self.builder.build_region_url("Kab. Cilacap")
        out2 = self.builder.build_search_url()
        self.assertEqual(out1, out2)

    def test_custom_base_and_path_override_defaults(self):
        builder = GovernmentWageUrlBuilder(
            base_url="https://example.com",
            search_path="/custom/path"
        )
        self.assertEqual(builder.build_search_url(), "https://example.com/custom/path")

    def test_build_region_url_with_different_region_still_returns_same_url(self):
        for region in ["Kab. Pekalongan", "Kota Semarang", "Kab. Wonosobo"]:
            result = self.builder.build_region_url(region)
            self.assertEqual(
                result,
                "https://maspetruk.dpubinmarcipka.jatengprov.go.id/harga_satuan/hspk",
            )


if __name__ == "__main__":
    unittest.main()