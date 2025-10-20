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
    def parse_products(self, html_content: str) -> List[Dict[str, Any]]:
        try:
            if not html_content or not html_content.strip():
                logger.warning("Empty HTML content received")
                return []

            soup = BeautifulSoup(html_content, "html.parser")

            table = soup.find("table", class_="dataTable")
            if not table:
                logger.warning("dataTable not found")
                return []

            idx = self._header_index_map(table)

            tbody = table.find("tbody")
            if not tbody:
                logger.warning("tbody not found in table")
                return []

            # DataTables empty result sentinel
            if tbody.select_one("td.dataTables_empty"):
                logger.info("DataTables reports empty result set")
                return []

            rows = tbody.find_all("tr")
            if not rows:
                logger.warning("No rows found in table body")
                return []

            products: List[Dict[str, Any]] = []

            # --------- robust row parsing ---------
            for tr in rows:
                if "Processing" in tr.get_text() or "Sedang memproses" in tr.get_text():
                    continue

                tds = tr.find_all("td")
                if len(tds) < 5:
                    continue

                # --- safer index resolution ---
                i_no, i_kode, i_uraian, i_sat, i_harga = 0, 1, 2, 3, 4
                if idx:
                    i_no = idx.get("no", i_no)
                    i_kode = idx.get("kode", i_kode)
                    i_uraian = idx.get("uraian pekerjaan", i_uraian)
                    i_sat = idx.get("satuan", i_sat)
                    i_harga = idx.get("harga satuan", i_harga)

                # --- extract text from "Uraian Pekerjaan" column safely ---
                desc_cell = tds[i_uraian] if i_uraian < len(tds) else None
                work_description = ""
                if desc_cell:
                    a = desc_cell.select_one("a.hspk") or desc_cell.find("a")
                    if a:
                        text = a.get_text(separator=" ", strip=True)
                        if text:
                            work_description = re.sub(r"\s+", " ", text)
                    else:
                        work_description = desc_cell.get_text(separator=" ", strip=True)


                # --- other columns ---
                item_number = self._text(self._safe_get(tds, i_no))
                work_code = self._text(self._safe_get(tds, i_kode))
                unit = self._text(self._safe_get(tds, i_sat))
                price_text = self._text(self._safe_get(tds, i_harga))
                price = self._parse_price(price_text)

                # Skip incomplete rows
                if not (work_code and work_description and unit):
                    continue

                products.append({
                    "item_number": item_number,
                    "work_code": work_code,
                    "work_description": work_description.strip(' "\u00a0'),
                    "unit": unit,
                    "price": price,
                })

            logger.info(f"Parsed {len(products)} rows from MAS PETRUK table.")
            return products

        except Exception as e:
            raise HtmlParserError(f"Failed to parse HTML: {e}")

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
            "uraian": "uraian pekerjaan",
            "uraian pekerjaan (hspk)": "uraian pekerjaan",
            "harga satuan (rp)": "harga satuan",
        }
        for k, v in list(mapping.items()):
            if k in aliases:
                mapping[aliases[k]] = v

        canonical: Dict[str, int] = {}
        for key in ("no", "kode", "uraian pekerjaan", "satuan", "harga satuan"):
            if key in mapping:
                canonical[key] = mapping[key]
        return canonical
