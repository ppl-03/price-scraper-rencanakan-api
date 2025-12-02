import re
import logging
from typing import Optional, Dict, List, Tuple, Protocol
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from .logging_utils import get_gemilang_logger

logger = get_gemilang_logger("unit_parser")

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


class UnitExtractionStrategy(Protocol):
    
    def extract_unit(self, text: str) -> Optional[str]:
        ...


class UnitPatternRepository:
    
    def __init__(self):
        self._unit_patterns = self._initialize_patterns()
        self._priority_order = self._initialize_priority_order()
    
    def _initialize_patterns(self) -> Dict[str, List[str]]:
        return {
            'MM': ['mm', 'milimeter', 'millimeter'],
            'CM': ['cm', 'centimeter', 'sentimeter'],
            'M': ['meter', 'metre', r'm(?!m|l|g|²|³)'],
            'INCH': ['inch', 'inchi', '"', '″'],
            'FEET': ['feet', 'ft', '\'', '′'],
            UNIT_CM2: ['cm²', 'cm2', 'centimeter persegi', 'sentimeter persegi'],
            UNIT_M2: ['m²', 'm2', 'meter persegi', 'square meter'],
            UNIT_INCH2: ['inch²', 'inch2', 'square inch', 'inchi persegi'],
            UNIT_KG: ['kg', 'kilogram', 'kilo'],
            'GRAM': ['gram', 'gr', 'g(?!a)'],
            'TON': ['ton', 'tonnes'],
            'POUND': ['pound', 'lb', 'lbs', 'pon'],
            'LITER': ['liter', 'litre', 'l(?!b|t)'],
            'ML': ['ml', 'mililiter', 'milliliter'],
            'GALLON': ['gallon', 'gal'],
            'M³': ['m³', 'm3', 'meter kubik', 'cubic meter'],
            'CM³': ['cm³', 'cm3', 'centimeter kubik', 'cubic centimeter'],
            'WATT': ['watt', 'w(?!a)', 'daya'],
            'VOLT': ['volt', 'v(?!a|e)'],
            'AMPERE': ['ampere', 'amp', 'a(?!l|r|n)'],
            'KWH': ['kwh', 'kilowatt hour', 'kilowatt-hour'],
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
            'HARI': ['hari', 'day', 'days'],
            'MINGGU': ['minggu', 'week', 'weeks'],
            'BULAN': ['bulan', 'month', 'months'],
            'TAHUN': ['tahun', 'year', 'years'],
            'JAM': ['jam', 'hour', 'hours', 'hr'],
            'MENIT': ['menit', 'minute', 'minutes', 'min'],
            'DETIK': ['detik', 'second', 'seconds', 'sec'],
            'KVA': ['kva', 'kilovolt ampere'],
            'HP': ['hp', 'horsepower', 'horse power'],
            'PSI': ['psi', 'pound per square inch'],
            'BAR': ['bar', 'tekanan'],
            'MPH': ['mph', 'mile per hour'],
            'KMH': ['kmh', 'km/h', 'kilometer per hour']
        }
    
    def _initialize_priority_order(self) -> List[str]:
        return [
            UNIT_M2, UNIT_CM2, UNIT_INCH2, UNIT_MM2,
            UNIT_M3, UNIT_CM3,
            UNIT_KG, UNIT_GRAM, UNIT_TON, UNIT_POUND,
            'M', 'CM', 'MM', 'INCH', 'FEET',
            'LITER', 'ML', 'GALLON',
            'WATT', 'KWH', 'VOLT', 'AMPERE', 'KVA', 'HP',
            'PCS', 'SET', 'PACK', 'BOX', 'ROLL', 'SHEET', 'PAPAN', 'BATANG', 'LEMBAR', 'UNIT',
            'HARI', 'MINGGU', 'BULAN', 'TAHUN', 'JAM', 'MENIT', 'DETIK',
            'PSI', 'BAR', 'MPH', 'KMH'
        ]
    
    def get_patterns(self, unit: str) -> List[str]:
        return self._unit_patterns.get(unit, [])
    
    def get_all_units(self) -> List[str]:
        return list(self._unit_patterns.keys())
    
    def get_priority_order(self) -> List[str]:
        return self._priority_order.copy()


class AreaPatternStrategy:
    
    def extract_unit(self, text_lower: str) -> Optional[str]:
        try:
            area_pattern = r'(\d{1,10}(?:[.,]\d{1,10})?)\s?[x×]\s?(\d{1,10}(?:[.,]\d{1,10})?)\s?(cm|mm|m|inch)(?:\s|$)'
            match = re.search(area_pattern, text_lower, re.IGNORECASE)
            if match:
                unit_key = match.group(3).lower()
                area_map = {'cm': UNIT_CM2, 'mm': UNIT_MM2, 'm': UNIT_M2, 'inch': UNIT_INCH2}
                return area_map.get(unit_key)
            
            return None
            
        except re.error as e:
            logger.warning("Regex error in area pattern extraction: %s", e)
            return None
        except Exception as e:
            logger.error("Unexpected error in area pattern extraction: %s", e)
            return None


class AdjacentPatternStrategy:
    
    def extract_unit(self, text_lower: str) -> Optional[str]:
        try:
            adjacent_patterns = [
                (r'(\d{1,10}(?:[.,]\d{1,10})?)(mm|cm|kg|gr|ml|lt|pcs|set|inch|feet|watt|volt|amp|hp|bar|psi)(?:\s|$)', 
                 {'mm': 'MM', 'cm': 'CM', 'kg': UNIT_KG, 'gr': UNIT_GRAM, 'ml': 'ML', 'lt': 'LITER', 
                  'pcs': 'PCS', 'set': 'SET', 'inch': 'INCH', 'feet': 'FEET', 'watt': 'WATT', 
                  'volt': 'VOLT', 'amp': 'AMPERE', 'hp': 'HP', 'bar': 'BAR', 'psi': 'PSI'}),
                (r'(\d{1,10}(?:[.,]\d{1,10})?)\s?diameter\s?(mm|cm|m|inch)', 
                 {'mm': 'MM', 'cm': 'CM', 'm': 'M', 'inch': 'INCH'}),
                (r'Ø\s?(\d{1,10}(?:[.,]\d{1,10})?)\s?(mm|cm|m|inch)', 
                 {'mm': 'MM', 'cm': 'CM', 'm': 'M', 'inch': 'INCH'}),
                (r'(\d{1,10}(?:[.,]\d{1,10})?)\s?/?(\bhari\b|\bminggu\b|\bulan\b|\btahun\b|\bjam\b|\bhour\b|\bday\b|\bweek\b|\bmonth\b|\byear\b)', 
                 {'hari': 'HARI', 'minggu': 'MINGGU', 'bulan': 'BULAN', 'tahun': 'TAHUN', 'jam': 'JAM',
                  'hour': 'JAM', 'day': 'HARI', 'week': 'MINGGU', 'month': 'BULAN', 'year': 'TAHUN'})
            ]
            
            for pattern, unit_map in adjacent_patterns:
                try:
                    matches = re.finditer(pattern, text_lower, re.IGNORECASE)
                    for match in matches:
                        try:
                            unit_key = match.group(-1).lower()
                            if unit_key in unit_map:
                                return unit_map[unit_key]
                        except (IndexError, AttributeError) as e:
                            logger.warning("Error processing match group: %s", e)
                            continue
                except re.error as e:
                    logger.warning("Invalid regex pattern: %s, error: %s", pattern, e)
                    continue
            
            return None
            
        except Exception as e:
            logger.error("Unexpected error in adjacent pattern extraction: %s", e)
            return None


class UnitExtractor:
    
    def __init__(self, pattern_repository: UnitPatternRepository = None):
        self._pattern_repository = pattern_repository or UnitPatternRepository()
        self._area_pattern_strategy = AreaPatternStrategy()
        self._adjacent_pattern_strategy = AdjacentPatternStrategy()
    
    def extract_unit(self, text: str) -> Optional[str]:
        if not text or not isinstance(text, str):
            return None
        
        try:
            text_lower = text.lower().strip()
            if not text_lower:
                return None
            
            area_unit = self._area_pattern_strategy.extract_unit(text_lower)
            if area_unit:
                return area_unit
            
            standard_unit = self._extract_by_priority_patterns(text_lower)
            if standard_unit:
                return standard_unit
            
            adjacent_unit = self._adjacent_pattern_strategy.extract_unit(text_lower)
            if adjacent_unit:
                return adjacent_unit
            
            return None
            
        except Exception as e:
            logger.warning("Error during unit extraction: %s", e)
            return None
    
    def _extract_by_priority_patterns(self, text_lower: str) -> Optional[str]:
        try:
            if len(text_lower) > 5000:
                logger.warning("Text too long for pattern extraction, truncating to 5000 chars")
                text_lower = text_lower[:5000]
            
            priority_order = self._pattern_repository.get_priority_order()
            
            for unit in priority_order:
                patterns = self._pattern_repository.get_patterns(unit)
                for pattern in patterns:
                    try:
                        pattern_with_boundaries = f'(?:^|\\s|[\\(\\[{{]|\\d)({pattern})(?:\\s|[\\)\\]}}]|$)'
                        if re.search(pattern_with_boundaries, text_lower, re.IGNORECASE):
                            return unit
                    except re.error as e:
                        logger.warning("Invalid regex pattern '%s' for unit '%s': %s", pattern, unit, e)
                        continue
            
            return None
            
        except Exception as e:
            logger.error("Error in priority pattern extraction: %s", e)
            return None

    def _extract_area_units(self, text_lower: str) -> Optional[str]:
        return self._area_pattern_strategy.extract_unit(text_lower)

    @property 
    def priority_order(self) -> List[str]:
        return self._pattern_repository.get_priority_order()

    @property
    def unit_patterns(self) -> Dict[str, List[str]]:
        return {unit: self._pattern_repository.get_patterns(unit) 
                for unit in self._pattern_repository.get_all_units()}


class SpecificationFinder:
    
    def __init__(self):
        self.spec_keywords = [
            'ukuran', 'dimensi', 'size', 'dimension', 'spesifikasi', 'specification',
            'berat', 'weight', 'kapasitas', 'capacity', 'daya', 'power', 'tegangan',
            'voltage', 'diameter', 'panjang', 'length', 'lebar', 'width', 'tinggi',
            'height', 'tebal', 'thickness', 'volume', 'isi', 'content'
        ]
    
    def find_specification_values(self, soup: BeautifulSoup) -> List[str]:
        """Extract specifications in a single DOM traversal for better performance"""
        specifications = []
        
        try:
            # Single pass: find all relevant elements at once
            # This reduces DOM traversal overhead
            table_specs = self._extract_from_tables(soup)
            specifications.extend(table_specs)
        except Exception as e:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("Error extracting table specifications: %s", e)
        
        try:
            span_specs = self._extract_from_spans(soup)
            specifications.extend(span_specs)
        except Exception as e:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("Error extracting span specifications: %s", e)
        
        try:
            div_specs = self._extract_from_divs(soup)
            specifications.extend(div_specs)
        except Exception as e:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("Error extracting div specifications: %s", e)
        
        return specifications
    
    def _extract_from_tables(self, soup: BeautifulSoup) -> List[str]:
        specs = []
        try:
            tables = soup.find_all('table')
            for table in tables:
                table_specs = self._extract_specs_from_table(table)
                specs.extend(table_specs)
        except Exception as e:
            logger.warning("Error finding tables: %s", e)
        
        return specs
    
    def _extract_specs_from_table(self, table) -> List[str]:
        specs = []
        try:
            rows = table.find_all('tr')
            for row in rows:
                spec_value = self._extract_spec_from_row(row)
                if spec_value:
                    specs.append(spec_value)
        except Exception as e:
            logger.debug("Error processing table: %s", e)
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
            logger.debug("Error processing table row: %s", e)
        return None
    
    def _extract_from_spans(self, soup: BeautifulSoup) -> List[str]:
        specs = []
        try:
            spans = soup.find_all('span')
            
            for span in spans:
                try:
                    text = span.get_text(strip=True)
                    if text and any(keyword in text.lower() for keyword in self.spec_keywords):
                        specs.append(text)
                except AttributeError as e:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("Error processing span: %s", e)
                    continue
        except Exception as e:
            logger.warning("Error finding spans: %s", e)
        
        return specs
    
    def _extract_from_divs(self, soup: BeautifulSoup) -> List[str]:
        specs = []
        try:
            spec_divs = soup.find_all('div', class_=lambda x: x and any(
                keyword in x.lower() for keyword in ['spec', 'detail', 'info', 'description']
            ))
            
            for div in spec_divs:
                try:
                    text = div.get_text(strip=True)
                    if text:
                        specs.append(text)
                except AttributeError as e:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("Error processing div: %s", e)
                    continue
        except Exception as e:
            logger.warning("Error finding divs: %s", e)
        
        return specs


class UnitParserConfiguration:
    
    def __init__(self):
        self.construction_keywords = [
            'semen', 'cement', 'beton', 'concrete', 'besi', 'iron', 'steel',
            'kayu', 'wood', 'plywood', 'triplek', 'papan', 'board',
            'genteng', 'tile', 'atap', 'roof', 'dinding', 'wall',
            'lantai', 'floor', 'keramik', 'ceramic', 'granit', 'granite',
            'marmer', 'marble', 'cat', 'paint', 'pipa', 'pipe',
            'kabel', 'cable', 'wire', 'kawat', 'baut', 'bolt',
            'sekrup', 'screw', 'paku', 'nail'
        ]
        
        self.electrical_keywords = [
            'listrik', 'electric', 'kabel', 'cable', 'lampu', 'lamp',
            'saklar', 'switch', 'stop kontak', 'outlet', 'mcb',
            'circuit breaker', 'fuse', 'sekering', 'trafo', 'transformer',
            'genset', 'generator', 'inverter', 'ups', 'stabilizer'
        ]
    
    def is_construction_context(self, text: str) -> bool:
        try:
            if not text or not isinstance(text, str):
                return False
            text_lower = text.lower()
            return any(keyword in text_lower for keyword in self.construction_keywords)
        except Exception as e:
            logger.warning("Error checking construction context: %s", e)
            return False
    
    def is_electrical_context(self, text: str) -> bool:
        try:
            if not text or not isinstance(text, str):
                return False
            text_lower = text.lower()
            return any(keyword in text_lower for keyword in self.electrical_keywords)
        except Exception as e:
            logger.warning("Error checking electrical context: %s", e)
            return False


class GemilangUnitParser:
    
    def __init__(self, extractor: UnitExtractor = None, 
                 spec_finder: SpecificationFinder = None,
                 config: UnitParserConfiguration = None):
        self.extractor = extractor or UnitExtractor()
        self.spec_finder = spec_finder or SpecificationFinder()
        self.config = config or UnitParserConfiguration()
    
    def parse_unit_from_element(self, element) -> Optional[str]:
        """Parse unit directly from BeautifulSoup element (optimized - avoids string conversion)"""
        if element is None:
            return None
        
        try:
            # Extract text directly from element - much faster than str(element)
            specifications = self._extract_specifications_from_element(element)
            found_units = self._extract_units_from_specifications(specifications)
            prioritized_unit = self._apply_priority_rules(found_units)
            if prioritized_unit:
                return prioritized_unit
            
            # Fallback to full text extraction
            full_text = element.get_text()
            return self.extractor.extract_unit(full_text)
            
        except Exception as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error("Unexpected error in unit parsing from element: %s", e)
            return None
    
    def _extract_specifications_from_element(self, element) -> List[str]:
        """Extract specifications directly from element without creating soup"""
        specifications = []
        try:
            # Get text from specific elements within the item
            for tag in ['p', 'span', 'div']:
                elements = element.find_all(tag)
                for el in elements:
                    text = el.get_text(strip=True)
                    if text and len(text) < 200:  # Only process reasonable length text
                        specifications.append(text)
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Error extracting specifications from element: %s", e)
        return specifications
    
    def parse_unit(self, html_content: str) -> Optional[str]:
        if not html_content or not isinstance(html_content, str):
            return None
        
        try:
            soup = self._create_soup_safely(html_content)
            if not soup:
                return None
            
            specifications = self._extract_specifications_safely(soup)
            found_units = self._extract_units_from_specifications(specifications)
            prioritized_unit = self._apply_priority_rules(found_units)
            if prioritized_unit:
                return prioritized_unit
            
            return self._extract_from_full_text(soup)
            
        except Exception as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error("Unexpected error in unit parsing: %s", e)
            return None
    
    def _create_soup_safely(self, html_content: str) -> Optional[BeautifulSoup]:
        try:
            return BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            logger.warning("Error creating soup from HTML: %s", e)
            return None
    
    def _extract_specifications_safely(self, soup: BeautifulSoup) -> List[str]:
        try:
            return self.spec_finder.find_specification_values(soup)
        except Exception as e:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("Error extracting specifications: %s", e)
            return []
    
    def _extract_units_from_specifications(self, specifications: List[str]) -> List[str]:
        found_units = []
        for spec in specifications:
            try:
                unit = self.extractor.extract_unit(spec)
                if unit:
                    found_units.append(unit)
            except Exception as e:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Error extracting unit from spec '%s': %s", spec, e)
                continue
        
        return found_units
    
    def _apply_priority_rules(self, found_units: List[str]) -> Optional[str]:
        if not found_units:
            return None
        
        try:
            # Use sets for faster membership testing
            area_units = {UNIT_M2, UNIT_CM2, UNIT_INCH2, UNIT_MM2}
            volume_units = {UNIT_M3, UNIT_CM3}
            weight_units = {UNIT_KG, UNIT_GRAM, UNIT_TON, UNIT_POUND}
            
            for unit in found_units:
                if unit in area_units:
                    return unit
            
            for unit in found_units:
                if unit in volume_units:
                    return unit
            
            for unit in found_units:
                if unit in weight_units:
                    return unit
            
            return found_units[0]
            
        except Exception as e:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("Error applying priority rules: %s", e)
            return found_units[0] if found_units else None
    
    def _extract_from_full_text(self, soup: BeautifulSoup) -> Optional[str]:
        try:
            full_text = soup.get_text()
            return self.extractor.extract_unit(full_text)
        except Exception as e:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("Error extracting from full text: %s", e)
            return None
