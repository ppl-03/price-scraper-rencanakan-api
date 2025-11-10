import unittest

from api.government_wage.factory import create_government_wage_scraper
from api.government_wage.scraper import GovernmentWageScraper
from api.government_wage.gov_playwright_client import GovernmentWagePlaywrightClient
from api.government_wage.url_builder import GovernmentWageUrlBuilder
from api.government_wage.html_parser import GovernmentWageHtmlParser


class TestGovernmentWageFactory(unittest.TestCase):
    def test_factory_wires_default_components(self):
        scraper = create_government_wage_scraper()  # defaults: headless=True, chromium
        try:
            # scraper instance
            self.assertIsInstance(scraper, GovernmentWageScraper)

            # http client
            self.assertIsInstance(scraper.http_client, GovernmentWagePlaywrightClient)
            self.assertTrue(scraper.http_client.headless)
            self.assertEqual(scraper.http_client.browser_type, "chromium")

            # url builder & parser
            self.assertIsInstance(scraper.url_builder, GovernmentWageUrlBuilder)
            self.assertIsInstance(scraper.html_parser, GovernmentWageHtmlParser)

            # gov client convenience flags/attrs should exist with sensible defaults
            self.assertTrue(hasattr(scraper.http_client, "auto_select_region"))
            self.assertTrue(scraper.http_client.auto_select_region)
            self.assertTrue(hasattr(scraper.http_client, "region_label"))
            # default in client is Kab. Cilacap unless changed later by scraper
            self.assertIsInstance(scraper.http_client.region_label, (str, type(None)))
        finally:
            # make sure browser resources (if any) are closed
            if hasattr(scraper.http_client, "close"):
                try:
                    scraper.http_client.close()
                except Exception:
                    pass

    def test_factory_propagates_options(self):
        scraper = create_government_wage_scraper(headless=False, browser_type="firefox")
        try:
            self.assertIsInstance(scraper.http_client, GovernmentWagePlaywrightClient)
            self.assertFalse(scraper.http_client.headless)
            self.assertEqual(scraper.http_client.browser_type, "firefox")
        finally:
            if hasattr(scraper.http_client, "close"):
                try:
                    scraper.http_client.close()
                except Exception:
                    pass

    def test_builder_search_url_is_base_plus_path(self):
        scraper = create_government_wage_scraper()
        try:
            url = scraper.url_builder.build_search_url()
            self.assertEqual(
                url,
                "https://maspetruk.dpubinmarcipka.jatengprov.go.id/harga_satuan/hspk",
            )
        finally:
            if hasattr(scraper.http_client, "close"):
                try:
                    scraper.http_client.close()
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()