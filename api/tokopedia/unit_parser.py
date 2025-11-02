import re
import logging
from typing import Optional, Dict, List, Protocol
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup

# Import shared components from Gemilang to avoid duplication
from api.gemilang.unit_parser import (
    UnitPatternRepository,
    AreaPatternStrategy,
    AdjacentPatternStrategy,
    UnitExtractor,
    SpecificationFinder,
    UnitParserConfiguration,
    UNIT_M2,
    UNIT_CM2,
    UNIT_INCH2,
    UNIT_MM2,
    UNIT_M3,
    UNIT_CM3,
    UNIT_KG,
    UNIT_GRAM,
    UNIT_TON,
    UNIT_POUND,
)

logger = logging.getLogger(__name__)


class TokopediaUnitParserConfiguration(UnitParserConfiguration):
    """Tokopedia-specific configuration extending Gemilang's configuration."""
    
    def __init__(self):
        super().__init__()
        # Add Tokopedia-specific construction keywords
        self.construction_keywords.extend(['batu', 'brick'])


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
        self.config = config or TokopediaUnitParserConfiguration()
    
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