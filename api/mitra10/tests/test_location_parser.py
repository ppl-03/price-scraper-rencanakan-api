from django.test import TestCase
from api.mitra10.location_parser import Mitra10LocationParser


class TestMitra10LocationParser(TestCase):

    def setUp(self):
        self.valid_html = """
        <div role="presentation">
          <ul>
            <li><span>MITRA10 JAKARTA</span></li>
            <li><span>MITRA10 BANDUNG</span></li>
            <li><span>MITRA10 BALI</span></li>
          </ul>
        </div>
        """
        self.empty_html = "<div role='presentation'><ul></ul></div>"
        self.malformed_html = "<div role='presentation'><li><span>MITRA10 DEPOK"

    def test_parse_valid_html(self):
        result = Mitra10LocationParser.parse(self.valid_html)
        self.assertEqual(result, ["JAKARTA", "BANDUNG", "BALI"])

    def test_parse_empty_html(self):
        result = Mitra10LocationParser.parse(self.empty_html)
        self.assertEqual(result, [])

    def test_parse_malformed_html(self):
        result = Mitra10LocationParser.parse(self.malformed_html)
        self.assertEqual(result, ["DEPOK"])

    def test_parse_with_extra_spaces(self):
        html = """
        <div role="presentation"><ul><li><span>  MITRA10 SURABAYA  </span></li></ul></div>
        """
        result = Mitra10LocationParser.parse(html)
        self.assertEqual(result, ["SURABAYA"])

    def test_parse_with_plain_text(self):
        html = "Just some plain text"
        result = Mitra10LocationParser.parse(html)
        self.assertEqual(result, [])
