import unittest
from api.government_wage.html_parser import GovernmentWageHtmlParser

def _wrap_table(thead_labels=None, rows_html=""):
    thead = ""
    if thead_labels is not None:
        ths = "".join(f"<th>{lbl}</th>" for lbl in thead_labels)
        thead = f"<thead><tr>{ths}</tr></thead>"
    return f"""
    <html>
      <body>
        <table class="dataTable">
          {thead}
          <tbody>
            {rows_html}
          </tbody>
        </table>
      </body>
    </html>
    """

class TestGovernmentWageHtmlParser(unittest.TestCase):
    def setUp(self):
        self.parser = GovernmentWageHtmlParser()

    def test_empty_html_returns_empty_list(self):
        self.assertEqual(self.parser.parse_products(""), [])

    def test_no_table_returns_empty_list(self):
        html = "<html><body><p>No table here</p></body></html>"
        self.assertEqual(self.parser.parse_products(html), [])

    def test_datatables_empty_state_returns_empty_list(self):
        html = _wrap_table(
            thead_labels=["No", "Kode", "Uraian Pekerjaan", "Satuan", "Harga Satuan (Rp)"],
            rows_html='<tr><td class="dataTables_empty" colspan="5">No data</td></tr>',
        )
        self.assertEqual(self.parser.parse_products(html), [])

    def test_processing_row_is_skipped(self):
        html = _wrap_table(
            thead_labels=["No", "Kode", "Uraian Pekerjaan", "Satuan", "Harga Satuan (Rp)"],
            rows_html="""
              <tr><td colspan="5">Sedang memproses...</td></tr>
              <tr>
                <td>1</td><td>A.1</td>
                <td><a class="hspk" href="#">Uraian A</a></td>
                <td>m2</td><td>Rp 12.345</td>
              </tr>
            """,
        )
        out = self.parser.parse_products(html)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["work_code"], "A.1")

    # ---- happy paths ----
    def test_parses_basic_row_with_anchor_text(self):
        html = _wrap_table(
            thead_labels=["No", "Kode", "Uraian Pekerjaan", "Satuan", "Harga Satuan (Rp)"],
            rows_html="""
              <tr>
                <td>1</td><td>2.2.1.3.1</td>
                <td><a class="hspk" href="#" idnya="36">Pemasangan 1 m2 Bekisting</a></td>
                <td>m2</td><td>Rp 232.373</td>
              </tr>
            """,
        )
        out = self.parser.parse_products(html)
        self.assertEqual(len(out), 1)
        row = out[0]
        self.assertEqual(row["item_number"], "1")
        self.assertEqual(row["work_code"], "2.2.1.3.1")
        self.assertEqual(row["work_description"], "Pemasangan 1 m2 Bekisting")
        self.assertEqual(row["unit"], "m2")
        self.assertEqual(row["price"], 232373)

    def test_parses_nested_span_inside_anchor(self):
        html = _wrap_table(
            thead_labels=["No", "Kode", "Uraian Pekerjaan", "Satuan", "Harga Satuan (Rp)"],
            rows_html="""
              <tr>
                <td>2</td><td>2.2.1.3.4</td>
                <td><a class="hspk" href="#"><span>Pemasangan</span> 1 m2 <span>Kolom</span></a></td>
                <td>m2</td><td>Rp 179,154</td>
              </tr>
            """,
        )
        out = self.parser.parse_products(html)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["work_description"], "Pemasangan 1 m2 Kolom")
        self.assertEqual(out[0]["price"], 179154)

    def test_fallback_to_cell_text_if_anchor_missing(self):
        html = _wrap_table(
            thead_labels=["No", "Kode", "Uraian Pekerjaan", "Satuan", "Harga Satuan (Rp)"],
            rows_html="""
              <tr>
                <td>1</td><td>A.2</td>
                <td>Pekerjaan Tanpa Anchor</td>
                <td>m</td><td>12.000</td>
              </tr>
            """,
        )
        out = self.parser.parse_products(html)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["work_description"], "Pekerjaan Tanpa Anchor")
        self.assertEqual(out[0]["unit"], "m")
        self.assertEqual(out[0]["price"], 12000)

    # ---- header aliases & defaults ----
    def test_header_aliases_are_recognized(self):
        html = _wrap_table(
            thead_labels=["NO", "KODE", "URAIAN PEKERJAAN (HSPK)", "SATUAN", "HARGA SATUAN (RP)"],
            rows_html="""
              <tr>
                <td>1</td><td>K-01</td>
                <td><a class="hspk" href="#">Uraian Variant</a></td>
                <td>unit</td><td>Rp 1.000.000</td>
              </tr>
            """,
        )
        out = self.parser.parse_products(html)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["work_code"], "K-01")
        self.assertEqual(out[0]["work_description"], "Uraian Variant")
        self.assertEqual(out[0]["price"], 1_000_000)

    def test_works_without_thead_using_default_indices(self):
        # No <thead> → parser falls back to default indices (0,1,2,4,5)
        html = _wrap_table(
            thead_labels=None,
            rows_html="""
              <tr>
                <td>9</td><td>X-999</td>
                <td><a class="hspk">No Thead Works</a></td>
                <td>ignored</td><td>Rp 300</td>
                <td>extra</td>
              </tr>
            """,
        )
        out = self.parser.parse_products(html)
        self.assertEqual(len(out), 1)
        row = out[0]
        self.assertEqual(row["item_number"], "9")
        self.assertEqual(row["work_code"], "X-999")
        self.assertEqual(row["work_description"], "No Thead Works")
        self.assertEqual(row["unit"], "ignored")
        self.assertEqual(row["price"], 300)

    # ---- incomplete rows ----
    def test_skips_incomplete_rows(self):
        # Missing work_description → row should be skipped
        html = _wrap_table(
            thead_labels=["No", "Kode", "Uraian Pekerjaan", "Satuan", "Harga Satuan (Rp)"],
            rows_html="""
              <tr>
                <td>1</td><td>K-02</td>
                <td></td>
                <td>m2</td><td>100</td>
              </tr>
            """,
        )
        out = self.parser.parse_products(html)
        self.assertEqual(out, [])

    # ---- price normalization table ----
    def test_price_normalization_various_formats(self):
        cases = [
            ("Rp 0", 0),
            ("Rp 12.345", 12345),
            ("179,154", 179154),
            ("1.234.567", 1234567),
            ("Rp 2.500.000", 2500000),
            ("", 0),
            (None, 0),
        ]
        for price_text, expected in cases:
            unit_price_td = price_text if price_text is not None else ""
            html = _wrap_table(
                thead_labels=["No", "Kode", "Uraian Pekerjaan", "Satuan", "Harga Satuan (Rp)"],
                rows_html=f"""
                  <tr>
                    <td>1</td><td>CODE</td>
                    <td><a class="hspk">Desc</a></td>
                    <td>m2</td><td>{unit_price_td}</td>
                  </tr>
                """,
            )
            out = self.parser.parse_products(html)
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0]["price"], expected)


if __name__ == "__main__":
    unittest.main()