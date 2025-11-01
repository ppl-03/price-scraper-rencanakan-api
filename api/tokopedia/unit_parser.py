import re
import logging
from typing import Optional, Dict, List, Protocol
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

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
    """Protocol for unit extraction strategies."""
    
    def extract_unit(self, text: str) -> Optional[str]:
        ...


class UnitPatternRepository:
    """Repository for unit patterns and priority ordering - Tokopedia specific."""
    
    def __init__(self):
        self._unit_patterns = self._build_unit_patterns()
        self._priority_order = self._build_priority_order()
    
    def _build_unit_patterns(self) -> Dict[str, List[str]]:
        """Build all unit pattern mappings for Tokopedia."""
        # Combine all pattern groups
        patterns = {}
        patterns.update(self._get_length_patterns())
        patterns.update(self._get_area_patterns())
        patterns.update(self._get_volume_patterns())
        patterns.update(self._get_weight_patterns())
        patterns.update(self._get_liquid_patterns())
        patterns.update(self._get_electrical_patterns())
        patterns.update(self._get_quantity_patterns())
        patterns.update(self._get_time_patterns())
        patterns.update(self._get_pressure_patterns())
        patterns.update(self._get_speed_patterns())
        return patterns
    
    def _get_length_patterns(self) -> Dict[str, List[str]]:
        """Length measurement patterns."""
        return {
            'MM': ['mm', 'milimeter', 'millimeter'],
            'CM': ['cm', 'centimeter', 'sentimeter'],
            'M': ['meter', 'metre', r'm(?!m|l|g|²|³)'],
            'INCH': ['inch', 'inchi', '"', '″'],
            'FEET': ['feet', 'ft', '\'', '′'],
        }
    
    def _get_area_patterns(self) -> Dict[str, List[str]]:
        """Area measurement patterns."""
        return {
            UNIT_CM2: ['cm²', 'cm2', 'centimeter persegi', 'sentimeter persegi'],
            UNIT_M2: ['m²', 'm2', 'meter persegi', 'square meter'],
            UNIT_INCH2: ['inch²', 'inch2', 'square inch', 'inchi persegi'],
        }
    
    def _get_volume_patterns(self) -> Dict[str, List[str]]:
        """Volume measurement patterns."""
        return {
            'M³': ['m³', 'm3', 'meter kubik', 'cubic meter'],
            'CM³': ['cm³', 'cm3', 'centimeter kubik', 'cubic centimeter'],
        }
    
    def _get_weight_patterns(self) -> Dict[str, List[str]]:
        """Weight measurement patterns."""
        return {
            UNIT_KG: ['kg', 'kilogram', 'kilo'],
            'GRAM': ['gram', 'gr', 'g(?!a)'],
            'TON': ['ton', 'tonnes'],
            'POUND': ['pound', 'lb', 'lbs', 'pon'],
        }
    
    def _get_liquid_patterns(self) -> Dict[str, List[str]]:
        """Liquid measurement patterns."""
        return {
            'LITER': ['liter', 'litre', 'l(?!b|t)'],
            'ML': ['ml', 'mililiter', 'milliliter'],
            'GALLON': ['gallon', 'gal'],
        }
    
    def _get_electrical_patterns(self) -> Dict[str, List[str]]:
        """Electrical measurement patterns."""
        return {
            'WATT': ['watt', 'w(?!a)', 'daya'],
            'VOLT': ['volt', 'v(?!a|e)'],
            'AMPERE': ['ampere', 'amp', 'a(?!l|r|n)'],
            'KWH': ['kwh', 'kilowatt hour', 'kilowatt-hour'],
            'KVA': ['kva', 'kilovolt ampere'],
            'HP': ['hp', 'horsepower', 'horse power'],
        }
    
    def _get_quantity_patterns(self) -> Dict[str, List[str]]:
        """Quantity/packaging patterns."""
        return {
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
        }
    
    def _get_time_patterns(self) -> Dict[str, List[str]]:
        """Time measurement patterns."""
        return {
            'HARI': ['hari', 'day', 'days'],
            'MINGGU': ['minggu', 'week', 'weeks'],
            'BULAN': ['bulan', 'month', 'months'],
            'TAHUN': ['tahun', 'year', 'years'],
            'JAM': ['jam', 'hour', 'hours', 'hr'],
            'MENIT': ['menit', 'minute', 'minutes', 'min'],
            'DETIK': ['detik', 'second', 'seconds', 'sec'],
        }
    
    def _get_pressure_patterns(self) -> Dict[str, List[str]]:
        """Pressure measurement patterns."""
        return {
            'PSI': ['psi', 'pound per square inch'],
            'BAR': ['bar', 'tekanan'],
        }
    
    def _get_speed_patterns(self) -> Dict[str, List[str]]:
        """Speed measurement patterns."""
        return {
            'MPH': ['mph', 'mile per hour'],
            'KMH': ['kmh', 'km/h', 'kilometer per hour'],
        }
    
    def _build_priority_order(self) -> List[str]:
        """Build priority order for unit detection."""
        return [
            # Area units (highest priority)
            UNIT_M2, UNIT_CM2, UNIT_INCH2, UNIT_MM2,
            # Volume units
            UNIT_M3, UNIT_CM3,
            # Weight units
            UNIT_KG, UNIT_GRAM, UNIT_TON, UNIT_POUND,
            # Length units
            'M', 'CM', 'MM', 'INCH', 'FEET',
            # Liquid units
            'LITER', 'ML', 'GALLON',
            # Electrical units
            'WATT', 'KWH', 'VOLT', 'AMPERE', 'KVA', 'HP',
            # Quantity units
            'PCS', 'SET', 'PACK', 'BOX', 'ROLL', 'SHEET', 'PAPAN', 'BATANG', 'LEMBAR', 'UNIT',
            # Time units
            'HARI', 'MINGGU', 'BULAN', 'TAHUN', 'JAM', 'MENIT', 'DETIK',
            # Pressure and speed units
            'PSI', 'BAR', 'MPH', 'KMH'
        ]
    
    def get_patterns(self, unit: str) -> List[str]:
        """Get patterns for a specific unit."""
        return self._unit_patterns.get(unit, [])
    
    def get_all_units(self) -> List[str]:
        """Get all available units."""
        return list(self._unit_patterns.keys())
    
    def get_priority_order(self) -> List[str]:
        """Get priority order copy for unit detection."""
        return self._priority_order.copy()


class AreaPatternStrategy:
    """Strategy for extracting area units from patterns like '10 x 20 cm'."""
    
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
            logger.warning(f"Regex error in area pattern extraction: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in area pattern extraction: {e}")
            return None


class AdjacentPatternStrategy:
    """Strategy for extracting units adjacent to numbers (e.g., '100mm', '5kg')."""
    
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
                            logger.warning(f"Error processing match group: {e}")
                            continue
                except re.error as e:
                    logger.warning(f"Invalid regex pattern: {pattern}, error: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error in adjacent pattern extraction: {e}")
            return None


class UnitExtractor:
    """Main unit extractor that applies multiple strategies."""
    
    def __init__(self, pattern_repository: UnitPatternRepository = None):
        self._pattern_repository = pattern_repository or UnitPatternRepository()
        self._area_pattern_strategy = AreaPatternStrategy()
        self._adjacent_pattern_strategy = AdjacentPatternStrategy()
    
    def extract_unit(self, text: str) -> Optional[str]:
        """
        Extract unit from text using multiple strategies.
        
        Args:
            text: Text to extract unit from
            
        Returns:
            Detected unit or None
        """
        if not text or not isinstance(text, str):
            return None
        
        try:
            text_lower = text.lower().strip()
            if not text_lower:
                return None
            
            # Try area patterns first (e.g., "10 x 20 cm")
            area_unit = self._area_pattern_strategy.extract_unit(text_lower)
            if area_unit:
                return area_unit
            
            # Try standard patterns with priority ordering
            standard_unit = self._extract_by_priority_patterns(text_lower)
            if standard_unit:
                return standard_unit
            
            # Try adjacent number patterns (e.g., "100mm", "5kg")
            adjacent_unit = self._adjacent_pattern_strategy.extract_unit(text_lower)
            if adjacent_unit:
                return adjacent_unit
            
            return None
            
        except Exception as e:
            logger.warning(f"Error during unit extraction: {e}")
            return None
    
    def _extract_by_priority_patterns(self, text_lower: str) -> Optional[str]:
        """Extract unit using priority-ordered patterns."""
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
                        logger.warning(f"Invalid regex pattern '{pattern}' for unit '{unit}': {e}")
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error in priority pattern extraction: {e}")
            return None

    def _extract_area_units(self, text_lower: str) -> Optional[str]:
        """Extract area units using area pattern strategy."""
        return self._area_pattern_strategy.extract_unit(text_lower)

    @property 
    def priority_order(self) -> List[str]:
        """Get priority order for units."""
        return self._pattern_repository.get_priority_order()

    @property
    def unit_patterns(self) -> Dict[str, List[str]]:
        """Get all unit patterns."""
        return {unit: self._pattern_repository.get_patterns(unit) 
                for unit in self._pattern_repository.get_all_units()}


class SpecificationFinder:
    """Finds specifications in product HTML."""
    
    def __init__(self):
        self.spec_keywords = [
            'ukuran', 'dimensi', 'size', 'dimension', 'spesifikasi', 'specification',
            'berat', 'weight', 'kapasitas', 'capacity', 'daya', 'power', 'tegangan',
            'voltage', 'diameter', 'panjang', 'length', 'lebar', 'width', 'tinggi',
            'height', 'tebal', 'thickness', 'volume', 'isi', 'content'
        ]
    
    def find_specification_values(self, soup: BeautifulSoup) -> List[str]:
        """Find all specification values in the soup."""
        specifications = []
        
        try:
            table_specs = self._extract_from_tables(soup)
            specifications.extend(table_specs)
        except Exception as e:
            logger.warning(f"Error extracting table specifications: {e}")
        
        try:
            span_specs = self._extract_from_spans(soup)
            specifications.extend(span_specs)
        except Exception as e:
            logger.warning(f"Error extracting span specifications: {e}")
        
        try:
            div_specs = self._extract_from_divs(soup)
            specifications.extend(div_specs)
        except Exception as e:
            logger.warning(f"Error extracting div specifications: {e}")
        
        return specifications
    
    def _extract_from_tables(self, soup: BeautifulSoup) -> List[str]:
        """Extract specifications from HTML tables."""
        specs = []
        try:
            tables = soup.find_all('table')
            for table in tables:
                table_specs = self._extract_specs_from_table(table)
                specs.extend(table_specs)
        except Exception as e:
            logger.warning(f"Error finding tables: {e}")
        
        return specs
    
    def _extract_specs_from_table(self, table) -> List[str]:
        """Extract specs from a single table."""
        specs = []
        try:
            rows = table.find_all('tr')
            for row in rows:
                spec_value = self._extract_spec_from_row(row)
                if spec_value:
                    specs.append(spec_value)
        except Exception as e:
            logger.debug(f"Error processing table: {e}")
        return specs
    
    def _extract_spec_from_row(self, row) -> Optional[str]:
        """Extract specification from a table row."""
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
    
    def _extract_from_spans(self, soup: BeautifulSoup) -> List[str]:
        """Extract specifications from span elements."""
        specs = []
        try:
            spans = soup.find_all('span')
            
            for span in spans:
                try:
                    text = span.get_text(strip=True)
                    if text and any(keyword in text.lower() for keyword in self.spec_keywords):
                        specs.append(text)
                except AttributeError as e:
                    logger.debug(f"Error processing span: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Error finding spans: {e}")
        
        return specs
    
    def _extract_from_divs(self, soup: BeautifulSoup) -> List[str]:
        """Extract specifications from div elements."""
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
                    logger.debug(f"Error processing div: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Error finding divs: {e}")
        
        return specs


class UnitParserConfiguration:
    """Configuration for unit parser context detection."""
    
    def __init__(self):
        self.construction_keywords = [
            'semen', 'cement', 'beton', 'concrete', 'besi', 'iron', 'steel',
            'kayu', 'wood', 'plywood', 'triplek', 'papan', 'board',
            'genteng', 'tile', 'atap', 'roof', 'dinding', 'wall',
            'lantai', 'floor', 'keramik', 'ceramic', 'granit', 'granite',
            'marmer', 'marble', 'cat', 'paint', 'pipa', 'pipe',
            'kabel', 'cable', 'wire', 'kawat', 'baut', 'bolt',
            'sekrup', 'screw', 'paku', 'nail', 'batu', 'brick'
        ]
        
        self.electrical_keywords = [
            'listrik', 'electric', 'kabel', 'cable', 'lampu', 'lamp',
            'saklar', 'switch', 'stop kontak', 'outlet', 'mcb',
            'circuit breaker', 'fuse', 'sekering', 'trafo', 'transformer',
            'genset', 'generator', 'inverter', 'ups', 'stabilizer'
        ]
    
    def is_construction_context(self, text: str) -> bool:
        """Check if text is related to construction."""
        try:
            if not text or not isinstance(text, str):
                return False
            text_lower = text.lower()
            return any(keyword in text_lower for keyword in self.construction_keywords)
        except Exception as e:
            logger.warning(f"Error checking construction context: {e}")
            return False
    
    def is_electrical_context(self, text: str) -> bool:
        """Check if text is related to electrical products."""
        try:
            if not text or not isinstance(text, str):
                return False
            text_lower = text.lower()
            return any(keyword in text_lower for keyword in self.electrical_keywords)
        except Exception as e:
            logger.warning(f"Error checking electrical context: {e}")
            return False


class TokopediaUnitParser:
    """
    Unit parser for Tokopedia products.
    
    Extracts product units (e.g., 'kg', 'm²', 'pcs') from HTML content
    using multiple strategies:
    1. Specification tables
    2. Product details sections
    3. Full text pattern matching
    """
    
    def __init__(self, extractor: UnitExtractor = None, 
                 spec_finder: SpecificationFinder = None,
                 config: UnitParserConfiguration = None):
        """
        Initialize Tokopedia unit parser.
        
        Args:
            extractor: Custom unit extractor (uses default if None)
            spec_finder: Custom specification finder (uses default if None)
            config: Custom configuration (uses default if None)
        """
        self.extractor = extractor or UnitExtractor()
        self.spec_finder = spec_finder or SpecificationFinder()
        self.config = config or UnitParserConfiguration()
    
    def parse_unit(self, html_content: str) -> Optional[str]:
        """
        Parse unit from product HTML content.
        
        Args:
            html_content: HTML content of product page
            
        Returns:
            Detected unit or None
        """
        if not html_content or not isinstance(html_content, str):
            return None
        
        try:
            soup = self._create_soup_safely(html_content)
            if not soup:
                return None
            
            # Extract specifications from structured elements
            specifications = self._extract_specifications_safely(soup)
            found_units = self._extract_units_from_specifications(specifications)
            prioritized_unit = self._apply_priority_rules(found_units)
            if prioritized_unit:
                return prioritized_unit
            
            # Fallback to full text extraction
            return self._extract_from_full_text(soup)
            
        except Exception as e:
            logger.error(f"Unexpected error in unit parsing: {e}")
            return None
    
    def _create_soup_safely(self, html_content: str) -> Optional[BeautifulSoup]:
        """Create BeautifulSoup object safely."""
        try:
            return BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            logger.warning(f"Error creating soup from HTML: {e}")
            return None
    
    def _extract_specifications_safely(self, soup: BeautifulSoup) -> List[str]:
        """Extract specifications from soup safely."""
        try:
            return self.spec_finder.find_specification_values(soup)
        except Exception as e:
            logger.warning(f"Error extracting specifications: {e}")
            return []
    
    def _extract_units_from_specifications(self, specifications: List[str]) -> List[str]:
        """Extract units from list of specifications."""
        found_units = []
        for spec in specifications:
            try:
                unit = self.extractor.extract_unit(spec)
                if unit:
                    found_units.append(unit)
            except Exception as e:
                logger.debug(f"Error extracting unit from spec '{spec}': {e}")
                continue
        
        return found_units
    
    def _apply_priority_rules(self, found_units: List[str]) -> Optional[str]:
        """Apply priority rules to select best unit."""
        if not found_units:
            return None
        
        try:
            # Priority 1: Area units
            area_units = [UNIT_M2, UNIT_CM2, UNIT_INCH2, UNIT_MM2]
            for unit in found_units:
                if unit in area_units:
                    return unit
            
            # Priority 2: Volume units
            volume_units = [UNIT_M3, UNIT_CM3]
            for unit in found_units:
                if unit in volume_units:
                    return unit
            
            # Priority 3: Weight units
            weight_units = [UNIT_KG, UNIT_GRAM, UNIT_TON, UNIT_POUND]
            for unit in found_units:
                if unit in weight_units:
                    return unit
            
            # Return first found unit
            return found_units[0]
            
        except Exception as e:
            logger.warning(f"Error applying priority rules: {e}")
            return found_units[0] if found_units else None
    
    def _extract_from_full_text(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract unit from full page text as fallback."""
        try:
            full_text = soup.get_text()
            return self.extractor.extract_unit(full_text)
        except Exception as e:
            logger.warning(f"Error extracting from full text: {e}")
            return None
