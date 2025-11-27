import re
import logging
from typing import Optional, Dict, List
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ReDoS protection: Set regex timeout (Python 3.11+)
try:
    _REGEX_TIMEOUT = 0.1  # 100ms timeout
except AttributeError:
    _REGEX_TIMEOUT = None


class DepoBangunanUnitExtractor:
    # Pre-compile commonly used patterns with ReDoS protection
    # Fixed: Use atomic groups and bounded quantifiers to prevent backtracking
    _AREA_PATTERN = re.compile(r'(\d{1,10}(?:[.,]\d{1,10})?)[ \t]?[x×][ \t]?(\d{1,10}(?:[.,]\d{1,10})?)[ \t]?(cm|mm|m)(?:\s|$)', re.IGNORECASE)
    _INCH_PATTERN = re.compile(r'\d{1,10}(?:[.,]\d{1,10})?[ \t]{0,3}(?:["″]|inch|inchi)(?=\s|$)', re.IGNORECASE)
    _FEET_PATTERN = re.compile(r'\d{1,10}(?:[.,]\d{1,10})?[ \t]{0,3}(?:[\'′]|feet|ft)(?=\s|$)', re.IGNORECASE)
    _ADJACENT_PATTERN = re.compile(r'(\d{1,10}(?:[.,]\d{1,10})?)(kg|gram|gr|g|ml|lt|l|cc|pcs|set|mm|cm|m)(?=\s|$)', re.IGNORECASE)
    _SPEC_UNIT_PATTERN = re.compile(r'[a-zA-Z²³]{1,20}')
    
    def __init__(self):
        self.unit_patterns = self._initialize_unit_patterns()
        self.priority_order = self._initialize_priority_order()
        # Cache for compiled priority patterns
        self._compiled_patterns = {}
    
    def _initialize_unit_patterns(self) -> Dict[str, List[str]]:
        return {
            'KG': ['kg', 'kilogram', 'kilo'],
            'G': ['gram', 'gr', 'g(?!a)'],
            'L': ['liter', 'litre', 'lt', 'l(?!b|t)'],
            'ML': ['ml', 'mililiter', 'milliliter'],
            'CC': ['cc', 'cubic centimeter'],
            'M': ['meter', 'metre', r'm(?!m|l|g|²|³)'],
            'CM': ['cm', 'centimeter', 'sentimeter'],
            'MM': ['mm', 'milimeter', 'millimeter'],
            'INCH': ['inch', 'inchi', '"', '″', r'\d+"', r'\d+\s*"', r'\d+\s*inch'],
            'FEET': ['feet', 'ft', '\'', '′'],
            'M²': ['m²', 'm2', 'meter persegi', 'square meter'],
            'CM²': ['cm²', 'cm2', 'centimeter persegi', 'sentimeter persegi'],
            'M³': ['m³', 'm3', 'meter kubik', 'cubic meter'],
            'PCS': ['pcs', 'pieces', 'piece', 'buah', 'biji', 'angka'],
            'SET': ['set', 'sets'],
            'PACK': ['pack', 'pak', 'kemasan'],
            'BOX': ['box', 'kotak', 'dus'],
            'ROLL': ['roll', 'gulungan', 'gulung'],
            'SHEET': ['sheet', 'lembar', 'lbr'],
            'BATANG': ['batang', 'bar', 'rod', 'stick'],
            'LEMBAR': ['lembar', 'sheet', 'lbr'],
            'UNIT': [r'\d+\s*unit', r'\d+\s*units'],
            'WATT': ['watt', 'w(?!a)', 'daya'],
            'VOLT': ['volt', 'v(?!a|e)'],
            'AMPERE': ['ampere', 'amp', 'a(?!l|r|n)']
        }
    
    def _initialize_priority_order(self) -> List[str]:
        """Initialize priority order for unit extraction."""
        return [
            'M²', 'CM²',  # Area units first (common for tiles, flooring)
            'M³',         # Volume units
            'KG', 'G',    # Weight units
            'M', 'CM', 'MM', 'INCH', 'FEET',  # Linear units
            'L', 'ML', 'CC',    # Liquid/volume units
            'PCS', 'SET', 'PACK', 'BOX', 'ROLL', 'SHEET', 'BATANG', 'LEMBAR', 'UNIT',  # Count units
            'WATT', 'VOLT', 'AMPERE'  # Electrical units
        ]
    
    def extract_unit_from_name(self, product_name: str) -> Optional[str]:
        """Extract unit from product name using pattern matching."""
        if not product_name or not isinstance(product_name, str):
            return None
        
        # ReDoS protection: Limit input length
        if len(product_name) > 1000:
            logger.warning(f"Product name too long ({len(product_name)} chars), truncating to 1000")
            product_name = product_name[:1000]
        
        try:
            text_lower = product_name.lower().strip()
            
            area_unit = self._extract_area_unit(text_lower)
            if area_unit:
                return area_unit
            
            adjacent_unit = self._extract_adjacent_unit(text_lower)
            if adjacent_unit:
                return adjacent_unit
            
            priority_unit = self._extract_by_priority_patterns(text_lower)
            if priority_unit:
                return priority_unit
            
            if self._should_default_to_pcs(text_lower):
                return 'PCS'
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting unit from name '{product_name}': {e}")
            return None
    
    def extract_unit_from_specification(self, spec_text: str) -> Optional[str]:

        if not spec_text or not isinstance(spec_text, str):
            return None
        
        # ReDoS protection: Limit input length
        if len(spec_text) > 500:
            logger.warning(f"Specification text too long ({len(spec_text)} chars), truncating to 500")
            spec_text = spec_text[:500]
        
        try:
            # Remove numbers and get only the unit part using pre-compiled pattern
            unit_match = self._SPEC_UNIT_PATTERN.search(spec_text.strip())
            if unit_match:
                unit = unit_match.group().upper()
                
                # Normalize common variations
                unit_mapping = {
                    'KG': 'KG', 'KILOGRAM': 'KG', 'KILO': 'KG',
                    'GRAM': 'G', 'GR': 'G', 'G': 'G',
                    'LITER': 'L', 'LITRE': 'L', 'LT': 'L', 'L': 'L',
                    'ML': 'ML', 'MILILITER': 'ML', 'MILLILITER': 'ML',
                    'METER': 'M', 'METRE': 'M', 'M': 'M',
                    'CM': 'CM', 'CENTIMETER': 'CM', 'SENTIMETER': 'CM',
                    'MM': 'MM', 'MILIMETER': 'MM', 'MILLIMETER': 'MM',
                    'M2': 'M²', 'M²': 'M²',
                    'CM2': 'CM²', 'CM²': 'CM²',
                    'M3': 'M³', 'M³': 'M³',
                    'PCS': 'PCS', 'PIECES': 'PCS', 'PIECE': 'PCS', 'BUAH': 'PCS',
                    'SET': 'SET', 'SETS': 'SET',
                    'PACK': 'PACK', 'PAK': 'PACK',
                    'BOX': 'BOX', 'KOTAK': 'BOX',
                    'ROLL': 'ROLL', 'GULUNGAN': 'ROLL',
                    'SHEET': 'SHEET', 'LEMBAR': 'SHEET', 'LBR': 'SHEET',
                    'BATANG': 'BATANG', 'BAR': 'BATANG', 'ROD': 'BATANG',
                    'UNIT': 'UNIT', 'UNITS': 'UNIT'
                }
                
                return unit_mapping.get(unit, unit if len(unit) <= 4 else None)
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting unit from specification '{spec_text}': {e}")
            return None
    
    def _extract_area_unit(self, text_lower: str) -> Optional[str]:
        try:
            match = self._AREA_PATTERN.search(text_lower)
            if match:
                unit_key = match.group(3).lower()
                area_map = {'cm': 'CM²', 'mm': 'MM²', 'm': 'M²'}
                return area_map.get(unit_key)
            return None
        except Exception as e:
            logger.warning(f"Error in area pattern extraction: {e}")
            return None
    
    def _extract_adjacent_unit(self, text_lower: str) -> Optional[str]:
        """Extract units that are adjacent to numbers like '25kg' or '3"'."""
        try:
            # Check for inch patterns first
            inch_unit = self._extract_inch_patterns(text_lower)
            if inch_unit:
                return inch_unit
            
            # Check for feet patterns
            feet_unit = self._extract_feet_patterns(text_lower)
            if feet_unit:
                return feet_unit
            
            # Check for standard adjacent patterns
            standard_unit = self._extract_standard_adjacent_patterns(text_lower)
            if standard_unit:
                return standard_unit
            
            return None
        except Exception as e:
            logger.warning(f"Error in adjacent pattern extraction: {e}")
            return None
    
    def _extract_inch_patterns(self, text_lower: str) -> Optional[str]:
        if self._INCH_PATTERN.search(text_lower):
            return 'INCH'
        return None
    
    def _extract_feet_patterns(self, text_lower: str) -> Optional[str]:
        if self._FEET_PATTERN.search(text_lower):
            return 'FEET'
        return None
    
    def _extract_standard_adjacent_patterns(self, text_lower: str) -> Optional[str]:
        unit_map = {
            'kg': 'KG', 'gram': 'G', 'gr': 'G', 'g': 'G', 'ml': 'ML', 
            'lt': 'L', 'l': 'L', 'cc': 'CC', 'pcs': 'PCS', 'set': 'SET', 
            'mm': 'MM', 'cm': 'CM', 'm': 'M'
        }
        
        match = self._ADJACENT_PATTERN.search(text_lower)
        if match and len(match.groups()) >= 2:
            unit_key = match.group(2).lower()
            return unit_map.get(unit_key)
        return None
    
    def _extract_by_priority_patterns(self, text_lower: str) -> Optional[str]:
        try:
            for unit in self.priority_order:
                # Use cached compiled pattern with ReDoS protection
                if unit not in self._compiled_patterns:
                    patterns = self.unit_patterns.get(unit, [])
                    # Fixed: Use word boundaries and lookaheads to prevent backtracking
                    combined_pattern = '|'.join(f'(?:^|\\s|[\\(\\[{{])({p})(?=\\s|[\\)\\]}}]|$)' for p in patterns)
                    self._compiled_patterns[unit] = re.compile(combined_pattern, re.IGNORECASE)
                
                # ReDoS protection: Catch timeout exceptions
                try:
                    if self._compiled_patterns[unit].search(text_lower):
                        return unit
                except TimeoutError:
                    logger.warning(f"Regex timeout for unit {unit}, skipping")
                    continue
            return None
        except Exception as e:
            logger.warning(f"Error in priority pattern extraction: {e}")
            return None
    
    def _should_default_to_pcs(self, text_lower: str) -> bool:
        pcs_indicators = [
            'sponge', 'brush', 'kuas', 'spons', 'sikat', 'angka', 'number',
            'switch', 'saklar', 'stop kontak', 'outlet', 'plug', 'socket',
            'handle', 'pegangan', 'knob', 'kenop', 'button', 'tombol'
        ]
        
        return any(indicator in text_lower for indicator in pcs_indicators)


class DepoBangunanUnitParser:
    """Main unit parser for Depo Bangunan products."""
    
    def __init__(self):
        self.extractor = DepoBangunanUnitExtractor()
        self.spec_keywords = ['ukuran', 'size', 'dimensi', 'berat', 'weight', 'kapasitas', 'volume']
    
    def parse_unit_from_product_name(self, product_name: str) -> Optional[str]:
        """Parse unit from product name."""
        unit = self.extractor.extract_unit_from_name(product_name)
        
        # If unit is None or 'X', default to 'PCS'
        if unit is None or unit == 'X':
            return 'PCS'
        
        return unit
    
    def parse_unit_from_detail_page(self, html_content: str) -> Optional[str]:
        """Parse unit from product detail page HTML."""
        if not html_content or not isinstance(html_content, str):
            return 'PCS'  # Default to PCS if no content
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for specification tables
            tables = soup.find_all('table')
            for table in tables:
                unit = self._extract_unit_from_table(table)
                if unit and unit != 'X':
                    return unit
            
            # Look for specification divs or spans
            spec_elements = soup.find_all(['div', 'span'], string=re.compile(r'ukuran|size', re.IGNORECASE))
            for element in spec_elements:
                unit = self._extract_unit_near_element(element)
                if unit and unit != 'X':
                    return unit
            
            return 'PCS'  # Default to PCS if no unit found
            
        except Exception as e:
            logger.warning(f"Error parsing unit from detail page: {e}")
            return 'PCS'  # Default to PCS on error
    
    def _extract_unit_from_table(self, table) -> Optional[str]:
        """Extract unit from specification table."""
        try:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    # Check if key indicates size/unit specification
                    if any(keyword in key for keyword in self.spec_keywords):
                        unit = self.extractor.extract_unit_from_specification(value)
                        if unit:
                            return unit
            
            return None
        except Exception as e:
            logger.warning(f"Error extracting unit from table: {e}")
            return None
    
    def _extract_unit_near_element(self, element) -> Optional[str]:
        """Extract unit near a specification element."""
        try:
            # Check siblings and parent elements for unit information
            for sibling in element.next_siblings:
                if hasattr(sibling, 'get_text'):
                    text = sibling.get_text(strip=True)
                    unit = self.extractor.extract_unit_from_specification(text)
                    if unit:
                        return unit
            
            # Check parent element
            if element.parent:
                text = element.parent.get_text(strip=True)
                unit = self.extractor.extract_unit_from_specification(text)
                if unit:
                    return unit
            
            return None
        except Exception as e:
            logger.warning(f"Error extracting unit near element: {e}")
            return None