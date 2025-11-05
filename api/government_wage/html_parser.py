from typing import List, Dict, Any
from bs4 import BeautifulSoup
from api.interfaces import IHtmlParser, HtmlParserError
import logging
import re

logger = logging.getLogger(__name__)


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


class GovernmentWageHtmlParser(IHtmlParser):
    # Column header constants
    COL_URAIAN_PEKERJAAN = "uraian pekerjaan"
    COL_HARGA_SATUAN = "harga satuan"
    
    def parse_products(self, html_content: str) -> List[Dict[str, Any]]:
        try:
            table = self._validate_and_get_table(html_content)
            if not table:
                return []

            tbody = self._get_table_body(table)
            if not tbody:
                return []

            idx = self._header_index_map(table)
            rows = tbody.find_all("tr")
            
            if not rows:
                logger.warning("No rows found in table body")
                return []

            products = self._parse_table_rows(rows, idx)
            logger.info(f"Parsed {len(products)} rows from MAS PETRUK table.")
            return products

        except Exception as e:
            raise HtmlParserError(f"Failed to parse HTML: {e}")

    def _validate_and_get_table(self, html_content: str):
        """Validate HTML content and extract the data table."""
        if not html_content or not html_content.strip():
            logger.warning("Empty HTML content received")
            return None

        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table", class_="dataTable")
        
        if not table:
            logger.warning("dataTable not found")
            return None
            
        return table

    def _get_table_body(self, table):
        """Get and validate table body."""
        tbody = table.find("tbody")
        if not tbody:
            logger.warning("tbody not found in table")
            return None

        # DataTables empty result sentinel
        if tbody.select_one("td.dataTables_empty"):
            logger.info("DataTables reports empty result set")
            return None

        return tbody

    def _parse_table_rows(self, rows, idx) -> List[Dict[str, Any]]:
        """Parse table rows into product data."""
        products: List[Dict[str, Any]] = []

        for tr in rows:
            if self._is_processing_row(tr):
                continue

            tds = tr.find_all("td")
            if len(tds) < 5:
                continue

            product = self._extract_product_from_row(tds, idx)
            if product:
                products.append(product)

        return products

    def _is_processing_row(self, tr) -> bool:
        """Check if row is a processing indicator."""
        text = tr.get_text()
        return "Processing" in text or "Sedang memproses" in text

    def _extract_product_from_row(self, tds, idx) -> Dict[str, Any]:
        """Extract product data from a table row."""
        column_indices = self._get_column_indices(idx)
        
        work_description = self._extract_work_description(tds, column_indices['uraian'])
        item_number = self._text(self._safe_get(tds, column_indices['no']))
        work_code = self._text(self._safe_get(tds, column_indices['kode']))
        unit = self._text(self._safe_get(tds, column_indices['satuan']))
        price_text = self._text(self._safe_get(tds, column_indices['harga']))
        price = self._parse_price(price_text)

        # Skip incomplete rows
        if not (work_code and work_description and unit):
            return None

        return {
            "item_number": item_number,
            "work_code": work_code,
            "work_description": work_description.strip(' "\u00a0'),
            "unit": unit,
            "price": price,
        }

    def _get_column_indices(self, idx) -> Dict[str, int]:
        """Get column indices with fallback to defaults."""
        defaults = {'no': 0, 'kode': 1, 'uraian': 2, 'satuan': 3, 'harga': 4}
        
        if not idx:
            return defaults

        return {
            'no': idx.get("no", defaults['no']),
            'kode': idx.get("kode", defaults['kode']),
            'uraian': idx.get(self.COL_URAIAN_PEKERJAAN, defaults['uraian']),
            'satuan': idx.get("satuan", defaults['satuan']),
            'harga': idx.get(self.COL_HARGA_SATUAN, defaults['harga']),
        }

    def _extract_work_description(self, tds, uraian_index: int) -> str:
        """Extract work description from the uraian column."""
        desc_cell = tds[uraian_index] if uraian_index < len(tds) else None
        if not desc_cell:
            return ""

        # Try to get text from anchor tag first
        a = desc_cell.select_one("a.hspk") or desc_cell.find("a")
        if a:
            text = a.get_text(separator=" ", strip=True)
            if text:
                return re.sub(r"\s+", " ", text)

        # Fallback to cell text
        return desc_cell.get_text(separator=" ", strip=True)

    # ---------- helpers ----------
    @staticmethod
    def _text(node) -> str:
        if not node:
            return ""
        # use separator to flatten nested tags, strip whitespace
        return re.sub(r"\s+", " ", node.get_text(separator=" ", strip=True)).strip()

    @staticmethod
    def _parse_price(price_text: str) -> int:
        # remove non-digits, safely cast to int
        digits = re.sub(r"[^\d]", "", price_text or "")
        return int(digits) if digits else 0

    @staticmethod
    def _safe_get(lst, i: int):
        return lst[i] if 0 <= i < len(lst) else None

    def _header_index_map(self, table) -> Dict[str, int]:
        """Map normalized header names to column indices."""
        thead = table.find("thead")
        mapping: Dict[str, int] = {}
        if not thead:
            return mapping

        ths = thead.find_all("th")
        for i, th in enumerate(ths):
            label = _norm(th.get_text())
            if not label:
                continue
            mapping[label] = i

        aliases = {
            "uraian": self.COL_URAIAN_PEKERJAAN,
            "uraian pekerjaan (hspk)": self.COL_URAIAN_PEKERJAAN,
            "harga satuan (rp)": self.COL_HARGA_SATUAN,
        }
        # Build alias mappings separately to avoid modifying dict during iteration
        alias_mappings = {}
        for k, v in mapping.items():
            if k in aliases:
                alias_mappings[aliases[k]] = v
        
        # Update mapping after iteration
        mapping.update(alias_mappings)

        canonical: Dict[str, int] = {}
        for key in ("no", "kode", self.COL_URAIAN_PEKERJAAN, "satuan", self.COL_HARGA_SATUAN):
            if key in mapping:
                canonical[key] = mapping[key]
        return canonical
