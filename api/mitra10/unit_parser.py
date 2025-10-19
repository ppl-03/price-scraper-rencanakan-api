import re
import logging
from typing import Optional, Dict, List, Protocol
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
    
    def extract_unit(self, text: str) -> Optional[str]:
        ...


class Mitra10UnitPatternRepository:
    
    def __init__(self):
        self._unit_patterns = self._initialize_patterns()
        self._priority_order = self._initialize_priority_order()
    
    def _initialize_patterns(self) -> Dict[str, List[str]]:
        return {
            'MM': ['mm', 'milimeter', 'millimeter'],
            'CM': ['cm', 'centimeter', 'sentimeter'],
            'M': ['meter', 'metre', r'm(?!m|l|g|²|³)'],
            'INCH': ['inch', 'inchi', '"', '″', 'inc'],
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


class Mitra10AreaPatternStrategy:
    
    def extract_unit(self, text_lower: str) -> Optional[str]:
        try:
            # Pattern for area calculations like "60x60 cm"
            area_pattern = r'(\d{1,10}(?:[.,]\d{1,10})?)\s?[x×]\s?(\d{1,10}(?:[.,]\d{1,10})?)\s?(cm|mm|m|inch)(?:\s|$)'
            match = re.search(area_pattern, text_lower, re.IGNORECASE)
            if match:
                unit_key = match.group(3).lower()
                area_map = {'cm': UNIT_CM2, 'mm': UNIT_MM2, 'm': UNIT_M2, 'inch': UNIT_INCH2}
                return area_map.get(unit_key)
            
            return None
            
        except re.error as e:
            logger.warning(f"Regex error in Mitra10 area pattern extraction: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Mitra10 area pattern extraction: {e}")
            return None


class Mitra10AdjacentPatternStrategy:
    
    def extract_unit(self, text_lower: str) -> Optional[str]:
        try:
            # Patterns specific to Mitra10 product descriptions
            adjacent_patterns = [
                # Direct unit attachment: "25kg", "100ml", "5pcs"
                (r'(\d{1,10}(?:[.,]\d{1,10})?)(mm|cm|kg|gr|ml|lt|pcs|set|inch|feet|watt|volt|amp|hp|bar|psi)(?:\s|$)', 2),
                
                # Diameter patterns: "diameter 25mm"
                (r'diameter\s?(\d{1,10}(?:[.,]\d{1,10})?)\s?(mm|cm|m|inch)', 2), 
                
                # Symbol diameter: "Ø 25mm"
                (r'Ø\s?(\d{1,10}(?:[.,]\d{1,10})?)\s?(mm|cm|m|inch)', 2),
                
                # Time units: "per hari", "/ minggu"
                (r'(\d{1,10}(?:[.,]\d{1,10})?)\s?/?(\bhari\b|\bminggu\b|\bulan\b|\btahun\b|\bjam\b|\bhour\b|\bday\b|\bweek\b|\bmonth\b|\byear\b)', 2),
                
                # Mitra10 specific patterns for construction materials
                (r'(\d{1,10}(?:[.,]\d{1,10})?)\s?(sak|karung|bag|zak)(?:\s+semen|\s+cement)?', 2),
                
                # Roll/sheet patterns common in Mitra10
                (r'(\d{1,10}(?:[.,]\d{1,10})?)\s?(roll|lembar|sheet|batang|papan)', 2)
            ]
            
            unit_mappings = {
                'mm': 'MM', 'cm': 'CM', 'kg': UNIT_KG, 'gr': UNIT_GRAM, 'ml': 'ML', 'lt': 'LITER', 
                'pcs': 'PCS', 'set': 'SET', 'inch': 'INCH', 'feet': 'FEET', 'watt': 'WATT', 
                'volt': 'VOLT', 'amp': 'AMPERE', 'hp': 'HP', 'bar': 'BAR', 'psi': 'PSI',
                'm': 'M', 'hari': 'HARI', 'minggu': 'MINGGU', 'bulan': 'BULAN', 'tahun': 'TAHUN', 
                'jam': 'JAM', 'hour': 'JAM', 'day': 'HARI', 'week': 'MINGGU', 'month': 'BULAN', 
                'year': 'TAHUN', 'sak': 'SAK', 'karung': 'SAK', 'bag': 'SAK', 'zak': 'SAK',
                'roll': 'ROLL', 'lembar': 'LEMBAR', 'sheet': 'SHEET', 'batang': 'BATANG', 'papan': 'PAPAN'
            }
            
            for pattern, group_index in adjacent_patterns:
                try:
                    matches = re.finditer(pattern, text_lower, re.IGNORECASE)
                    for match in matches:
                        try:
                            unit_key = match.group(group_index).lower()
                            if unit_key in unit_mappings:
                                return unit_mappings[unit_key]
                        except (IndexError, AttributeError) as e:
                            logger.warning(f"Error processing Mitra10 match group: {e}")
                            continue
                except re.error as e:
                    logger.warning(f"Invalid Mitra10 regex pattern: {pattern}, error: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error in Mitra10 adjacent pattern extraction: {e}")
            return None


class Mitra10UnitExtractor:
    
    def __init__(self, pattern_repository: Mitra10UnitPatternRepository = None):
        self._pattern_repository = pattern_repository or Mitra10UnitPatternRepository()
        self._area_pattern_strategy = Mitra10AreaPatternStrategy()
        self._adjacent_pattern_strategy = Mitra10AdjacentPatternStrategy()
    
    def extract_unit(self, text: str) -> Optional[str]:
        if not text or not isinstance(text, str):
            return None
        
        try:
            text_lower = text.lower().strip()
            if not text_lower:
                return None
            
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
            
        except Exception as e:
            logger.warning(f"Error during Mitra10 unit extraction: {e}")
            return None
    
    def _extract_by_priority_patterns(self, text_lower: str) -> Optional[str]:
        try:
            if len(text_lower) > 5000:
                logger.warning("Text too long for Mitra10 pattern extraction, truncating to 5000 chars")
                text_lower = text_lower[:5000]
            
            priority_order = self._pattern_repository.get_priority_order()
            
            for unit in priority_order:
                patterns = self._pattern_repository.get_patterns(unit)
                for pattern in patterns:
                    try:
                        # Use word boundaries for better matching
                        pattern_with_boundaries = f'(?:^|\\s|[\\(\\[{{]|\\d)({pattern})(?:\\s|[\\)\\]}}]|$)'
                        if re.search(pattern_with_boundaries, text_lower, re.IGNORECASE):
                            return unit
                    except re.error as e:
                        logger.warning(f"Invalid Mitra10 regex pattern '{pattern}' for unit '{unit}': {e}")
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error in Mitra10 priority pattern extraction: {e}")
            return None


class Mitra10SpecificationFinder:
    
    def __init__(self):
        # Keywords specific to Mitra10 product specifications
        self.spec_keywords = [
            'ukuran', 'dimensi', 'size', 'dimension', 'spesifikasi', 'specification',
            'berat', 'weight', 'kapasitas', 'capacity', 'daya', 'power', 'tegangan',
            'voltage', 'diameter', 'panjang', 'length', 'lebar', 'width', 'tinggi',
            'height', 'tebal', 'thickness', 'volume', 'isi', 'content', 'kemasan',
            'packaging', 'satuan', 'unit', 'per', 'setiap', 'each'
        ]
    
    def find_specification_values(self, soup: BeautifulSoup) -> List[str]:
        specifications = []
        
        try:
            # Extract from Mitra10 specific elements
            mitra10_specs = self._extract_from_mitra10_elements(soup)
            specifications.extend(mitra10_specs)
        except Exception as e:
            logger.warning(f"Error extracting Mitra10 specific specifications: {e}")
        
        try:
            # Extract from tables (common in product detail pages)
            table_specs = self._extract_from_tables(soup)
            specifications.extend(table_specs)
        except Exception as e:
            logger.warning(f"Error extracting table specifications: {e}")
        
        try:
            # Extract from spans and divs
            span_specs = self._extract_from_spans_and_divs(soup)
            specifications.extend(span_specs)
        except Exception as e:
            logger.warning(f"Error extracting span/div specifications: {e}")
        
        return specifications
    
    def _extract_from_mitra10_elements(self, soup: BeautifulSoup) -> List[str]:
        """Extract specifications from Mitra10-specific HTML elements"""
        specs = []
        
        try:
            # Look for product description areas
            desc_areas = soup.find_all(['div', 'section'], class_=lambda x: x and any(
                keyword in x.lower() for keyword in ['product-info', 'product-detail', 'specification', 'deskripsi']
            ))
            
            for area in desc_areas:
                try:
                    # Use separator to avoid text concatenation issues
                    text = area.get_text(separator=' ', strip=True)
                    if text and len(text) > 10:
                        specs.append(text)
                except Exception as e:
                    logger.debug(f"Error processing Mitra10 description area: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Error finding Mitra10 description areas: {e}")
        
        return specs
    
    def _extract_from_tables(self, soup: BeautifulSoup) -> List[str]:
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
        
        try:
            # Extract from spans
            spans = soup.find_all('span')
            for span in spans:
                try:
                    text = span.get_text(separator=' ', strip=True)
                    if text and any(keyword in text.lower() for keyword in self.spec_keywords):
                        specs.append(text)
                except AttributeError as e:
                    logger.debug(f"Error processing span: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Error finding spans: {e}")
        
        try:
            # Extract from divs with specification-related classes
            spec_divs = soup.find_all('div', class_=lambda x: x and any(
                keyword in x.lower() for keyword in ['spec', 'detail', 'info', 'description', 'produk']
            ))
            
            for div in spec_divs:
                try:
                    text = div.get_text(separator=' ', strip=True)
                    if text and len(text) > 5:
                        specs.append(text)
                except AttributeError as e:
                    logger.debug(f"Error processing div: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Error finding divs: {e}")
        
        return specs


class Mitra10UnitParserConfiguration:
    
    def __init__(self):
        # Keywords specific to Mitra10 construction and hardware products
        self.construction_keywords = [
            'semen', 'cement', 'beton', 'concrete', 'besi', 'iron', 'steel',
            'kayu', 'wood', 'plywood', 'triplek', 'papan', 'board',
            'genteng', 'tile', 'atap', 'roof', 'dinding', 'wall',
            'lantai', 'floor', 'keramik', 'ceramic', 'granit', 'granite',
            'marmer', 'marble', 'cat', 'paint', 'pipa', 'pipe',
            'kabel', 'cable', 'wire', 'kawat', 'baut', 'bolt',
            'sekrup', 'screw', 'paku', 'nail', 'lem', 'glue',
            'pasir', 'sand', 'kerikil', 'gravel', 'batako', 'block'
        ]
        
        self.electrical_keywords = [
            'listrik', 'electric', 'kabel', 'cable', 'lampu', 'lamp',
            'saklar', 'switch', 'stop kontak', 'outlet', 'mcb',
            'circuit breaker', 'fuse', 'sekering', 'trafo', 'transformer',
            'genset', 'generator', 'inverter', 'ups', 'stabilizer',
            'fitting', 'socket', 'plug', 'colokan'
        ]
        
        self.plumbing_keywords = [
            'pipa', 'pipe', 'pvc', 'fitting', 'elbow', 'tee', 'reducer',
            'kran', 'faucet', 'valve', 'katup', 'sambungan', 'joint',
            'seal', 'gasket', 'teflon', 'dop', 'cap', 'tutup'
        ]
    
    def is_construction_context(self, text: str) -> bool:
        try:
            if not text or not isinstance(text, str):
                return False
            text_lower = text.lower()
            return any(keyword in text_lower for keyword in self.construction_keywords)
        except Exception as e:
            logger.warning(f"Error checking Mitra10 construction context: {e}")
            return False
    
    def is_electrical_context(self, text: str) -> bool:
        try:
            if not text or not isinstance(text, str):
                return False
            text_lower = text.lower()
            return any(keyword in text_lower for keyword in self.electrical_keywords)
        except Exception as e:
            logger.warning(f"Error checking Mitra10 electrical context: {e}")
            return False
    
    def is_plumbing_context(self, text: str) -> bool:
        try:
            if not text or not isinstance(text, str):
                return False
            text_lower = text.lower()
            return any(keyword in text_lower for keyword in self.plumbing_keywords)
        except Exception as e:
            logger.warning(f"Error checking Mitra10 plumbing context: {e}")
            return False


class Mitra10UnitParser:
    """
    Unit parser specifically designed for Mitra10 products.
    Handles construction materials, hardware, electrical, and plumbing items.
    """
    
    def __init__(self, 
                 extractor: Mitra10UnitExtractor = None,
                 spec_finder: Mitra10SpecificationFinder = None,
                 config: Mitra10UnitParserConfiguration = None):
        self.extractor = extractor or Mitra10UnitExtractor()
        self.spec_finder = spec_finder or Mitra10SpecificationFinder()
        self.config = config or Mitra10UnitParserConfiguration()
    
    def parse_unit(self, html_content: str) -> Optional[str]:
        """
        Parse unit from Mitra10 product HTML content.
        
        Args:
            html_content: HTML content from Mitra10 product page
            
        Returns:
            Optional[str]: Detected unit or None if not found
        """
        if not html_content or not isinstance(html_content, str):
            return None
        
        try:
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
            
        except Exception as e:
            logger.error(f"Unexpected error in Mitra10 unit parsing: {e}")
            return None
    
    def _create_soup_safely(self, html_content: str) -> Optional[BeautifulSoup]:
        try:
            return BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            logger.warning(f"Error creating soup from Mitra10 HTML: {e}")
            return None
    
    def _extract_specifications_safely(self, soup: BeautifulSoup) -> List[str]:
        try:
            return self.spec_finder.find_specification_values(soup)
        except Exception as e:
            logger.warning(f"Error extracting Mitra10 specifications: {e}")
            return []
    
    def _extract_units_from_specifications(self, specifications: List[str]) -> List[str]:
        found_units = []
        for spec in specifications:
            try:
                unit = self.extractor.extract_unit(spec)
                if unit:
                    found_units.append(unit)
            except Exception as e:
                logger.debug(f"Error extracting unit from Mitra10 spec '{spec}': {e}")
                continue
        
        return found_units
    
    def _apply_mitra10_priority_rules(self, found_units: List[str], html_content: str) -> Optional[str]:
        """Apply Mitra10-specific priority rules based on product context"""
        if not found_units:
            return None
        
        try:
            # Context-based priority
            context_unit = self._get_context_specific_unit(found_units, html_content)
            if context_unit:
                return context_unit
            
            # General priority order
            return self._get_general_priority_unit(found_units)
            
        except Exception as e:
            logger.warning(f"Error applying Mitra10 priority rules: {e}")
            return found_units[0] if found_units else None
    
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
        try:
            full_text = soup.get_text()
            return self.extractor.extract_unit(full_text)
        except Exception as e:
            logger.warning(f"Error extracting from Mitra10 full text: {e}")
            return None