import unittest
from api.blibli.factory import create_blibli_scraper
from api.blibli.scraper import BlibliPriceScraper

class TestBlibliFactory(unittest.TestCase):
    
    def test_factory_creates_scraper_instance(self):
        scraper = create_blibli_scraper()
        self.assertIsInstance(scraper, BlibliPriceScraper)
        self.assertIsNotNone(scraper.http_client)
        self.assertIsNotNone(scraper.url_builder)
        self.assertIsNotNone(scraper.html_parser)
    
    def test_factory_creates_unique_instances(self):
        scraper1 = create_blibli_scraper()
        scraper2 = create_blibli_scraper()
        self.assertIsNot(scraper1, scraper2)

if __name__ == '__main__':
    unittest.main()