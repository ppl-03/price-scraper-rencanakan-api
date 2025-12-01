import re
from typing import Optional, Dict, List, Protocol
from bs4 import BeautifulSoup
from .logging_utils import get_mitra10_logger

logger = get_mitra10_logger("unit_parser")

# Unit type constants
UNIT_M2 = 'M²'
UNIT_CM2 = 'CM²'
UNIT_INCH2 = 'INCH²'
UNIT_MM2 = 'MM²'
UNIT_M3 = 'M³'
UNIT_CM3 = 'CM³'
UNIT_KG = 'KG'
UNIT_GRAM = 'GRAM'
UNIT_TON = 'TON'
UNIT_POUND = 'POUND'


class UnitConstants:
    """Centralized constants for all Mitra10 unit types and patterns"""
    
    # Unit categories for better organization
    AREA_UNITS = [UNIT_M2, UNIT_CM2, UNIT_INCH2, UNIT_MM2]
    VOLUME_UNITS = [UNIT_M3, UNIT_CM3, 'LITER', 'ML', 'GALLON']
    WEIGHT_UNITS = [UNIT_KG, UNIT_GRAM, UNIT_TON, UNIT_POUND]
    LENGTH_UNITS = ['M', 'CM', 'MM', 'INCH', 'FEET']
    ELECTRICAL_UNITS = ['WATT', 'KWH', 'VOLT', 'AMPERE', 'KVA', 'HP']
    COUNT_UNITS = ['PCS', 'SET', 'PACK', 'BOX', 'ROLL', 'SHEET', 'PAPAN', 'BATANG', 'LEMBAR', 'UNIT']
    TIME_UNITS = ['HARI', 'MINGGU', 'BULAN', 'TAHUN', 'JAM', 'MENIT', 'DETIK']
    PRESSURE_UNITS = ['PSI', 'BAR']
    SPEED_UNITS = ['MPH', 'KMH']
    
    @classmethod
    def get_all_priority_order(cls) -> List[str]:
        """Unified global priority order for all unit types"""
        return (
            cls.AREA_UNITS + cls.VOLUME_UNITS + cls.WEIGHT_UNITS + 
            cls.LENGTH_UNITS + cls.ELECTRICAL_UNITS + cls.COUNT_UNITS + 
            cls.TIME_UNITS + cls.PRESSURE_UNITS + cls.SPEED_UNITS
        )
    
    @classmethod
    def get_unit_patterns(cls) -> Dict[str, List[str]]:
        """Centralized unit pattern definitions"""
        return {
            # Length units
            'MM': ['mm', 'milimeter', 'millimeter'],
            'CM': ['cm', 'centimeter', 'sentimeter'],
            'M': ['meter', 'metre', r'm(?!m|l|g|²|³)'],
            'INCH': ['inch', 'inchi', '"', '″', 'inc'],
            'FEET': ['feet', 'ft', '\'', '′'],
            
            # Area units
            UNIT_CM2: ['cm²', 'cm2', 'centimeter persegi', 'sentimeter persegi'],
            UNIT_M2: ['m²', 'm2', 'meter persegi', 'square meter'],
            UNIT_INCH2: ['inch²', 'inch2', 'square inch', 'inchi persegi'],
            UNIT_MM2: ['mm²', 'mm2', 'milimeter persegi'],
            
            # Weight units
            UNIT_KG: ['kg', 'kilogram', 'kilo'],
            'GRAM': ['gram', 'gr', 'g(?!a)'],
            'TON': ['ton', 'tonnes'],
            'POUND': ['pound', 'lb', 'lbs', 'pon'],
            
            # Volume units
            'LITER': ['liter', 'litre', 'l(?!b|t)'],
            'ML': ['ml', 'mililiter', 'milliliter'],
            'GALLON': ['gallon', 'gal'],
            UNIT_M3: ['m³', 'm3', 'meter kubik', 'cubic meter'],
            UNIT_CM3: ['cm³', 'cm3', 'centimeter kubik', 'cubic centimeter'],
            
            # Electrical units
            'WATT': ['watt', 'w(?!a)', 'daya'],
            'VOLT': ['volt', 'v(?!a|e)'],
            'AMPERE': ['ampere', 'amp', 'a(?!l|r|n)'],
            'KWH': ['kwh', 'kilowatt hour', 'kilowatt-hour'],
            'KVA': ['kva', 'kilovolt ampere'],
            'HP': ['hp', 'horsepower', 'horse power'],
            
            # Count units
            'PCS': ['pcs', 'pieces', 'piece', 'buah', 'biji'],
            'SET': ['set', 'sets'],
            'PACK': ['pack', 'pak', 'kemasan'],
            'BOX': ['box', 'kotak', 'dus'],
            'ROLL': ['roll', 'gulungan', 'gulung'],
            'SHEET': ['sheet', 'lembar', 'lbr'],
            'PAPAN': ['papan', 'board', 'plank'],
            'BATANG': ['batang', 'bar', 'rod', 'stick'],
            'LEMBAR': ['lembar', 'sheet', 'lbr'],
            'UNIT': ['unit', 'units'],
            
            # Time units
            'HARI': ['hari', 'day', 'days'],
            'MINGGU': ['minggu', 'week', 'weeks'],
            'BULAN': ['bulan', 'month', 'months'],
            'TAHUN': ['tahun', 'year', 'years'],
            'JAM': ['jam', 'hour', 'hours', 'hr'],
            'MENIT': ['menit', 'minute', 'minutes', 'min'],
            'DETIK': ['detik', 'second', 'seconds', 'sec'],
            
            # Pressure and other units
            'PSI': ['psi', 'pound per square inch'],
            'BAR': ['bar', 'tekanan'],
            'MPH': ['mph', 'mile per hour'],
            'KMH': ['kmh', 'km/h', 'kilometer per hour']
        }
    
    @classmethod
    def get_unit_mappings(cls) -> Dict[str, str]:
        """Centralized unit mappings for normalization"""
        return {
            'mm': 'MM', 'cm': 'CM', 'kg': UNIT_KG, 'gr': UNIT_GRAM, 'ml': 'ML', 'lt': 'LITER', 
            'pcs': 'PCS', 'set': 'SET', 'inch': 'INCH', 'feet': 'FEET', 'watt': 'WATT', 
            'volt': 'VOLT', 'amp': 'AMPERE', 'hp': 'HP', 'bar': 'BAR', 'psi': 'PSI',
            'm': 'M', 'hari': 'HARI', 'minggu': 'MINGGU', 'bulan': 'BULAN', 'tahun': 'TAHUN', 
            'jam': 'JAM', 'hour': 'JAM', 'day': 'HARI', 'week': 'MINGGU', 'month': 'BULAN', 
            'year': 'TAHUN', 'sak': 'SAK', 'karung': 'SAK', 'bag': 'SAK', 'zak': 'SAK',
            'roll': 'ROLL', 'lembar': 'LEMBAR', 'sheet': 'SHEET', 'batang': 'BATANG', 'papan': 'PAPAN'
        }
    
    @classmethod
    def get_construction_keywords(cls) -> List[str]:
        """Centralized construction-related keywords"""
        return [
            'semen', 'cement', 'beton', 'concrete', 'besi', 'iron', 'steel',
            'kayu', 'wood', 'plywood', 'triplek', 'papan', 'board',
            'genteng', 'tile', 'atap', 'roof', 'dinding', 'wall',
            'lantai', 'floor', 'keramik', 'ceramic', 'granit', 'granite',
            'marmer', 'marble', 'cat', 'paint', 'pipa', 'pipe',
            'kabel', 'cable', 'wire', 'kawat', 'baut', 'bolt',
            'sekrup', 'screw', 'paku', 'nail', 'lem', 'glue',
            'pasir', 'sand', 'kerikil', 'gravel', 'batako', 'block'
        ]
    
    @classmethod
    def get_electrical_keywords(cls) -> List[str]:
        """Centralized electrical-related keywords"""
        return [
            'listrik', 'electric', 'kabel', 'cable', 'lampu', 'lamp',
            'saklar', 'switch', 'stop kontak', 'outlet', 'mcb',
            'circuit breaker', 'fuse', 'sekering', 'trafo', 'transformer',
            'genset', 'generator', 'inverter', 'ups', 'stabilizer',
            'fitting', 'socket', 'plug', 'colokan'
        ]
    
    @classmethod
    def get_plumbing_keywords(cls) -> List[str]:
        """Centralized plumbing-related keywords"""
        return [
            'pipa', 'pipe', 'pvc', 'fitting', 'elbow', 'tee', 'reducer',
            'kran', 'faucet', 'valve', 'katup', 'sambungan', 'joint',
            'seal', 'gasket', 'teflon', 'dop', 'cap', 'tutup'
        ]
    
    @classmethod
    def get_spec_keywords(cls) -> List[str]:
        """Centralized specification-related keywords"""
        return [
            'ukuran', 'dimensi', 'size', 'dimension', 'spesifikasi', 'specification',
            'berat', 'weight', 'kapasitas', 'capacity', 'daya', 'power', 'tegangan',
            'voltage', 'diameter', 'panjang', 'length', 'lebar', 'width', 'tinggi',
            'height', 'tebal', 'thickness', 'volume', 'isi', 'content', 'kemasan',
            'packaging', 'satuan', 'unit', 'per', 'setiap', 'each'
        ]


class TextProcessingHelper:
    """Helper class for common text processing operations"""
    
    @staticmethod
    def validate_and_clean_text(text: str, max_length: int = 5000) -> Optional[str]:
        """Validate and clean text input with smart truncation to preserve important parts"""
        if not text or not isinstance(text, str):
            return None
        
        text_cleaned = text.lower().strip()
        if not text_cleaned:
            return None
            
        if len(text_cleaned) > max_length:
            logger.warning(f"Text too long, truncating to {max_length} chars")
            # Smart truncation: keep first part and last part to preserve units at the end
            keep_start = max_length // 2
            keep_end = max_length - keep_start - 10  # Account for " ... " separator
            text_cleaned = text_cleaned[:keep_start] + " ... " + text_cleaned[-keep_end:]
            
        return text_cleaned
    
    @staticmethod
    def safe_regex_search(pattern: str, text: str, flags: int = re.IGNORECASE) -> Optional[re.Match]:
        """Safely perform regex search with error handling"""
        try:
            return re.search(pattern, text, flags)
        except re.error as e:
            logger.warning(f"Regex error with pattern '{pattern}': {e}")
            return None
    
    @staticmethod
    def safe_regex_finditer(pattern: str, text: str, flags: int = re.IGNORECASE):
        """Safely perform regex finditer with error handling"""
        try:
            return re.finditer(pattern, text, flags)
        except re.error as e:
            logger.warning(f"Regex error with pattern '{pattern}': {e}")
            return []


class ErrorHandlingMixin:
    """Mixin for consistent error handling across classes"""
    
    def safe_execute(self, operation, operation_name: str, *args, **kwargs):
        """Execute operation with consistent error handling"""
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {operation_name}: {e}")
            return None
    
    def safe_execute_with_default(self, operation, default_value, operation_name: str, *args, **kwargs):
        """Execute operation with default return value on error"""
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Error in {operation_name}: {e}")
            return default_value


class ContextChecker:
    """Helper class for checking text context against keyword lists"""
    
    @staticmethod
    def check_keywords_in_text(text: str, keywords: List[str], context_name: str) -> bool:
        """Check if any keywords are present in text"""
        try:
            if not text or not isinstance(text, str):
                return False
            text_lower = text.lower()
            return any(keyword in text_lower for keyword in keywords)
        except Exception as e:
            logger.warning(f"Error checking {context_name} context: {e}")
            return False


class Mitra10UnitPatternRepository:
    """Simplified repository using centralized constants"""
    
    def __init__(self):
        self._unit_patterns = UnitConstants.get_unit_patterns()
        self._priority_order = UnitConstants.get_all_priority_order()
    
    def get_patterns(self, unit: str) -> List[str]:
        return self._unit_patterns.get(unit, [])
    
    def get_all_units(self) -> List[str]:
        return list(self._unit_patterns.keys())
    
    def get_priority_order(self) -> List[str]:
        return self._priority_order.copy()


class Mitra10AreaPatternStrategy(ErrorHandlingMixin):
    
    def extract_unit(self, text_lower: str) -> Optional[str]:
        return self.safe_execute(self._extract_area_unit, "Mitra10 area pattern extraction", text_lower)
    
    def _extract_area_unit(self, text_lower: str) -> Optional[str]:
        # Pattern for area calculations like "60x60 cm"
        area_pattern = r'(\d{1,10}(?:[.,]\d{1,10})?)\s?[x×]\s?(\d{1,10}(?:[.,]\d{1,10})?)\s?(cm|mm|m|inch)(?:\s|$)'
        match = TextProcessingHelper.safe_regex_search(area_pattern, text_lower)
        if match:
            unit_key = match.group(3).lower()
            area_map = {'cm': UNIT_CM2, 'mm': UNIT_MM2, 'm': UNIT_M2, 'inch': UNIT_INCH2}
            return area_map.get(unit_key)
        
        return None


class Mitra10AdjacentPatternStrategy(ErrorHandlingMixin):
    """Simplified strategy using centralized constants"""
    
    def __init__(self):
        self.unit_mappings = UnitConstants.get_unit_mappings()
        
        # Centralized pattern definitions
        self.adjacent_patterns = [
            (r'(\d{1,10}(?:[.,]\d{1,10})?)(mm|cm|kg|gr|ml|lt|pcs|set|inch|feet|watt|volt|amp|hp|bar|psi)(?:\s|$)', 2),
            (r'diameter\s?(\d{1,10}(?:[.,]\d{1,10})?)\s?(mm|cm|m|inch)', 2), 
            (r'Ø\s?(\d{1,10}(?:[.,]\d{1,10})?)\s?(mm|cm|m|inch)', 2),
            (r'(\d{1,10}(?:[.,]\d{1,10})?)\s?/?(\bhari\b|\bminggu\b|\bulan\b|\btahun\b|\bjam\b|\bhour\b|\bday\b|\bweek\b|\bmonth\b|\byear\b)', 2),
            (r'(\d{1,10}(?:[.,]\d{1,10})?)\s?(sak|karung|bag|zak)(?:\s+semen|\s+cement)?', 2),
            (r'(\d{1,10}(?:[.,]\d{1,10})?)\s?(roll|lembar|sheet|batang|papan)', 2)
        ]
    
    def extract_unit(self, text_lower: str) -> Optional[str]:
        return self.safe_execute(self._extract_adjacent_unit, "Mitra10 adjacent pattern extraction", text_lower)
    
    def _extract_adjacent_unit(self, text_lower: str) -> Optional[str]:
        for pattern, group_index in self.adjacent_patterns:
            matches = TextProcessingHelper.safe_regex_finditer(pattern, text_lower)
            for match in matches:
                unit_result = self._process_match_group(match, group_index)
                if unit_result:
                    return unit_result
        return None
    
    def _process_match_group(self, match, group_index: int) -> Optional[str]:
        try:
            unit_key = match.group(group_index).lower()
            return self.unit_mappings.get(unit_key)
        except (IndexError, AttributeError) as e:
            logger.debug(f"Error processing Mitra10 match group: {e}")
            return None


class Mitra10UnitExtractor(ErrorHandlingMixin):
    
    def __init__(self, pattern_repository: Mitra10UnitPatternRepository = None):
        self._pattern_repository = pattern_repository or Mitra10UnitPatternRepository()
        self._area_pattern_strategy = Mitra10AreaPatternStrategy()
        self._adjacent_pattern_strategy = Mitra10AdjacentPatternStrategy()
    
    def extract_unit(self, text: str) -> Optional[str]:
        text_lower = TextProcessingHelper.validate_and_clean_text(text)
        if not text_lower:
            return None
        
        return self.safe_execute(self._extract_unit_from_text, "Mitra10 unit extraction", text_lower)
    
    def _extract_unit_from_text(self, text_lower: str) -> Optional[str]:
        # First, try area pattern (highest priority)
        area_unit = self._area_pattern_strategy.extract_unit(text_lower)
        if area_unit:
            return area_unit
        
        # Then, standard patterns with priority
        standard_unit = self._extract_by_priority_patterns(text_lower)
        if standard_unit:
            return standard_unit
        
        # Finally, adjacent patterns
        adjacent_unit = self._adjacent_pattern_strategy.extract_unit(text_lower)
        if adjacent_unit:
            return adjacent_unit
        
        return None
    
    def _extract_by_priority_patterns(self, text_lower: str) -> Optional[str]:
        return self.safe_execute(self._priority_pattern_search, "Mitra10 priority pattern extraction", text_lower)
    
    def _priority_pattern_search(self, text_lower: str) -> Optional[str]:
        text_processed = TextProcessingHelper.validate_and_clean_text(text_lower, 5000)
        if not text_processed:
            return None
        
        priority_order = self._pattern_repository.get_priority_order()
        
        for unit in priority_order:
            patterns = self._pattern_repository.get_patterns(unit)
            for pattern in patterns:
                if self._match_pattern_with_boundaries(pattern, text_processed):
                    return unit
        
        return None
    
    def _match_pattern_with_boundaries(self, pattern: str, text: str) -> bool:
        # Use word boundaries for better matching
        pattern_with_boundaries = f'(?:^|\\s|[\\(\\[{{]|\\d)({pattern})(?:\\s|[\\)\\]}}]|$)'
        match = TextProcessingHelper.safe_regex_search(pattern_with_boundaries, text)
        return match is not None


class Mitra10SpecificationFinder(ErrorHandlingMixin):
    """Simplified specification finder using centralized constants"""
    
    def __init__(self):
        self.spec_keywords = UnitConstants.get_spec_keywords()
    
    def find_specification_values(self, soup: BeautifulSoup) -> List[str]:
        specifications = []
        
        extraction_methods = [
            (self._extract_from_mitra10_elements, "Mitra10 specific specifications"),
            (self._extract_from_tables, "table specifications"),
            (self._extract_from_spans_and_divs, "span/div specifications")
        ]
        
        for method, method_name in extraction_methods:
            specs = self.safe_execute_with_default(method, [], method_name, soup)
            specifications.extend(specs)
        
        return specifications
    
    def _extract_from_mitra10_elements(self, soup: BeautifulSoup) -> List[str]:
        """Extract specifications from Mitra10-specific HTML elements"""
        specs = []
        
        desc_areas = self._find_description_areas(soup)
        for area in desc_areas:
            text = self._extract_text_safely(area)
            if text and len(text) > 10:
                specs.append(text)
        
        return specs
    
    def _find_description_areas(self, soup: BeautifulSoup):
        """Find product description areas with error handling"""
        try:
            return soup.find_all(['div', 'section'], class_=lambda x: x and any(
                keyword in x.lower() for keyword in ['product-info', 'product-detail', 'specification', 'deskripsi']
            ))
        except Exception as e:
            logger.warning(f"Error finding Mitra10 description areas: {e}")
            return []
    
    def _extract_text_safely(self, element) -> Optional[str]:
        """Safely extract text from HTML element"""
        try:
            return element.get_text(separator=' ', strip=True)
        except Exception as e:
            logger.debug(f"Error processing element: {e}")
            return None
    
    def _extract_from_tables(self, soup: BeautifulSoup) -> List[str]:
        specs = []
        tables = self._find_elements_safely(soup, 'table')
        for table in tables:
            table_specs = self._extract_specs_from_table(table)
            specs.extend(table_specs)
        return specs
    
    def _find_elements_safely(self, soup: BeautifulSoup, tag: str):
        """Safely find elements with error handling"""
        try:
            return soup.find_all(tag)
        except Exception as e:
            logger.warning(f"Error finding {tag} elements: {e}")
            return []
    
    def _extract_specs_from_table(self, table) -> List[str]:
        specs = []
        rows = self._find_elements_safely(table, 'tr')
        for row in rows:
            spec_value = self._extract_spec_from_row(row)
            if spec_value:
                specs.append(spec_value)
        return specs
    
    def _extract_spec_from_row(self, row) -> Optional[str]:
        try:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)
                
                if any(keyword in key for keyword in self.spec_keywords):
                    return value
        except (AttributeError, IndexError) as e:
            logger.debug(f"Error processing table row: {e}")
        return None
    
    def _extract_from_spans_and_divs(self, soup: BeautifulSoup) -> List[str]:
        specs = []
        
        # Extract from spans
        spans = self._find_elements_safely(soup, 'span')
        specs.extend(self._extract_from_elements(spans, 'span'))
        
        # Extract from divs with specification-related classes
        spec_divs = self._find_spec_divs(soup)
        specs.extend(self._extract_from_elements(spec_divs, 'div'))
        
        return specs
    
    def _find_spec_divs(self, soup: BeautifulSoup):
        """Find divs with specification-related classes"""
        try:
            return soup.find_all('div', class_=lambda x: x and any(
                keyword in x.lower() for keyword in ['spec', 'detail', 'info', 'description', 'produk']
            ))
        except Exception as e:
            logger.warning(f"Error finding spec divs: {e}")
            return []
    
    def _extract_from_elements(self, elements, element_type: str) -> List[str]:
        """Extract specifications from a list of elements"""
        specs = []
        for element in elements:
            text = self._extract_text_safely(element)
            if self._is_valid_spec_text(text, element_type):
                specs.append(text)
        return specs
    
    def _is_valid_spec_text(self, text: str, element_type: str) -> bool:
        """Check if text is valid for specification extraction"""
        if not text:
            return False
        
        if element_type == 'span':
            return any(keyword in text.lower() for keyword in self.spec_keywords)
        elif element_type == 'div':
            return len(text) > 5
        
        return False


class Mitra10UnitParserConfiguration:
    """Simplified configuration using centralized constants"""
    
    def is_construction_context(self, text: str) -> bool:
        return ContextChecker.check_keywords_in_text(text, UnitConstants.get_construction_keywords(), "Mitra10 construction")
    
    def is_electrical_context(self, text: str) -> bool:
        return ContextChecker.check_keywords_in_text(text, UnitConstants.get_electrical_keywords(), "Mitra10 electrical")
    
    def is_plumbing_context(self, text: str) -> bool:
        return ContextChecker.check_keywords_in_text(text, UnitConstants.get_plumbing_keywords(), "Mitra10 plumbing")


class Mitra10UnitParser(ErrorHandlingMixin):
    def __init__(self, 
                 extractor: Mitra10UnitExtractor = None,
                 spec_finder: Mitra10SpecificationFinder = None,
                 config: Mitra10UnitParserConfiguration = None):
        self.extractor = extractor or Mitra10UnitExtractor()
        self.spec_finder = spec_finder or Mitra10SpecificationFinder()
        self.config = config or Mitra10UnitParserConfiguration()
    
    def parse_unit(self, html_content: str) -> Optional[str]:
        clean_content = TextProcessingHelper.validate_and_clean_text(html_content, max_length=50000)
        if not clean_content:
            return 'PCS'
        
        unit = self.safe_execute(self._parse_unit_from_html, "Mitra10 unit parsing", html_content)
        return unit if unit else 'PCS'
    
    def _parse_unit_from_html(self, html_content: str) -> Optional[str]:
        soup = self._create_soup_safely(html_content)
        if not soup:
            return None
        
        # Extract specifications from HTML
        specifications = self._extract_specifications_safely(soup)
        
        # Extract units from specifications
        found_units = self._extract_units_from_specifications(specifications)
        
        # Apply Mitra10-specific priority rules
        prioritized_unit = self._apply_mitra10_priority_rules(found_units, html_content)
        if prioritized_unit:
            return prioritized_unit
        
        # Fallback to full text extraction
        return self._extract_from_full_text(soup)
    
    def _create_soup_safely(self, html_content: str) -> Optional[BeautifulSoup]:
        return self.safe_execute_with_default(
            lambda: BeautifulSoup(html_content, 'html.parser'), 
            None, 
            "creating soup from Mitra10 HTML"
        )
    
    def _extract_specifications_safely(self, soup: BeautifulSoup) -> List[str]:
        return self.safe_execute_with_default(
            self.spec_finder.find_specification_values, 
            [], 
            "extracting Mitra10 specifications", 
            soup
        )
    
    def _extract_units_from_specifications(self, specifications: List[str]) -> List[str]:
        found_units = []
        for spec in specifications:
            unit = self.safe_execute(self.extractor.extract_unit, f"extracting unit from spec '{spec[:50]}...'", spec)
            if unit:
                found_units.append(unit)
        
        return found_units
    
    def _apply_mitra10_priority_rules(self, found_units: List[str], html_content: str) -> Optional[str]:
        """Apply Mitra10-specific priority rules based on product context"""
        if not found_units:
            return None
        
        # Filter out empty or None units to get a valid fallback
        valid_units = [unit for unit in found_units if unit and unit.strip()]
        fallback_unit = valid_units[0] if valid_units else None
        
        return self.safe_execute_with_default(
            self._get_prioritized_unit, 
            fallback_unit, 
            "applying Mitra10 priority rules", 
            found_units, 
            html_content
        )
    
    def _get_prioritized_unit(self, found_units: List[str], html_content: str) -> Optional[str]:
        # Context-based priority
        context_unit = self._get_context_specific_unit(found_units, html_content)
        if context_unit:
            return context_unit
        
        # General priority order
        return self._get_general_priority_unit(found_units)
    
    def _get_context_specific_unit(self, found_units: List[str], html_content: str) -> Optional[str]:
        """Get unit based on product context (construction, electrical, plumbing)"""
        if self.config.is_construction_context(html_content):
            return self._find_unit_in_groups(found_units, [
                [UNIT_M2, UNIT_CM2, UNIT_INCH2, UNIT_MM2],  # Area units first
                [UNIT_M3, UNIT_CM3],                        # Volume units
                [UNIT_KG, UNIT_GRAM, 'SAK', 'TON']          # Weight units
            ])
        
        if self.config.is_electrical_context(html_content):
            electrical_units = ['WATT', 'VOLT', 'AMPERE', 'KWH', 'KVA', 'HP']
            return self._find_first_match(found_units, electrical_units)
        
        if self.config.is_plumbing_context(html_content):
            length_units = ['M', 'CM', 'MM', 'INCH', 'FEET']
            return self._find_first_match(found_units, length_units)
        
        return None
    
    def _get_general_priority_unit(self, found_units: List[str]) -> Optional[str]:
        """Get unit based on general priority order"""
        priority_order = [
            UNIT_M2, UNIT_CM2, UNIT_INCH2, UNIT_MM2,  # Area units
            UNIT_M3, UNIT_CM3,                        # Volume units
            UNIT_KG, UNIT_GRAM, UNIT_TON, UNIT_POUND, # Weight units
            'M', 'CM', 'MM', 'INCH', 'FEET',          # Length units
            'PCS', 'SET', 'PACK', 'BOX', 'ROLL',      # Count units
            'LITER', 'ML', 'GALLON'                   # Volume liquid units
        ]
        
        for unit_type in priority_order:
            if unit_type in found_units:
                return unit_type
        
        return found_units[0]  # Return first found unit if no priority match
    
    def _find_unit_in_groups(self, found_units: List[str], unit_groups: List[List[str]]) -> Optional[str]:
        """Find first matching unit from prioritized groups"""
        for group in unit_groups:
            found_unit = self._find_first_match(found_units, group)
            if found_unit:
                return found_unit
        return None
    
    def _find_first_match(self, found_units: List[str], target_units: List[str]) -> Optional[str]:
        """Find first unit from found_units that matches any in target_units"""
        for unit in found_units:
            if unit in target_units:
                return unit
        return None
    
    def _extract_from_full_text(self, soup: BeautifulSoup) -> Optional[str]:
        return self.safe_execute_with_default(
            lambda: self.extractor.extract_unit(soup.get_text()), 
            None, 
            "extracting from Mitra10 full text"
        )